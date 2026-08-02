"""Digest formatting and outbound push (webhook / email)."""

from __future__ import annotations

import asyncio
import logging
import smtplib
import time
from datetime import datetime
from email.mime.text import MIMEText
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from us_market_pulse.config import Settings, load_settings
from us_market_pulse.feeds import refresh_intel

logger = logging.getLogger(__name__)

_LAST_PUSH: dict[str, Any] = {
    "ok": None,
    "at": None,
    "channels": [],
    "error": None,
    "slot": None,
}
_PUSHED_SLOTS: set[str] = set()
_INTERVAL_BOOTSTRAPPED = False


def push_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or load_settings()
    return {
        "enabled": settings.push_enabled,
        "webhook_configured": settings.webhook_configured,
        "email_configured": settings.email_configured,
        "webhook_format": settings.resolved_webhook_format,
        "interval_minutes": settings.push_interval_minutes,
        "times": list(settings.push_times),
        "timezone": settings.push_timezone,
        "watch_keywords": list(settings.watch_keywords),
        "settings": settings.public_dict(),
        "last": _LAST_PUSH,
        "requires_secret": bool(settings.push_secret),
    }


def format_digest_text(data: dict[str, Any]) -> str:
    indicators = data.get("indicators") or []
    calendar = data.get("calendar") or []
    digest = data.get("digest") or {}
    sentiment = data.get("sentiment_summary") or {}
    items = data.get("items") or []
    watch_hits = data.get("watch_hits") or []
    next_fomc = data.get("next_fomc")

    live = data.get("live_briefing") or {}
    direction = live.get("direction") or {}

    lines = [
        "Pulse Desk 定时简报",
        "================",
        digest.get("summary") or "",
        sentiment.get("blurb") or "",
    ]
    if live.get("overview") or live.get("summary"):
        lines.extend(
            [
                "",
                f"【近{live.get('window_hours', 12):g}小时利空速评】",
                "事件概述：",
                live.get("overview") or live.get("summary") or "",
                "利空评判：",
                live.get("assessment")
                or f"{direction.get('change_zh') or ''} · {direction.get('bias_zh') or ''}",
            ]
        )
        for driver in (live.get("drivers") or [])[:3]:
            title = driver.get("title_zh") or driver.get("title") or ""
            lines.append(f"- [{driver.get('sentiment_label') or '利空'}] {title}")
    lines.extend(
        [
            "",
            "【交易台读数】",
        ]
    )
    for row in indicators:
        unit = "%" if row.get("unit") == "%" else ""
        delta = row.get("delta")
        delta_s = f" ({delta:+.3f})" if isinstance(delta, (int, float)) else ""
        lines.append(f"- {row.get('label')}: {row.get('value')}{unit}{delta_s}")

    if next_fomc:
        lines.extend(
            [
                "",
                "【下一场 FOMC】",
                f"- {next_fomc.get('label')}: {next_fomc.get('end')}（还有 {next_fomc.get('days_until')} 天）",
            ]
        )

    if calendar:
        lines.extend(["", "【政策日程 · 利空/利多评判】"])
        for ev in calendar[:5]:
            label = ev.get("sentiment_label") or "中性"
            lines.append(f"- {ev.get('date')} [{label}] {ev.get('title')}")
            if ev.get("bear_case"):
                lines.append(f"  利空：{ev.get('bear_case')}")
            if ev.get("bull_case"):
                lines.append(f"  利多：{ev.get('bull_case')}")

    if watch_hits:
        lines.extend(["", "【盯盘命中】"])
        for item in watch_hits[:8]:
            keys = ",".join(item.get("watch_matches") or [])
            label = item.get("sentiment_label") or "中性"
            title_zh = item.get("title_zh") or item.get("title") or ""
            title_en = item.get("title") or ""
            lines.append(f"- [{label}] ({keys}) {title_zh}")
            if title_en and title_en != title_zh:
                lines.append(f"  EN: {title_en}")

    lines.extend(["", "【利多头条】"])
    for row in sentiment.get("top_bullish") or []:
        lines.append(f"- [{row.get('label')}] {row.get('title')}")
    if not sentiment.get("top_bullish"):
        lines.append("- （暂无）")

    lines.extend(["", "【利空头条】"])
    for row in sentiment.get("top_bearish") or []:
        lines.append(f"- [{row.get('label')}] {row.get('title')}")
    if not sentiment.get("top_bearish"):
        lines.append("- （暂无）")

    event_threads = data.get("event_threads") or []
    if event_threads:
        lines.extend(["", "【同一事件追踪】"])
        for event in event_threads[:4]:
            title_zh = event.get("title_zh") or event.get("title") or ""
            lines.append(
                f"- [{event.get('sentiment_label') or '中性'}] {event.get('count')}条 · {title_zh}"
            )

    lines.extend(["", "【最新情报】"])
    for item in items[:6]:
        label = item.get("sentiment_label") or "中性"
        title_zh = item.get("title_zh") or item.get("title") or ""
        lines.append(f"- [{label}] {title_zh}")
        title_en = item.get("title") or ""
        if title_en and title_en != title_zh:
            lines.append(f"  EN: {title_en}")

    lines.extend(
        [
            "",
            "说明：利多/利空为规则引擎对美股风险偏好的启发式判断，不构成投资建议。",
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]
    )
    return "\n".join(lines)


