"""Pulse Desk — US market intelligence web app."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from us_market_pulse import lan_ips
from us_market_pulse.config import load_settings, save_settings
from us_market_pulse.feeds import (
    CATEGORIES,
    FEED_SOURCES,
    bearish_spotlight,
    clear_cache,
    filter_items,
    get_event,
    refresh_intel,
)
from us_market_pulse.push import push_status, scheduler_loop, send_digest
from us_market_pulse import share as public_share

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PORT = int(
    __import__("os").getenv("PORT")
    or __import__("os").getenv("PULSE_PORT", "8765")
    or "8765"
)


class SettingsUpdate(BaseModel):
    webhook_url: str | None = None
    webhook_format: str | None = None
    push_interval_minutes: int | None = None
    push_times: list[str] | str | None = None
    push_timezone: str | None = None
    push_enabled: bool | None = None
    push_secret: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_to: str | None = None
    smtp_from: str | None = None
    watch_keywords: list[str] | str | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    stop = asyncio.Event()
    task = asyncio.create_task(scheduler_loop(stop))
    try:
        yield
    finally:
        stop.set()
        await task


app = FastAPI(
    title="Pulse Desk",
    description="美股 · 政策 · 美联储 · 国债情报台",
    version="0.3.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "categories": CATEGORIES,
            "source_count": len(FEED_SOURCES),
        },
    )


@app.get("/api/intel")
async def api_intel(
    category: str = Query(default="all"),
    sentiment: str = Query(default="all"),
    sort: str = Query(default="bearish"),
    q: str | None = Query(default=None),
    watch_only: bool = Query(default=False),
    refresh: bool = Query(default=False),
) -> dict:
    data = await refresh_intel(force=refresh)
    items = filter_items(
        data["items"], category=category, q=q, sentiment=sentiment, sort=sort
    )
    if watch_only:
        items = [i for i in items if i.get("watch_hit")]
        items = filter_items(items, sort=sort)
    spotlight = bearish_spotlight(data["items"], limit=6)
    # Keep event threads aligned with filtered universe when possible
    item_event_ids = {i.get("event_id") for i in items if i.get("event_id")}
    event_threads = [
        e
        for e in (data.get("event_threads") or [])
        if e.get("id") in item_event_ids or not item_event_ids
    ][:16]
    return {
        "category": category,
        "sentiment": sentiment,
        "sort": sort,
        "q": q or "",
        "count": len(items),
        "items": items,
        "bearish_spotlight": spotlight,
        "indicators": data["indicators"],
        "calendar": data.get("calendar", []),
        "digest": data.get("digest", {}),
        "sentiment_summary": data.get("sentiment_summary", {}),
        "watch_hits": data.get("watch_hits", []),
        "events": data.get("events", []),
        "event_threads": event_threads,
        "timeline": data.get("timeline", []),
        "live_briefing": data.get("live_briefing") or {},
        "next_fomc": data.get("next_fomc"),
        "fetched_at": data["fetched_at"],
        "cached": data["cached"],
        "errors": data["errors"],
        "categories": CATEGORIES,
        "push": push_status(),
        "sources": [
            {"id": s["id"], "name": s["name"], "category": s["category"]}
            for s in FEED_SOURCES
        ],
    }


@app.get("/api/events/{event_id}")
async def api_event(event_id: str, refresh: bool = Query(default=False)) -> dict:
    if refresh or not get_event(event_id):
        await refresh_intel(force=refresh)
    event = get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="事件未找到")
    return {"event": event}


@app.get("/api/settings")
async def api_get_settings() -> dict[str, Any]:
    return load_settings().public_dict()


@app.put("/api/settings")
async def api_put_settings(body: SettingsUpdate) -> dict[str, Any]:
    patch = body.model_dump(exclude_unset=True)
    settings = save_settings(patch)
    clear_cache()
    return {
        "ok": True,
        "settings": settings.public_dict(),
        "push": push_status(settings),
    }


@app.get("/api/push/status")
async def api_push_status() -> dict:
    return push_status()


@app.post("/api/push/test")
async def api_push_test(
    x_pulse_secret: str | None = Header(default=None),
) -> dict:
    settings = load_settings()
    if settings.push_secret and x_pulse_secret != settings.push_secret:
        raise HTTPException(status_code=401, detail="Invalid push secret")
    if not settings.any_channel:
        raise HTTPException(
            status_code=400,
            detail="未配置推送渠道。请先在页面保存 Webhook 或邮件设置。",
        )
    return await send_digest(force_refresh=True, settings=settings, slot="manual")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/access")
async def api_access() -> dict:
    """URLs for opening the desk from phone on the same Wi-Fi / public tunnel."""
    port = DEFAULT_PORT
    urls = [f"http://127.0.0.1:{port}"]
    phone_urls = [f"http://{ip}:{port}" for ip in lan_ips()]
    urls.extend(phone_urls)
    share_st = public_share.status()
    public_url = share_st.get("url")
    if public_url:
        urls.insert(0, public_url)
    return {
        "port": port,
        "local": f"http://127.0.0.1:{port}",
        "phone": phone_urls,
        "public": public_url,
        "share": share_st,
        "urls": urls,
        "tip": (
            "公网链接已开启，手机/电脑任意网络都可打开（需本机服务保持运行）。"
            if public_url
            else "局域网需同一 Wi-Fi；也可点「开启公网分享」生成外网链接。"
        ),
    }


@app.get("/api/share")
async def api_share_status() -> dict:
    return public_share.status()


@app.post("/api/share/start")
async def api_share_start() -> dict:
    try:
        return await asyncio.to_thread(public_share.start, DEFAULT_PORT)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/share/stop")
async def api_share_stop() -> dict:
    return await asyncio.to_thread(public_share.stop)
