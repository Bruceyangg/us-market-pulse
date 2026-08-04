"""US market-wide earnings calendar via Nasdaq public calendar API."""

from __future__ import annotations

import asyncio
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

_TIME_LABELS = {
    "time-pre-market": "盘前",
    "time-after-hours": "盘后",
    "time-not-supplied": "时段未定",
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
    try:
        n_ests = int(str(row.get("noOfEsts") or "0").replace(",", "") or "0")
    except ValueError:
        n_ests = 0
    return {
        "symbol": symbol,
        "name": str(row.get("name") or symbol).strip(),
        "date": report_date,
        "time": time_key,
        "time_zh": _TIME_LABELS.get(time_key, "时段未定"),
        "market_cap": market_cap,
        "market_cap_text": str(row.get("marketCap") or "—"),
        "eps_forecast": eps_forecast,
        "eps_forecast_text": str(row.get("epsForecast") or "—"),
        "last_year_eps": last_eps,
        "last_year_eps_text": str(row.get("lastYearEPS") or "—"),
        "last_year_report_date": str(row.get("lastYearRptDt") or ""),
        "fiscal_quarter_ending": str(row.get("fiscalQuarterEnding") or ""),
        "estimate_count": n_ests,
        "url": f"https://finance.yahoo.com/quote/{symbol}/" if symbol else "",
    }


async def fetch_earnings_for_date(
    client: httpx.AsyncClient,
    day: date,
    *,
    force: bool = False,
) -> tuple[list[dict[str, Any]], str | None]:
    key = day.isoformat()
    cached_at = float(_CACHE["fetched_at"].get(key) or 0)
    if (
        not force
        and key in _CACHE["by_date"]
        and time.time() - cached_at < _CACHE_TTL
    ):
        return list(_CACHE["by_date"][key]), None

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
        rows.sort(
            key=lambda r: (
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


def _daterange(start: date, end: date) -> list[date]:
    if end < start:
        start, end = end, start
    # hard cap to keep Nasdaq calls reasonable
    span = min((end - start).days, 21)
    return [start + timedelta(days=i) for i in range(span + 1)]


async def build_earnings_calendar(
    *,
    day: date | None = None,
    days: int = 7,
    q: str | None = None,
    session: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Market-wide earnings calendar (Nasdaq): today→N days ET, select one day."""
    today = today_et()
    selected = day or today
    window_days = max(1, min(int(days or 7), 14))
    dates = _daterange(today, today + timedelta(days=window_days - 1))
    if selected not in dates:
        dates = sorted({*dates, selected})
    errors: list[str] = []

    async with httpx.AsyncClient(follow_redirects=True, trust_env=False) as client:
        results = await asyncio.gather(
            *[fetch_earnings_for_date(client, d, force=force) for d in dates]
        )

    by_date: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    for d, (rows, err) in zip(dates, results, strict=True):
        if err:
            errors.append(err)
        by_date.append(
            {
                "date": d.isoformat(),
                "label": d.strftime("%m/%d"),
                "weekday": ["一", "二", "三", "四", "五", "六", "日"][d.weekday()],
                "count": len(rows),
                "is_today": d == today,
                "is_selected": d == selected,
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
    selected_date = selected.isoformat()
    selected_rows = [r for r in filtered_window if r.get("date") == selected_date]
    selected_rows.sort(
        key=lambda r: (-(r.get("market_cap") or 0), r.get("symbol") or "")
    )

    # Refresh tab counts under active filters
    count_by_date = {d.isoformat(): 0 for d in dates}
    for row in filtered_window:
        key = row.get("date") or ""
        if key in count_by_date:
            count_by_date[key] += 1
    for entry in by_date:
        entry["count"] = count_by_date.get(entry["date"], 0)

    mega = [r for r in selected_rows if (r.get("market_cap") or 0) >= 50e9][:12]
    return {
        "as_of": datetime.now(tz=ET).isoformat(),
        "timezone": "America/New_York",
        "source": "Nasdaq Earnings Calendar",
        "source_url": "https://www.nasdaq.com/market-activity/earnings",
        "day": selected_date,
        "days": window_days,
        "q": q or "",
        "session": session_key,
        "dates": by_date,
        "selected_date": selected_date,
        "count": len(selected_rows),
        "total_window": len(filtered_window),
        "items": selected_rows,
        "mega_caps": mega,
        "errors": errors[-20:],
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
