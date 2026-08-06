"""Pulse Desk — US market intelligence web app."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from us_market_pulse import lan_ips
from us_market_pulse.auth import (
    authenticate_user,
    current_user,
    current_username,
    login_session,
    logout_session,
    register_user,
    require_user,
    session_secret,
)
from us_market_pulse.config import load_settings, save_settings
from us_market_pulse.feeds import (
    CATEGORIES,
    FEED_SOURCES,
    bearish_spotlight,
    clear_cache,
    filter_items,
    get_event,
    peek_intel_items,
    refresh_intel,
    refresh_market_desk,
)
from us_market_pulse.earnings_calendar import (
    build_earnings_calendar,
    parse_day_param,
)
from us_market_pulse.market_map import build_market_map
from us_market_pulse.chains import build_chains_desk
from us_market_pulse.sectors import build_sector_desk, fetch_intraday_snapshot
from us_market_pulse.us_markets import build_us_markets_desk
from us_market_pulse.symbol_lookup import resolve_holding_query, suggest_holdings
from us_market_pulse.topics import build_war_desk
from us_market_pulse.portfolio import (
    MAX_HOLDINGS,
    add_holding,
    build_portfolio_view,
    load_portfolio,
    normalize_symbol,
    remove_holding,
    replace_holdings,
    resolve_and_normalize,
    select_holding,
    upgrade_selected_board,
)
from us_market_pulse.portfolio_intel import summarize_holding_intel
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


class HoldingIn(BaseModel):
    symbol: str
    name: str | None = None
    note: str | None = None


class PortfolioReplace(BaseModel):
    holdings: list[HoldingIn]
    selected: str | None = None


class AuthForm(BaseModel):
    username: str
    password: str = Field(min_length=1)
    display_name: str | None = None


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
    version="0.4.0",
    lifespan=lifespan,
)
# Render/Cloudflare terminate TLS; mark cookie Secure in production so browsers
# keep the session after login/register redirects.
_https_only = (
    __import__("os").getenv("RENDER", "").lower() in {"true", "1", "yes"}
    or __import__("os").getenv("PULSE_HTTPS_ONLY", "").lower()
    in {"true", "1", "yes"}
)
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret(),
    session_cookie="pulse_session",
    max_age=60 * 60 * 24 * 30,
    same_site="lax",
    https_only=_https_only,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _page(request: Request, template: str, page: str, **extra: Any) -> HTMLResponse:
    ctx = {
        "page": page,
        "categories": CATEGORIES,
        "source_count": len(FEED_SOURCES),
        "user": current_user(request),
        **extra,
    }
    response = templates.TemplateResponse(request, template, ctx)
    # Prevent SW/browser from sticky-caching logged-out shells after login
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return _page(request, "desk.html", "desk")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    if current_username(request):
        return RedirectResponse("/", status_code=303)
    return _page(request, "login.html", "login")


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request) -> HTMLResponse:
    """Alias so /register does not 404 — same desk as /login."""
    if current_username(request):
        return RedirectResponse("/", status_code=303)
    return RedirectResponse("/login?mode=register", status_code=303)


@app.get("/markets", response_class=HTMLResponse)
async def markets_page(request: Request) -> HTMLResponse:
    return _page(request, "markets.html", "markets")


@app.get("/sectors", response_class=HTMLResponse)
async def sectors_page(request: Request) -> HTMLResponse:
    return _page(request, "sectors.html", "sectors")


@app.get("/earnings", response_class=HTMLResponse)
async def earnings_page(request: Request) -> HTMLResponse:
    return _page(request, "earnings.html", "earnings")


@app.get("/intel", response_class=HTMLResponse)
async def intel_page(request: Request) -> HTMLResponse:
    return _page(request, "intel.html", "intel")


@app.get("/chains", response_class=HTMLResponse)
async def chains_page(request: Request) -> HTMLResponse:
    return _page(request, "chains.html", "chains")


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    return _page(request, "settings.html", "settings")


@app.get("/install", response_class=HTMLResponse)
async def install_page(request: Request) -> HTMLResponse:
    return _page(request, "install.html", "install")


@app.get("/sw.js")
async def service_worker() -> FileResponse:
    return FileResponse(
        BASE_DIR / "static" / "sw.js",
        media_type="application/javascript",
        headers={
            "Service-Worker-Allowed": "/",
            "Cache-Control": "no-cache",
        },
    )



@app.get("/api/auth/me")
async def api_auth_me(request: Request) -> dict[str, Any]:
    user = current_user(request)
    return {"ok": True, "authenticated": bool(user), "user": user}


@app.post("/api/auth/register")
async def api_auth_register(request: Request, body: AuthForm) -> dict[str, Any]:
    try:
        user = register_user(
            body.username, body.password, display_name=body.display_name or ""
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    login_session(request, user["username"])
    return {"ok": True, "user": user}


@app.post("/api/auth/login")
async def api_auth_login(request: Request, body: AuthForm) -> dict[str, Any]:
    try:
        user = authenticate_user(body.username, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    login_session(request, user["username"])
    return {"ok": True, "user": user}


@app.post("/api/auth/logout")
async def api_auth_logout(request: Request) -> dict[str, Any]:
    logout_session(request)
    return {"ok": True}


@app.get("/api/markets")
async def api_markets(refresh: bool = Query(default=False)) -> dict[str, Any]:
    return await refresh_market_desk(force=refresh)


@app.get("/api/sectors")
async def api_sectors(
    refresh: bool = Query(default=False),
    sector: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
) -> dict[str, Any]:
    # Soft-warm intel cache when empty so keyword fallbacks still work.
    # Sector/symbol cards primarily use on-demand Google News in build_sector_desk.
    items = peek_intel_items()
    if not items:
        intel = await refresh_intel(force=False)
        items = intel.get("items") or []
    desk = await build_sector_desk(
        items,
        force=refresh,
        selected_sector=sector,
        selected_symbol=symbol,
    )
    return desk


@app.get("/api/quote/intraday")
async def api_quote_intraday(
    symbol: str = Query(..., min_length=1, max_length=24),
    refresh: bool = Query(default=False),
) -> dict[str, Any]:
    """Shared Yahoo-first 分时 snapshot for holdings + sectors auto-refresh."""
    snap = await fetch_intraday_snapshot(symbol, force=refresh)
    if not snap:
        raise HTTPException(status_code=404, detail="暂无分时数据")
    return snap


@app.get("/api/sectors/map")
async def api_sectors_map(refresh: bool = Query(default=False)) -> dict[str, Any]:
    return await build_market_map(force=refresh)


@app.get("/api/us-markets")
async def api_us_markets(refresh: bool = Query(default=False)) -> dict[str, Any]:
    """US markets strip + NQ/ES/YM futures charts for the sectors page."""
    return await build_us_markets_desk(force=refresh)


@app.get("/api/earnings")
async def api_earnings(
    date: str | None = Query(default=None),
    days: int = Query(default=31, ge=1, le=31),
    q: str | None = Query(default=None),
    session: str | None = Query(default=None),
    refresh: bool = Query(default=False),
) -> dict[str, Any]:
    day = parse_day_param(date)
    return await build_earnings_calendar(
        day=day,
        days=days,
        q=q,
        session=session,
        force=refresh,
    )


@app.get("/api/portfolio/intel")
async def api_portfolio_intel(
    request: Request,
    symbol: str | None = Query(default=None),
    refresh: bool = Query(default=False),
    limit: int = Query(default=24, ge=1, le=60),
) -> dict[str, Any]:
    """Intel stories linked to current portfolio holdings."""
    username = require_user(request)
    data = await refresh_intel(force=refresh)
    portfolio = load_portfolio(username)
    summary = summarize_holding_intel(
        data.get("items") or [],
        portfolio.get("holdings") or [],
        symbol=symbol,
        limit=limit,
    )
    return {
        "ok": True,
        "holdings": portfolio.get("holdings") or [],
        "portfolio_selected": portfolio.get("selected") or "",
        "owner": username,
        "fetched_at": data.get("fetched_at"),
        "cached": data.get("cached"),
        "errors": data.get("errors") or [],
        **summary,
    }


@app.get("/api/chains")
async def api_chains(
    chain: str | None = Query(default=None),
    node: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> dict[str, Any]:
    return await build_chains_desk(chain_id=chain, node_id=node, q=q)


@app.get("/api/intel")
async def api_intel(
    request: Request,
    category: str = Query(default="all"),
    sentiment: str = Query(default="all"),
    sort: str = Query(default="bearish"),
    q: str | None = Query(default=None),
    watch_only: bool = Query(default=False),
    holdings_only: bool = Query(default=False),
    holding: str | None = Query(default=None),
    refresh: bool = Query(default=False),
) -> dict:
    data = await refresh_intel(force=refresh)
    username = current_username(request)
    portfolio = load_portfolio(username) if username else {"holdings": [], "selected": ""}
    holding_summary = summarize_holding_intel(
        data.get("items") or [],
        portfolio.get("holdings") or [],
        symbol=None,
        limit=80,
    )
    items = filter_items(
        data["items"], category=category, q=q, sentiment=sentiment, sort=sort
    )
    selected_holding = (holding or "").strip().upper() or None
    if holdings_only or selected_holding:
        items = [
            i
            for i in items
            if i.get("holding_hit")
            and (
                not selected_holding
                or selected_holding in (i.get("holding_matches") or [])
            )
        ]
        items = filter_items(items, sort=sort)
        holding_summary = {
            **holding_summary,
            "selected": selected_holding or "",
            "count": len(items),
            "items": items[:80],
        }
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
    war_desk = build_war_desk(
        data.get("items") or [],
        data.get("event_threads") or [],
    )
    return {
        "category": category,
        "sentiment": sentiment,
        "sort": sort,
        "q": q or "",
        "count": len(items),
        "items": items,
        "bearish_spotlight": spotlight,
        "war_desk": war_desk,
        "indicators": data["indicators"],
        "calendar": data.get("calendar", []),
        "digest": data.get("digest", {}),
        "sentiment_summary": data.get("sentiment_summary", {}),
        "watch_hits": data.get("watch_hits", []),
        "holding_intel": holding_summary,
        "holdings_only": holdings_only,
        "holding": (holding or "").upper(),
        "events": data.get("events", []),
        "event_threads": event_threads,
        "timeline": data.get("timeline", []),
        "live_briefing": data.get("live_briefing") or {},
        "markets": data.get("markets") or {"indices": [], "charts": []},
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


@app.get("/api/portfolio/lookup")
async def api_portfolio_lookup(
    q: str = Query(default=""),
    limit: int = Query(default=8, ge=1, le=20),
) -> dict[str, Any]:
    query = (q or "").strip()
    resolved = resolve_holding_query(query) if query else None
    return {
        "ok": True,
        "q": query,
        "resolved": resolved,
        "suggestions": suggest_holdings(query, limit=limit) if query else [],
    }


@app.get("/api/portfolio/symbols")
async def api_portfolio_symbols(request: Request) -> dict[str, Any]:
    """Lightweight holdings symbols for cross-page +/- tags (no quotes)."""
    username = require_user(request)
    data = load_portfolio(username)
    symbols = [
        str(h.get("symbol") or "").upper()
        for h in (data.get("holdings") or [])
        if str(h.get("symbol") or "").strip()
    ]
    return {
        "symbols": symbols,
        "selected": str(data.get("selected") or "").upper(),
        "count": len(symbols),
        "updated_at": data.get("updated_at") or 0,
    }


@app.get("/api/portfolio")
async def api_portfolio(
    request: Request, refresh: bool = Query(default=False)
) -> dict[str, Any]:
    username = require_user(request)
    try:
        view = await asyncio.wait_for(
            build_portfolio_view(username, force_refresh=refresh),
            timeout=45.0,
        )
    except Exception as exc:  # noqa: BLE001
        view = _portfolio_stub_view(username)
        view["errors"] = [f"持仓行情暂不可用：{exc}"]
        view["note"] = "持仓列表已加载；行情稍后自动刷新。"
    view["user"] = current_user(request)
    return view


def _portfolio_stub_view(username: str, *, selected: str = "") -> dict[str, Any]:
    """Return holdings immediately without waiting on quote/earnings fetches."""
    data = load_portfolio(username)
    holdings = data.get("holdings") or []
    pick = selected or data.get("selected") or (
        holdings[0]["symbol"] if holdings else ""
    )
    cards: list[dict[str, Any]] = []
    for h in holdings:
        sym = h.get("symbol") or ""
        cards.append(
            {
                **h,
                "price": None,
                "change": None,
                "change_pct": None,
                "as_of": None,
                "points": [],
                "series": {},
                "label": h.get("name") or sym,
                "url": f"https://finance.yahoo.com/quote/{sym}" if sym else "",
            }
        )
    selected_card = next((c for c in cards if c.get("symbol") == pick), None)
    if selected_card is None and cards:
        selected_card = cards[0]
        pick = selected_card.get("symbol") or ""
    return {
        "updated_at": data.get("updated_at") or 0,
        "selected": pick,
        "selected_symbol": pick,
        "holdings": cards,
        "selected_board": selected_card,
        "board": selected_card,
        "selected_earnings": None,
        "value_chain": None,
        "earnings_calendar": [],
        "timeframes": [
            {"id": "intraday", "label": "分时", "blurb": "", "chart": "line"},
            {"id": "day", "label": "日图", "blurb": "", "chart": "candle"},
            {"id": "month", "label": "月图", "blurb": "", "chart": "candle"},
            {"id": "quarter", "label": "季图", "blurb": "", "chart": "candle"},
        ],
        "default_tf": "intraday",
        "max_holdings": MAX_HOLDINGS,
        "owner": str(username).strip().lower(),
        "errors": [],
        "note": "持仓已保存；行情稍后自动刷新。",
        "style": {"up": "red", "down": "green"},
    }


@app.post("/api/portfolio/add")
async def api_portfolio_add(request: Request, body: HoldingIn) -> dict[str, Any]:
    username = require_user(request)
    symbol, canonical = resolve_and_normalize(body.symbol)
    try:
        if not symbol:
            raise ValueError(
                "无法识别。可输入美股代码（如 AAPL）或中文名（如 苹果 / 亚马逊 / 英伟达）。"
            )
        add_holding(
            username,
            symbol,
            name=body.name or canonical or "",
            note=body.note or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Instant ack — never wait on Yahoo/Nasdaq for +/− from the sectors desk.
    # Holdings page refreshes quotes via /api/portfolio separately.
    view = _portfolio_stub_view(username, selected=symbol)
    view["user"] = current_user(request)
    return {
        "ok": True,
        "portfolio": view,
        "resolved": {"symbol": symbol, "name": canonical or symbol},
    }


@app.post("/api/portfolio/remove")
async def api_portfolio_remove(request: Request, body: HoldingIn) -> dict[str, Any]:
    username = require_user(request)
    try:
        remove_holding(username, body.symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    view = _portfolio_stub_view(username)
    view["user"] = current_user(request)
    return {"ok": True, "portfolio": view}


@app.post("/api/portfolio/select")
async def api_portfolio_select(request: Request, body: HoldingIn) -> dict[str, Any]:
    username = require_user(request)
    try:
        select_holding(username, body.symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Fast path: only upgrade the selected board (no full-list Yahoo round-trip).
    sym = normalize_symbol(body.symbol)
    try:
        upgraded = await asyncio.wait_for(
            upgrade_selected_board(username, sym, force=False),
            timeout=16.0,
        )
    except Exception as exc:  # noqa: BLE001
        upgraded = {
            "selected": sym,
            "selected_symbol": sym,
            "selected_board": None,
            "errors": [str(exc)],
        }
    return {
        "ok": True,
        "selected": upgraded.get("selected") or sym,
        "selected_symbol": upgraded.get("selected_symbol")
        or upgraded.get("selected")
        or sym,
        "selected_board": upgraded.get("selected_board"),
        "board": upgraded.get("board") or upgraded.get("selected_board"),
        "selected_earnings": upgraded.get("selected_earnings"),
        "value_chain": upgraded.get("value_chain"),
        "errors": upgraded.get("errors") or [],
        "user": current_user(request),
    }


@app.put("/api/portfolio")
async def api_portfolio_replace(
    request: Request, body: PortfolioReplace
) -> dict[str, Any]:
    username = require_user(request)
    rows = [h.model_dump() for h in body.holdings]
    replace_holdings(username, rows, selected=body.selected or "")
    view = await build_portfolio_view(username, force_refresh=True)
    view["user"] = current_user(request)
    return {"ok": True, "portfolio": view}


@app.get("/api/portfolio/export")
async def api_portfolio_export(request: Request) -> dict[str, Any]:
    username = require_user(request)
    data = load_portfolio(username)
    return {"ok": True, "portfolio": data, "owner": username}


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