def _webhook_payload(fmt: str, text: str) -> dict[str, Any]:
    title = "Pulse Desk 简报"
    short = text if len(text) <= 3500 else text[:3490] + "…"

    if fmt == "discord":
        return {"content": text[:1900]}
    if fmt == "serverchan":
        return {"title": title, "desp": short}
    if fmt == "dingtalk":
        return {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"### {title}\n\n{short}",
            },
        }
    if fmt == "feishu":
        return {
            "msg_type": "text",
            "content": {"text": short},
        }
    if fmt == "wecom":
        return {
            "msgtype": "markdown",
            "markdown": {"content": f"### {title}\n{short[:3500]}"},
        }
    if fmt == "generic":
        return {"text": short, "msg_type": "text", "content": {"text": short}}
    # markdown / default: include several common shapes
    return {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": short},
        "msg_type": "text",
        "content": {"text": short},
        "text": short,
        "title": title,
        "desp": short,
    }


async def _send_webhook(settings: Settings, text: str) -> None:
    if not settings.webhook_url:
        return
    fmt = settings.resolved_webhook_format
    payload = _webhook_payload(fmt, text)
    headers = {"Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(settings.webhook_url, json=payload, headers=headers)
        resp.raise_for_status()


def _send_email(settings: Settings, text: str) -> None:
    if not settings.email_configured:
        return
    msg = MIMEText(text, "plain", "utf-8")
    msg["Subject"] = f"Pulse Desk 简报 {datetime.now().strftime('%m-%d %H:%M')}"
    msg["From"] = settings.smtp_from
    msg["To"] = settings.smtp_to

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.ehlo()
        try:
            smtp.starttls()
            smtp.ehlo()
        except smtplib.SMTPException:
            pass
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.sendmail(settings.smtp_from, [settings.smtp_to], msg.as_string())


async def send_digest(
    *,
    force_refresh: bool = True,
    settings: Settings | None = None,
    slot: str | None = None,
) -> dict[str, Any]:
    settings = settings or load_settings()
    if not settings.any_channel:
        result = {
            "ok": False,
            "error": "未配置推送渠道。请在页面保存 Webhook，或设置环境变量。",
            "channels": [],
            "at": time.time(),
            "slot": slot,
        }
        _LAST_PUSH.update(result)
        return result

    data = await refresh_intel(force=force_refresh)
    text = format_digest_text(data)
    channels: list[str] = []
    try:
        if settings.webhook_configured:
            await _send_webhook(settings, text)
            channels.append(f"webhook:{settings.resolved_webhook_format}")
        if settings.email_configured:
            await asyncio.to_thread(_send_email, settings, text)
            channels.append("email")
        result = {
            "ok": True,
            "error": None,
            "channels": channels,
            "at": time.time(),
            "slot": slot,
            "preview": text[:400],
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("push failed")
        result = {
            "ok": False,
            "error": str(exc),
            "channels": channels,
            "at": time.time(),
            "slot": slot,
        }
    _LAST_PUSH.update(result)
    return result


async def scheduler_loop(stop_event: asyncio.Event) -> None:
    """Fire digest on interval (default every 15 min) and optional clock times."""
    global _INTERVAL_BOOTSTRAPPED
    while not stop_event.is_set():
        settings = load_settings()
        if settings.push_enabled and settings.any_channel:
            try:
                tz = ZoneInfo(settings.push_timezone)
            except Exception:  # noqa: BLE001
                tz = ZoneInfo("Asia/Shanghai")
            now = datetime.now(tz)
            due_slots: list[str] = []

            interval = int(settings.push_interval_minutes or 0)
            if interval > 0:
                bucket = int(time.time() // (interval * 60))
                slot_key = f"every{interval}m:{bucket}"
                if not _INTERVAL_BOOTSTRAPPED:
                    # Skip the in-progress bucket on startup to avoid immediate burst.
                    _PUSHED_SLOTS.add(slot_key)
                    _INTERVAL_BOOTSTRAPPED = True
                elif slot_key not in _PUSHED_SLOTS:
                    due_slots.append(slot_key)

            hhmm = now.strftime("%H:%M")
            if hhmm in (settings.push_times or []):
                clock_slot = f"{now.date().isoformat()}T{hhmm}"
                if clock_slot not in _PUSHED_SLOTS:
                    due_slots.append(clock_slot)

            for slot_key in due_slots:
                _PUSHED_SLOTS.add(slot_key)
                if len(_PUSHED_SLOTS) > 128:
                    newest = list(_PUSHED_SLOTS)[-64:]
                    _PUSHED_SLOTS.clear()
                    _PUSHED_SLOTS.update(newest)
                logger.info("scheduled push slot %s", slot_key)
                await send_digest(force_refresh=True, settings=settings, slot=slot_key)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=15.0)
        except TimeoutError:
            continue


async def push_once_cli() -> None:
    result = await send_digest(force_refresh=True)
    print(result)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(push_once_cli())


if __name__ == "__main__":
    main()
