"""US market-wide earnings calendar via Nasdaq public calendar API."""

from __future__ import annotations

import asyncio
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
NASDAQ_EARNINGS_URL = "https://api.nasdaq.com/api/calendar/earnings"
ET = ZoneInfo("America/New_York")

_CACHE: dict[str, Any] = {"by_date": {}, "fetched_at": {}}
_CACHE_TTL = 30 * 60  # 30 minutes per day bucket
_FETCH_CONCURRENCY = 6
_MAX_WINDOW_DAYS = 31
_UPCOMING: dict[str, Any] = {"by_symbol": {}, "fetched_at": 0.0}
_UPCOMING_TTL = 30 * 60
_UPCOMING_DAYS = 75

_TIME_LABELS = {
    "time-pre-market": "盘前",
    "time-after-hours": "盘后",
    "time-not-supplied": "时段未定",
}

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MDY_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def _normalize_date_label(raw: Any) -> str:
    """Unify earnings date labels to YYYY-MM-DD when parseable."""
    text = str(raw or "").strip()
    if not text or text in {"—", "-", "N/A", "n/a"}:
        return ""
    if _ISO_DATE_RE.match(text):
        return text
    m = _MDY_DATE_RE.match(text)
    if m:
        month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return text
    return text

# Always elevate these names when they report in-window
_FOCUS_SYMBOLS = {
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "GOOGL",
    "GOOG",
    "META",
    "TSLA",
    "AVGO",
    "AMD",
    "TSM",
    "ASML",
    "ORCL",
    "CRM",
    "NFLX",
    "COST",
    "JPM",
    "BAC",
    "XOM",
    "CVX",
    "LLY",
    "UNH",
    "V",
    "MA",
    "PLTR",
    "SMCI",
    "MU",
    "QCOM",
    "INTC",
    "IBM",
    "NOW",
    "SNOW",
    "ARM",
    "WMT",
    "HD",
    "DIS",
    "BA",
    "CAT",
    "GE",
}


def _headers() -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.nasdaq.com",
        "Referer": "https://www.nasdaq.com/market-activity/earnings",
    }


def today_et(now: datetime | None = None) -> date:
    stamp = now or datetime.now(tz=ET)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc).astimezone(ET)
    else:
        stamp = stamp.astimezone(ET)
    return stamp.date()


def _parse_money(text: str | None) -> float | None:
    if text is None:
        return None
    raw = str(text).strip()
    if not raw or raw in {"N/A", "n/a", "--", "-"}:
        return None
    neg = raw.startswith("(") and raw.endswith(")")
    cleaned = raw.replace("$", "").replace(",", "").replace("(", "").replace(")", "")
    mult = 1.0
    if cleaned.endswith(("B", "b")):
        mult = 1e9
        cleaned = cleaned[:-1]
    elif cleaned.endswith(("M", "m")):
        mult = 1e6
        cleaned = cleaned[:-1]
    elif cleaned.endswith(("T", "t")):
        mult = 1e12
        cleaned = cleaned[:-1]
    try:
        value = float(cleaned) * mult
    except ValueError:
        return None
    return -value if neg else value


def _normalize_row(row: dict[str, Any], report_date: str) -> dict[str, Any]:
    symbol = str(row.get("symbol") or "").strip().upper()
    time_key = str(row.get("time") or "time-not-supplied")
    market_cap = _parse_money(row.get("marketCap"))
    eps_forecast = _parse_money(row.get("epsForecast"))
    last_eps = _parse_money(row.get("lastYearEPS"))
    yoy_pct = None
    if eps_forecast is not None and last_eps not in (None, 0):
        try:
            yoy_pct = round((eps_forecast - last_eps) / abs(last_eps) * 100.0, 2)
        except (TypeError, ValueError, ZeroDivisionError):
            yoy_pct = None
    try:
        n_ests = int(str(row.get("noOfEsts") or "0").replace(",", "") or "0")
    except ValueError:
        n_ests = 0
    last_year_date = _normalize_date_label(row.get("lastYearRptDt"))
    next_date = _normalize_date_label(report_date) or str(report_date or "").strip()
    return {
        "symbol": symbol,
        "name": str(row.get("name") or symbol).strip(),
        "date": next_date,
        "time": time_key,
        "time_zh": _TIME_LABELS.get(time_key, "时段未定"),
        "market_cap": market_cap,
        "market_cap_text": str(row.get("marketCap") or "—"),
        "eps_forecast": eps_forecast,
        "eps_forecast_text": str(row.get("epsForecast") or "—"),
        "last_year_eps": last_eps,
        "last_year_eps_text": str(row.get("lastYearEPS") or "—"),
        "yoy_pct": yoy_pct,
        "last_year_report_date": last_year_date,
        "prev_earnings_label": last_year_date or "",
        "next_earnings_label": next_date,
        "fiscal_quarter_ending": str(row.get("fiscalQuarterEnding") or ""),
        "estimate_count": n_ests,
        "url": f"https://finance.yahoo.com/quote/{symbol}/" if symbol else "",
    }


