"""US Market Pulse / Pulse Desk entrypoint."""

from __future__ import annotations

import os
import socket


def lan_ips() -> list[str]:
    """Best-effort local network IPv4 addresses for phone access tips."""
    found: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                found.append(ip)
    except OSError:
        pass

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127.") and ip not in found:
                found.append(ip)
    except OSError:
        pass
    return found


def main() -> None:
    import uvicorn

    host = os.getenv("PULSE_HOST", "0.0.0.0").strip() or "0.0.0.0"
    # Cloud platforms (Render/Railway/Fly) inject PORT
    port = int(os.getenv("PORT") or os.getenv("PULSE_PORT", "8765") or "8765")
    # Local default: reload on; cloud/prod: set PULSE_RELOAD=0 (or PORT present)
    reload_default = "0" if os.getenv("PORT") else "1"
    reload = os.getenv("PULSE_RELOAD", reload_default) not in {"0", "false", "no"}
    ips = lan_ips()

    print("Pulse Desk starting…")
    print(f"  Local:  http://127.0.0.1:{port}")
    for ip in ips:
        print(f"  Phone:  http://{ip}:{port}  (same Wi-Fi)")
    if not ips:
        print("  Phone:  use your Mac LAN IP, e.g. http://192.168.x.x:8765")
    if os.getenv("PORT"):
        print(f"  Cloud:  listening on 0.0.0.0:{port}")

    uvicorn.run(
        "us_market_pulse.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
