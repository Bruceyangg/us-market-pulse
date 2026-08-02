"""Public share via Cloudflare quick tunnel (trycloudflare.com)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from us_market_pulse import lan_ips

ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = ROOT / ".tools"
DATA_DIR = ROOT / "data"
STATE_PATH = DATA_DIR / "share.json"

_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.I)

_lock = threading.Lock()
_proc: subprocess.Popen[str] | None = None
_url: str | None = None
_started_at: float | None = None
_error: str | None = None
_log_tail: list[str] = []


def _default_port() -> int:
    return int(os.getenv("PULSE_PORT", "8765") or "8765")


def _find_cloudflared() -> str | None:
    env = os.getenv("CLOUDFLARED_BIN", "").strip()
    if env and Path(env).exists():
        return env
    for candidate in (
        TOOLS_DIR / "cloudflared",
        Path("/tmp/cloudflared"),
        Path("/usr/local/bin/cloudflared"),
        Path("/opt/homebrew/bin/cloudflared"),
    ):
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    which = shutil.which("cloudflared")
    return which


def ensure_cloudflared() -> str:
    """Return path to cloudflared, copying from /tmp if needed."""
    found = _find_cloudflared()
    if found:
        # Prefer a project-local copy for stability
        local = TOOLS_DIR / "cloudflared"
        if found != str(local) and Path(found).exists():
            TOOLS_DIR.mkdir(parents=True, exist_ok=True)
            if not local.exists():
                shutil.copy2(found, local)
                local.chmod(0o755)
            return str(local)
        return found
    raise RuntimeError(
        "未找到 cloudflared。请先安装：从 Cloudflare 下载 darwin-arm64，"
        "放到项目 .tools/cloudflared，或设置 CLOUDFLARED_BIN。"
    )


def _save_state() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "url": _url,
        "started_at": _started_at,
        "error": _error,
        "running": bool(_proc and _proc.poll() is None),
    }
    STATE_PATH.write_text(
        __import__("json").dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _reader(proc: subprocess.Popen[str]) -> None:
    global _url, _error
    assert proc.stderr is not None
    for line in proc.stderr:
        text = line.rstrip()
        _log_tail.append(text)
        if len(_log_tail) > 80:
            del _log_tail[:40]
        match = _URL_RE.search(text)
        if match and not _url:
            with _lock:
                _url = match.group(0).rstrip("/")
                _error = None
                _save_state()
        if "failed" in text.casefold() and "error" in text.casefold():
            with _lock:
                _error = text[-240:]
                _save_state()
    code = proc.poll()
    with _lock:
        if code not in (None, 0) and not _url:
            _error = _error or f"cloudflared 退出码 {code}"
        _save_state()


def status() -> dict[str, Any]:
    running = bool(_proc and _proc.poll() is None)
    port = _default_port()
    ips = lan_ips()
    return {
        "running": running,
        "url": _url if running else None,
        "started_at": _started_at if running else None,
        "error": _error,
        "binary": _find_cloudflared(),
        "local": f"http://127.0.0.1:{port}",
        "lan": [f"http://{ip}:{port}" for ip in ips],
        "tip": (
            "公网链接任何人手机/电脑都可打开；链接在进程重启后会变化。"
            if running and _url
            else "点击「开启公网分享」生成可外网访问的链接（Cloudflare 临时隧道）。"
        ),
    }


def start(port: int | None = None) -> dict[str, Any]:
    global _proc, _url, _started_at, _error, _log_tail
    port = port or _default_port()
    with _lock:
        if _proc and _proc.poll() is None and _url:
            return status()
        if _proc and _proc.poll() is None:
            # Still starting
            return status()

        binary = ensure_cloudflared()
        _url = None
        _error = None
        _log_tail = []
        _started_at = time.time()
        target = f"http://127.0.0.1:{port}"
        _proc = subprocess.Popen(
            [binary, "tunnel", "--url", target, "--no-autoupdate"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=_reader, args=(_proc,), daemon=True).start()
        _save_state()

    # Wait briefly for URL
    deadline = time.time() + 20
    while time.time() < deadline:
        if _url or (_proc and _proc.poll() is not None):
            break
        time.sleep(0.25)
    if not _url and _proc and _proc.poll() is not None:
        with _lock:
            _error = _error or "隧道启动失败，请查看服务日志"
            _save_state()
    return status()


def stop() -> dict[str, Any]:
    global _proc, _url, _started_at, _error
    with _lock:
        if _proc and _proc.poll() is None:
            _proc.terminate()
            try:
                _proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _proc.kill()
        _proc = None
        _url = None
        _started_at = None
        _error = None
        _save_state()
    return status()


def main() -> None:
    """CLI: pulse-share — start tunnel and print public URL."""
    import json

    st = start()
    print(json.dumps(st, ensure_ascii=False, indent=2))
    if st.get("url"):
        print(f"\nPublic URL: {st['url']}")
    else:
        print("\nWaiting for URL… check again with status, or inspect logs.")
        # Keep process alive while tunnel runs
        try:
            while _proc and _proc.poll() is None:
                if _url:
                    print(f"Public URL: {_url}")
                    break
                time.sleep(0.5)
            while _proc and _proc.poll() is None:
                time.sleep(2)
        except KeyboardInterrupt:
            stop()


if __name__ == "__main__":
    main()
