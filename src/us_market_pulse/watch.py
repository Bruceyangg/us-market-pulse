"""Keyword watchlist matching."""

from __future__ import annotations

from typing import Any


def match_watchlist(
    items: list[dict[str, Any]], keywords: list[str]
) -> list[dict[str, Any]]:
    needles = [k.strip() for k in keywords if k and k.strip()]
    if not needles:
        for item in items:
            item["watch_hit"] = False
            item["watch_matches"] = []
        return []

    hits: list[dict[str, Any]] = []
    for item in items:
        text = " ".join(
            [
                str(item.get("title") or ""),
                str(item.get("title_zh") or ""),
                str(item.get("summary") or ""),
                str(item.get("brief_zh") or ""),
                str(item.get("theme") or ""),
                "、".join(item.get("sentiment_factors") or []),
            ]
        )
        folded = text.casefold()
        matched = [k for k in needles if k.casefold() in folded]
        item["watch_hit"] = bool(matched)
        item["watch_matches"] = matched
        if matched:
            hits.append(item)
    return hits
