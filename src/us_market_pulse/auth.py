"""Simple username/password auth with signed cookie sessions."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

from us_market_pulse.config import DATA_DIR

_LOCK = threading.RLock()
USERS_PATH = DATA_DIR / "users.json"
SECRET_PATH = DATA_DIR / "secret.key"

# Fixed dummy hash so authenticating a non-existent user still spends PBKDF2
# time, preventing username enumeration via response timing.
_DUMMY_HASH = (
    "pbkdf2_sha256$210000$"
    "00000000000000000000000000000000$"
    "0000000000000000000000000000000000000000000000000000000000000000"
)

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,24}$")
_PBKDF2_ITERS = 210_000


def session_secret() -> str:
    env = (os.getenv("PULSE_SECRET_KEY") or "").strip()
    if env:
        return env
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if SECRET_PATH.exists():
        val = SECRET_PATH.read_text(encoding="utf-8").strip()
        if val:
            return val
    val = secrets.token_urlsafe(48)
    SECRET_PATH.write_text(val + "\n", encoding="utf-8")
    try:
        SECRET_PATH.chmod(0o600)
    except OSError:
        pass
    return val


def normalize_username(raw: str | None) -> str:
    return str(raw or "").strip().lower()


def validate_username(username: str) -> str:
    user = normalize_username(username)
    if not _USERNAME_RE.match(user):
        raise ValueError("用户名需为 3–24 位字母、数字或下划线")
    return user


def validate_password(password: str) -> str:
    pwd = str(password or "")
    if len(pwd) < 6:
        raise ValueError("密码至少 6 位")
    if len(pwd) > 128:
        raise ValueError("密码过长")
    return pwd


def _hash_password(password: str, *, salt: str | None = None) -> str:
    salt_b = bytes.fromhex(salt) if salt else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_b,
        _PBKDF2_ITERS,
    )
    return f"pbkdf2_sha256${_PBKDF2_ITERS}${salt_b.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algo, iters_s, salt_hex, digest_hex = encoded.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        salt_b = bytes.fromhex(salt_hex)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt_b,
            iters,
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _load_users() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not USERS_PATH.exists():
        return {"users": {}}
    try:
        data = json.loads(USERS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"users": {}}
    if not isinstance(data.get("users"), dict):
        data["users"] = {}
    return data


def _save_users(data: dict[str, Any]) -> None:
    with _LOCK:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = USERS_PATH.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp.replace(USERS_PATH)


def public_user(user: dict[str, Any] | None) -> dict[str, Any] | None:
    if not user:
        return None
    return {
        "username": user.get("username"),
        "display_name": user.get("display_name") or user.get("username"),
        "created_at": user.get("created_at"),
    }


def get_user(username: str) -> dict[str, Any] | None:
    user = normalize_username(username)
    return (_load_users().get("users") or {}).get(user)


def register_user(username: str, password: str, *, display_name: str = "") -> dict[str, Any]:
    user = validate_username(username)
    pwd = validate_password(password)
    # Read-check-write under one lock so concurrent registrations cannot both
    # pass the uniqueness check or clobber each other's records.
    with _LOCK:
        data = _load_users()
        users = data.setdefault("users", {})
        if user in users:
            raise ValueError("用户名已被占用")
        record = {
            "username": user,
            "display_name": (display_name or user).strip()[:40] or user,
            "password_hash": _hash_password(pwd),
            "created_at": time.time(),
        }
        users[user] = record
        _save_users(data)
    return public_user(record)  # type: ignore[return-value]


def authenticate_user(username: str, password: str) -> dict[str, Any]:
    user = normalize_username(username)
    pwd = str(password or "")
    record = get_user(user)
    encoded = str((record or {}).get("password_hash") or "") or _DUMMY_HASH
    ok = _verify_password(pwd, encoded)
    if not record or not ok:
        raise ValueError("用户名或密码错误")
    return public_user(record)  # type: ignore[return-value]


def current_username(request: Request) -> str | None:
    user = request.session.get("user")
    if not user:
        return None
    return normalize_username(str(user))


def current_user(request: Request) -> dict[str, Any] | None:
    username = current_username(request)
    if not username:
        return None
    return public_user(get_user(username))


def require_user(request: Request) -> str:
    username = current_username(request)
    if not username or not get_user(username):
        raise HTTPException(status_code=401, detail="请先登录后查看个人持仓")
    return username


def login_session(request: Request, username: str) -> None:
    request.session.clear()
    request.session["user"] = normalize_username(username)
    request.session["logged_in_at"] = time.time()


def logout_session(request: Request) -> None:
    request.session.clear()