def _focus_score(row: dict[str, Any]) -> float:
    """Higher = more worth watching in the earnings window."""
    score = 0.0
    cap = row.get("market_cap")
    try:
        cap_f = float(cap) if cap is not None else 0.0
    except (TypeError, ValueError):
        cap_f = 0.0
    if cap_f >= 200e9:
        score += 6.0
    elif cap_f >= 100e9:
        score += 5.0
    elif cap_f >= 50e9:
        score += 4.0
    elif cap_f >= 20e9:
        score += 3.0
    elif cap_f >= 5e9:
        score += 1.5

    sym = str(row.get("symbol") or "").upper()
    if sym in _FOCUS_SYMBOLS:
        score += 3.5

    yoy = row.get("yoy_pct")
    try:
        yoy_f = abs(float(yoy)) if yoy is not None else 0.0
    except (TypeError, ValueError):
        yoy_f = 0.0
    if yoy_f >= 80:
        score += 2.5
    elif yoy_f >= 40:
        score += 1.5
    elif yoy_f >= 20:
        score += 0.8

    try:
        n_est = int(row.get("estimate_count") or 0)
    except (TypeError, ValueError):
        n_est = 0
    if n_est >= 20:
        score += 1.2
    elif n_est >= 10:
        score += 0.6

    # Prefer named session over unknown
    if row.get("time") in {"time-pre-market", "time-after-hours"}:
        score += 0.3
    return round(score, 3)


