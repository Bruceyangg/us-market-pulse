"""Link portfolio holdings to intel / news items."""

from __future__ import annotations

import re
from typing import Any


def _holding_needles(holding: dict[str, Any]) -> list[tuple[str, str]]:
    symbol = str(holding.get("symbol") or "").strip().upper()
    if not symbol:
        return []
    needles: list[tuple[str, str]] = [("symbol", symbol)]
    name = str(holding.get("name") or "").strip()
    if name and name.casefold() != symbol.casefold() and len(name) >= 2:
        needles.append(("name", name))
    note = str(holding.get("note") or "").strip()
    if note and len(note) >= 2 and note.casefold() not in {
        symbol.casefold(),
        name.casefold(),
    }:
        needles.append(("note", note))
    return needles


def _item_blob(item: dict[str, Any]) -> str:
    return " ".join(
        [
            str(item.get("title") or ""),
            str(item.get("title_zh") or ""),
            str(item.get("summary") or ""),
            str(item.get("brief_zh") or ""),
            str(item.get("theme") or ""),
            str(item.get("source") or ""),
            "、".join(item.get("sentiment_factors") or []),
        ]
    )


def _token_hit(blob: str, needle: str, *, kind: str) -> bool:
    text = needle.strip()
    if not text:
        return False
    if kind == "symbol":
        # Whole-token ticker match: NVDA, BRK.B, ^VIX
        pattern = rf"(?<![A-Za-z0-9]){re.escape(text)}(?![A-Za-z0-9])"
        return re.search(pattern, blob, flags=re.IGNORECASE) is not None
    return text.casefold() in blob.casefold()


def match_portfolio_intel(
    items: list[dict[str, Any]],
    holdings: list[dict[str, Any]],
    *,
    symbol: str | None = None,
) -> list[dict[str, Any]]:
    """Annotate and filter intel items that mention portfolio holdings."""
    selected = (symbol or "").strip().upper() or None
    catalog: list[dict[str, Any]] = []
    for holding in holdings or []:
        needles = _holding_needles(holding)
        if not needles:
            continue
        sym = str(holding.get("symbol") or "").upper()
        if selected and sym != selected:
            continue
        catalog.append(
            {
                "symbol": sym,
                "name": holding.get("name") or sym,
                "needles": needles,
            }
        )

    # Clear previous annotations
    for item in items:
        item["holding_hit"] = False
        item["holding_matches"] = []

    if not catalog:
        return []

    hits: list[dict[str, Any]] = []
    for item in items:
        blob = _item_blob(item)
        matched: list[str] = []
        for row in catalog:
            for kind, needle in row["needles"]:
                if _token_hit(blob, needle, kind=kind):
                    if row["symbol"] not in matched:
                        matched.append(row["symbol"])
                    break
        item["holding_hit"] = bool(matched)
        item["holding_matches"] = matched
        if matched:
            hits.append(item)

    # Prefer bearish / fresher within holding hits
    hits.sort(
        key=lambda x: (
            0 if x.get("sentiment") == "bearish" else 1 if x.get("sentiment") == "neutral" else 2,
            float(x.get("sentiment_score") or 0)
            if x.get("sentiment") == "bearish"
            else -float(x.get("sentiment_score") or 0),
            -(x.get("published_ts") or 0.0),
        )
    )
    return hits


def summarize_holding_intel(
    items: list[dict[str, Any]],
    holdings: list[dict[str, Any]],
    *,
    symbol: str | None = None,
    limit: int = 24,
) -> dict[str, Any]:
    """Match, count, and optionally filter holding-linked intel."""
    selected = (symbol or "").strip().upper() or None
    hits = match_portfolio_intel(items, holdings)
    counts: dict[str, int] = {}
    for item in hits:
        for sym in item.get("holding_matches") or []:
            counts[sym] = counts.get(sym, 0) + 1
    symbols = []
    for holding in holdings or []:
        sym = str(holding.get("symbol") or "").upper()
        if not sym:
            continue
        symbols.append(
            {
                "symbol": sym,
                "name": holding.get("name") or sym,
                "count": counts.get(sym, 0),
            }
        )
    filtered = (
        [i for i in hits if selected in (i.get("holding_matches") or [])]
        if selected
        else hits
    )
    return {
        "selected": selected or "",
        "symbols": symbols,
        "count": len(filtered),
        "total": len(hits),
        "items": filtered[: max(1, min(limit, 60))],
    }
