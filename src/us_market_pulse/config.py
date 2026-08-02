"""Runtime config: local JSON file + environment overrides."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()

# Prefer project data/ next to repo root; fallback to package-adjacent.
_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("PULSE_DATA_DIR", str(_ROOT / "data")))
SETTINGS_PATH = DATA_DIR / "settings.json"


def _split_list(raw: str | list[str] | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return [part.strip() for part in str(raw).replace("\n", ",").split(",") if part.strip()]


def detect_webhook_format(url: str, explicit: str = "auto") -> str:
    fmt = (explicit or "auto").strip().lower()
    if fmt and fmt != "auto":
        return fmt
    u = (url or "").lower()
    if "sctapi.ftqq.com" in u or "push.ft07.com" in u or "serverchan" in u:
        return "serverchan"
    if "oapi.dingtalk.com" in u:
        return "dingtalk"
    if "open.feishu.cn" in u or "open.larksuite.com" in u:
        return "feishu"
    if "qyapi.weixin.qq.com" in u:
        return "wecom"
    if "discord.com/api/webhooks" in u or "discordapp.com/api/webhooks" in u:
        return "discord"
    return "markdown"


@dataclass
class Settings:
    webhook_url: str = ""
    webhook_format: str = "auto"
    push_interval_minutes: int = 15
    push_times: list[str] = field(default_factory=list)
    push_timezone: str = "Asia/Shanghai"
    push_enabled: bool = False
    push_secret: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_to: str = ""
    smtp_from: str = ""
    watch_keywords: list[str] = field(default_factory=list)

    @property
    def email_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_to and (self.smtp_from or self.smtp_user))

    @property
    def webhook_configured(self) -> bool:
        return bool(self.webhook_url)

    @property
    def any_channel(self) -> bool:
        return self.webhook_configured or self.email_configured

    @property
    def resolved_webhook_format(self) -> str:
        return detect_webhook_format(self.webhook_url, self.webhook_format)

    def public_dict(self) -> dict[str, Any]:
        """Safe view for UI/API (mask secrets)."""
        return {
            "webhook_url": self.webhook_url,
            "webhook_format": self.webhook_format,
            "resolved_webhook_format": self.resolved_webhook_format,
            "push_interval_minutes": self.push_interval_minutes,
            "push_times": list(self.push_times),
            "push_timezone": self.push_timezone,
            "push_enabled": self.push_enabled,
            "has_push_secret": bool(self.push_secret),
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "smtp_user": self.smtp_user,
            "smtp_to": self.smtp_to,
            "smtp_from": self.smtp_from,
            "has_smtp_password": bool(self.smtp_password),
            "watch_keywords": list(self.watch_keywords),
            "webhook_configured": self.webhook_configured,
            "email_configured": self.email_configured,
            "any_channel": self.any_channel,
            "settings_path": str(SETTINGS_PATH),
        }


def _read_file() -> dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _env_overlay(data: dict[str, Any]) -> dict[str, Any]:
    """Environment variables win over file for deployment convenience."""
    mapping = {
        "PULSE_WEBHOOK_URL": "webhook_url",
        "PULSE_WEBHOOK_FORMAT": "webhook_format",
        "PULSE_PUSH_TZ": "push_timezone",
        "PULSE_PUSH_SECRET": "push_secret",
        "PULSE_SMTP_HOST": "smtp_host",
        "PULSE_SMTP_USER": "smtp_user",
        "PULSE_SMTP_PASSWORD": "smtp_password",
        "PULSE_SMTP_TO": "smtp_to",
        "PULSE_SMTP_FROM": "smtp_from",
    }
    out = dict(data)
    for env_key, field_name in mapping.items():
        val = os.getenv(env_key)
        if val is not None and val.strip() != "":
            out[field_name] = val.strip()

    if os.getenv("PULSE_PUSH_TIMES"):
        out["push_times"] = _split_list(os.getenv("PULSE_PUSH_TIMES"))
    if os.getenv("PULSE_PUSH_INTERVAL_MINUTES"):
        try:
            out["push_interval_minutes"] = int(os.getenv("PULSE_PUSH_INTERVAL_MINUTES", "15"))
        except ValueError:
            pass
    if os.getenv("PULSE_WATCH_KEYWORDS"):
        out["watch_keywords"] = _split_list(os.getenv("PULSE_WATCH_KEYWORDS"))
    if os.getenv("PULSE_SMTP_PORT"):
        try:
            out["smtp_port"] = int(os.getenv("PULSE_SMTP_PORT", "587"))
        except ValueError:
            pass

    enabled_raw = os.getenv("PULSE_PUSH_ENABLED", "").strip().lower()
    if enabled_raw in {"0", "false", "no", "off"}:
        out["push_enabled"] = False
    elif enabled_raw in {"1", "true", "yes", "on"}:
        out["push_enabled"] = True
    return out


def load_settings() -> Settings:
    raw = _env_overlay(_read_file())
    # Default interval: every 15 minutes. Fixed clock times are optional extras.
    if "push_interval_minutes" in raw:
        try:
            interval = int(raw.get("push_interval_minutes") or 15)
        except (TypeError, ValueError):
            interval = 15
    else:
        interval = 15
    interval = max(0, interval)

    times = _split_list(raw.get("push_times"))
    keywords = _split_list(raw.get("watch_keywords"))
    webhook = str(raw.get("webhook_url") or "").strip()
    email_ready = bool(str(raw.get("smtp_host") or "").strip() and str(raw.get("smtp_to") or "").strip())

    if "push_enabled" in raw:
        enabled = bool(raw.get("push_enabled"))
    else:
        enabled = bool(webhook or email_ready)

    smtp_user = str(raw.get("smtp_user") or "").strip()
    smtp_from = str(raw.get("smtp_from") or "").strip() or smtp_user

    return Settings(
        webhook_url=webhook,
        webhook_format=str(raw.get("webhook_format") or "auto").strip() or "auto",
        push_interval_minutes=interval,
        push_times=times,
        push_timezone=str(raw.get("push_timezone") or "Asia/Shanghai").strip()
        or "Asia/Shanghai",
        push_enabled=enabled,
        push_secret=str(raw.get("push_secret") or "").strip(),
        smtp_host=str(raw.get("smtp_host") or "").strip(),
        smtp_port=int(raw.get("smtp_port") or 587),
        smtp_user=smtp_user,
        smtp_password=str(raw.get("smtp_password") or "").strip(),
        smtp_to=str(raw.get("smtp_to") or "").strip(),
        smtp_from=smtp_from,
        watch_keywords=keywords,
    )


def save_settings(patch: dict[str, Any]) -> Settings:
    """Merge patch into local settings file and return loaded settings."""
    with _LOCK:
        current = _read_file()
        allowed = {
            "webhook_url",
            "webhook_format",
            "push_interval_minutes",
            "push_times",
            "push_timezone",
            "push_enabled",
            "push_secret",
            "smtp_host",
            "smtp_port",
            "smtp_user",
            "smtp_password",
            "smtp_to",
            "smtp_from",
            "watch_keywords",
        }
        for key, value in patch.items():
            if key not in allowed:
                continue
            # Keep existing password/secret when UI sends blank
            if key in {"smtp_password", "push_secret"} and (value is None or value == ""):
                continue
            if key == "push_times":
                current[key] = _split_list(value)
            elif key == "watch_keywords":
                current[key] = _split_list(value)
            elif key in {"smtp_port", "push_interval_minutes"}:
                current[key] = int(value or 0)
            elif key == "push_enabled":
                current[key] = bool(value)
            else:
                current[key] = value

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return load_settings()


def export_file_settings() -> dict[str, Any]:
    """Raw file contents (for debugging), secrets masked."""
    data = _read_file()
    if data.get("smtp_password"):
        data["smtp_password"] = "***"
    if data.get("push_secret"):
        data["push_secret"] = "***"
    return data