def _focus_reasons(row: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    cap = row.get("market_cap")
    try:
        cap_f = float(cap) if cap is not None else 0.0
    except (TypeError, ValueError):
        cap_f = 0.0
    if cap_f >= 100e9:
        reasons.append("超大市值")
    elif cap_f >= 50e9:
        reasons.append("大市值")
    elif cap_f >= 20e9:
        reasons.append("中大市值")

    if str(row.get("symbol") or "").upper() in _FOCUS_SYMBOLS:
        reasons.append("核心标的")

    yoy = row.get("yoy_pct")
    try:
        yoy_f = float(yoy) if yoy is not None else None
    except (TypeError, ValueError):
        yoy_f = None
    if yoy_f is not None and abs(yoy_f) >= 40:
        reasons.append(f"预期同比 {yoy_f:+.0f}%")
    elif yoy_f is not None and abs(yoy_f) >= 20:
        reasons.append(f"同比变化 {yoy_f:+.0f}%")

    try:
        n_est = int(row.get("estimate_count") or 0)
    except (TypeError, ValueError):
        n_est = 0
    if n_est >= 15:
        reasons.append(f"{n_est} 家机构覆盖")

    if row.get("time_zh") in {"盘前", "盘后"}:
        reasons.append(str(row["time_zh"]))
    return reasons[:4]


def _attach_focus(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in rows:
        score = _focus_score(row)
        row["focus_score"] = score
        row["focus_reasons"] = _focus_reasons(row)
        row["is_focus"] = False
    return rows


async def fetch_earnings_for_date(
    client: httpx.AsyncClient,
    day: date,
    *,
    force: bool = False,
    sem: asyncio.Semaphore | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    key = day.isoformat()
    cached_at = float(_CACHE["fetched_at"].get(key) or 0)
    if (
        not force
        and key in _CACHE["by_date"]
        and time.time() - cached_at < _CACHE_TTL
    ):
        return list(_CACHE["by_date"][key]), None

    async def _do() -> tuple[list[dict[str, Any]], str | None]:
        try:
            resp = await client.get(
                NASDAQ_EARNINGS_URL,
                params={"date": key},
                headers=_headers(),
                timeout=30.0,
            )
            resp.raise_for_status()
            payload = resp.json() or {}
            rows_raw = ((payload.get("data") or {}).get("rows")) or []
            rows = [_normalize_row(row, key) for row in rows_raw if row.get("symbol")]
            rows = _attach_focus(rows)
            rows.sort(
                key=lambda r: (
                    -(r.get("focus_score") or 0),
                    -(r.get("market_cap") or 0),
                    r.get("symbol") or "",
                )
            )
            _CACHE["by_date"][key] = rows
            _CACHE["fetched_at"][key] = time.time()
            return rows, None
        except Exception as exc:  # noqa: BLE001
            stale = list(_CACHE["by_date"].get(key) or [])
            return stale, f"earnings {key}: {exc}"

    if sem is None:
        return await _do()
    async with sem:
        return await _do()


def _daterange(start: date, end: date, *, max_days: int = _MAX_WINDOW_DAYS) -> list[date]:
    if end < start:
        start, end = end, start
    span = min((end - start).days, max(0, max_days - 1))
    return [start + timedelta(days=i) for i in range(span + 1)]


def _build_focus_watch(
    rows: list[dict[str, Any]], *, limit: int = 24
) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda r: (
            -(r.get("focus_score") or 0),
            -(r.get("market_cap") or 0),
            r.get("date") or "",
            r.get("symbol") or "",
        ),
    )
    # Deduplicate by symbol (keep earliest / highest-score occurrence)
    seen: set[str] = set()
    focus: list[dict[str, Any]] = []
    for row in ranked:
        sym = str(row.get("symbol") or "")
        if not sym or sym in seen:
            continue
        # Threshold: keep meaningful names, not the whole tape
        score = float(row.get("focus_score") or 0)
        cap = float(row.get("market_cap") or 0)
        if score < 2.5 and cap < 50e9 and sym not in _FOCUS_SYMBOLS:
            continue
        if score < 3.5 and len(focus) >= 12 and cap < 50e9:
            continue
        seen.add(sym)
        item = dict(row)
        item["is_focus"] = True
        focus.append(item)
        if len(focus) >= limit:
            break

    # Ensure top mega names aren't missed if score edge-case
    focus_syms = {r["symbol"] for r in focus}
    for row in ranked:
        sym = str(row.get("symbol") or "")
        if sym in focus_syms:
            continue
        if float(row.get("market_cap") or 0) >= 100e9 or sym in _FOCUS_SYMBOLS:
            item = dict(row)
            item["is_focus"] = True
            focus.append(item)
            focus_syms.add(sym)
        if len(focus) >= limit:
            break

    focus.sort(key=lambda r: (r.get("date") or "", -(r.get("focus_score") or 0)))
    return focus[:limit]


async def build_earnings_calendar(
    *,
    day: date | None = None,
    days: int = 31,
    q: str | None = None,
    session: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Market-wide earnings calendar (Nasdaq): today→~1 month ET."""
    today = today_et()
    selected = day or today
    window_days = max(1, min(int(days or 31), _MAX_WINDOW_DAYS))
    dates = _daterange(today, today + timedelta(days=window_days - 1))
    if selected not in dates:
        # Keep month window anchored at today; still allow selecting outside via extra fetch
        dates = sorted({*dates, selected})
    errors: list[str] = []
    sem = asyncio.Semaphore(_FETCH_CONCURRENCY)

    async with httpx.AsyncClient(follow_redirects=True, trust_env=False) as client:
        results = await asyncio.gather(
            *[
                fetch_earnings_for_date(client, d, force=force, sem=sem)
                for d in dates
            ]
        )

    by_date: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    for d, (rows, err) in zip(dates, results, strict=True):
        if err:
            errors.append(err)
        # Re-attach focus scores if served from older cache shape
        rows = _attach_focus(rows)
        focus_n = sum(1 for r in rows if float(r.get("focus_score") or 0) >= 3.5)
        by_date.append(
            {
                "date": d.isoformat(),
                "label": d.strftime("%m/%d"),
                "weekday": ["一", "二", "三", "四", "五", "六", "日"][d.weekday()],
                "count": len(rows),
                "focus_count": focus_n,
                "is_today": d == today,
                "is_selected": d == selected,
                "is_weekend": d.weekday() >= 5,
            }
        )
        all_rows.extend(rows)

    needle = (q or "").strip().casefold()
    session_key = (session or "all").strip().lower()
    if session_key not in {"pre", "post", "all"}:
        session_key = "all"

    def _passes(row: dict[str, Any]) -> bool:
        if needle and needle not in (row.get("symbol") or "").casefold() and needle not in (
            row.get("name") or ""
        ).casefold():
            return False
        if session_key == "pre" and row.get("time") != "time-pre-market":
            return False
        if session_key == "post" and row.get("time") != "time-after-hours":
            return False
        return True

    filtered_window = [r for r in all_rows if _passes(r)]
    focus_watch = _build_focus_watch(filtered_window, limit=24)
    focus_syms = {r.get("symbol") for r in focus_watch}

    for row in filtered_window:
        row["is_focus"] = row.get("symbol") in focus_syms

    selected_date = selected.isoformat()
    selected_rows = [r for r in filtered_window if r.get("date") == selected_date]
    selected_rows.sort(
        key=lambda r: (
            0 if r.get("is_focus") else 1,
            -(r.get("focus_score") or 0),
            -(r.get("market_cap") or 0),
            r.get("symbol") or "",
        )
    )

    count_by_date = {d.isoformat(): 0 for d in dates}
    focus_by_date = {d.isoformat(): 0 for d in dates}
    for row in filtered_window:
        key = row.get("date") or ""
        if key in count_by_date:
            count_by_date[key] += 1
        if key in focus_by_date and row.get("is_focus"):
            focus_by_date[key] += 1
    for entry in by_date:
        entry["count"] = count_by_date.get(entry["date"], 0)
        entry["focus_count"] = focus_by_date.get(entry["date"], 0)

    mega = [r for r in selected_rows if (r.get("market_cap") or 0) >= 50e9][:12]
    selected_focus = [r for r in selected_rows if r.get("is_focus")][:12]

    return {
        "as_of": datetime.now(tz=ET).isoformat(),
        "timezone": "America/New_York",
        "source": "Nasdaq Earnings Calendar",
        "source_url": "https://www.nasdaq.com/market-activity/earnings",
        "day": selected_date,
        "days": window_days,
        "window_start": dates[0].isoformat() if dates else today.isoformat(),
        "window_end": dates[-1].isoformat() if dates else today.isoformat(),
        "q": q or "",
        "session": session_key,
        "dates": by_date,
        "selected_date": selected_date,
        "count": len(selected_rows),
        "total_window": len(filtered_window),
        "focus_count": len(focus_watch),
        "items": selected_rows,
        "mega_caps": mega,
        "focus_watch": focus_watch,
        "selected_focus": selected_focus,
        "errors": errors[-30:],
        "cached": any(
            time.time() - float(_CACHE["fetched_at"].get(d.isoformat()) or 0) < _CACHE_TTL
            for d in dates
        ),
    }


async def build_earnings_day(
    day: date | None = None,
    *,
    q: str | None = None,
    session: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    return await build_earnings_calendar(
        day=day, days=1, q=q, session=session, force=force
    )


def parse_day_param(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def peek_upcoming_earnings_map() -> dict[str, dict[str, Any]]:
    """Return cached upcoming map only — never triggers a network refresh."""
    return dict(_UPCOMING.get("by_symbol") or {})


async def get_upcoming_earnings_map(
    *, force: bool = False, days: int = _UPCOMING_DAYS
) -> dict[str, dict[str, Any]]:
    """Symbol → earliest upcoming Nasdaq calendar row (cached)."""
    now = time.time()
    if (
        not force
        and _UPCOMING["by_symbol"]
        and now - float(_UPCOMING["fetched_at"] or 0) < _UPCOMING_TTL
    ):
        return dict(_UPCOMING["by_symbol"])

    start = today_et()
    end = start + timedelta(days=max(1, days))
    days_list = [
        d for d in _daterange(start, end, max_days=max(1, days) + 1) if d.weekday() < 5
    ]
    sem = asyncio.Semaphore(_FETCH_CONCURRENCY)
    by_symbol: dict[str, dict[str, Any]] = {}
    async with httpx.AsyncClient(follow_redirects=True, trust_env=False) as client:
        results = await asyncio.gather(
            *[
                fetch_earnings_for_date(client, day, force=force, sem=sem)
                for day in days_list
            ]
        )
    for rows, _err in results:
        for row in rows:
            sym = str(row.get("symbol") or "").upper()
            if not sym or sym in by_symbol:
                continue
            by_symbol[sym] = row

    _UPCOMING["by_symbol"] = by_symbol
    _UPCOMING["fetched_at"] = now
    return dict(by_symbol)


async def lookup_upcoming_earnings(
    symbol: str, *, force: bool = False
) -> dict[str, Any] | None:
    sym = (symbol or "").strip().upper()
    if not sym:
        return None
    mapping = await get_upcoming_earnings_map(force=force)
    row = mapping.get(sym)
    return dict(row) if row else None
