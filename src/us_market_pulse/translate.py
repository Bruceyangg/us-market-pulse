"""Headline Chinese translation: glossary + online fallback with disk cache."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

from us_market_pulse.config import DATA_DIR

GLOSSARY: list[tuple[str, str]] = [
    ("federal open market committee", "联邦公开市场委员会"),
    ("federal reserve board", "美联储理事会"),
    ("federal reserve", "美联储"),
    ("interest rates", "利率"),
    ("interest rate", "利率"),
    ("rate cuts", "降息"),
    ("rate cut", "降息"),
    ("rate hikes", "加息"),
    ("rate hike", "加息"),
    ("cutting rates", "降息"),
    ("cuts rates", "降息"),
    ("hikes rates", "加息"),
    ("higher for longer", "利率更长时间维持高位"),
    ("quantitative tightening", "量化紧缩"),
    ("monetary policy", "货币政策"),
    ("press conference", "发布会"),
    ("press release", "新闻稿"),
    ("balance sheet", "资产负债表"),
    ("treasury yields", "国债收益率"),
    ("treasury yield", "国债收益率"),
    ("bond market", "债券市场"),
    ("stock market", "股市"),
    ("wall street", "华尔街"),
    ("white house", "白宫"),
    ("debt ceiling", "债务上限"),
    ("trade war", "贸易战"),
    ("soft landing", "软着陆"),
    ("hard landing", "硬着陆"),
    ("risk-off", "避险情绪"),
    ("risk-on", "风险偏好上升"),
    ("consumer price index", "消费者物价指数"),
    ("producer price index", "生产者物价指数"),
    ("nonfarm payrolls", "非农就业"),
    ("nonfarm payroll", "非农就业"),
    ("jobs report", "就业报告"),
    ("dot plot", "点阵图"),
    ("enforcement action", "执法行动"),
    ("securities and exchange commission", "美国证监会"),
    ("supreme court", "最高法院"),
    ("military action", "军事行动"),
    ("travel risk", "旅行风险"),
    ("profit warning", "盈利预警"),
    ("credit crunch", "信贷紧缩"),
    ("government shutdown", "政府停摆"),
    ("in the coming days", "未来数日"),
    ("amid signs of", "在出现迹象之际"),
    ("warns of", "警告存在"),
    ("warn of", "警告存在"),
    ("possible", "可能的"),
    ("embassies", "使领馆"),
    ("americans", "美国人"),
    ("inflation", "通胀"),
    ("recession", "衰退"),
    ("stagflation", "滞胀"),
    ("sanctions", "制裁"),
    ("tariffs", "关税"),
    ("tariff", "关税"),
    ("shutdown", "停摆"),
    ("layoffs", "裁员"),
    ("layoff", "裁员"),
    ("unemployment", "失业率"),
    ("investigation", "调查"),
    ("antitrust", "反垄断"),
    ("lawsuit", "诉讼"),
    ("default", "违约"),
    ("downgrade", "下调评级"),
    ("selloff", "抛售"),
    ("sell-off", "抛售"),
    ("plunge", "暴跌"),
    ("crash", "崩盘"),
    ("surge", "飙升"),
    ("soar", "飙升"),
    ("rally", "反弹"),
    ("hawkish", "鹰派"),
    ("dovish", "鸽派"),
    ("easing", "宽松"),
    ("tightening", "紧缩"),
    ("yields", "收益率"),
    ("yield", "收益率"),
    ("auction", "拍卖"),
    ("treasury", "国债/财政部"),
    ("markets", "市场"),
    ("market", "市场"),
    ("stocks", "股票"),
    ("stock", "股票"),
    ("bonds", "债券"),
    ("bond", "债券"),
    ("economy", "经济"),
    ("economic", "经济"),
    ("growth", "增长"),
    ("banks", "银行"),
    ("bank", "银行"),
    ("war", "战争"),
    ("iran", "伊朗"),
    ("israel", "以色列"),
    ("china", "中国"),
    ("russia", "俄罗斯"),
    ("ukraine", "乌克兰"),
    ("trump", "特朗普"),
    ("biden", "拜登"),
    ("powell", "鲍威尔"),
    ("congress", "国会"),
    ("senate", "参议院"),
    ("ceo", "首席执行官"),
    ("sec", "SEC"),
    ("fomc", "FOMC"),
    ("cpi", "CPI"),
    ("ppi", "PPI"),
    ("pce", "PCE"),
    ("gdp", "GDP"),
    ("fed", "美联储"),
    ("u.s.", "美国"),
    ("says", "表示"),
    ("said", "表示"),
    ("after", "在……之后"),
    ("before", "在……之前"),
    ("amid", "在……背景下"),
    ("despite", "尽管"),
    ("near", "接近"),
    ("hits", "触及"),
    ("rises", "上升"),
    ("falls", "下降"),
    ("jumps", "跳升"),
    ("drops", "下跌"),
    ("weak", "疲弱"),
    ("strong", "强劲"),
    ("threat", "威胁"),
    ("risks", "风险"),
    ("risk", "风险"),
    ("warning", "警告"),
    ("crisis", "危机"),
    ("deal", "协议"),
    ("bill", "法案"),
    ("order", "命令"),
    ("ban", "禁令"),
    ("probe", "调查"),
]

CACHE_PATH = DATA_DIR / "translate_cache.json"
_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_TTL = 14 * 24 * 3600
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_CACHE_LOADED = False


def _key(title: str) -> str:
    return hashlib.sha1(title.encode("utf-8")).hexdigest()


def _load_cache() -> None:
    global _CACHE_LOADED, _CACHE
    if _CACHE_LOADED:
        return
    _CACHE_LOADED = True
    if not CACHE_PATH.exists():
        return
    try:
        raw = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            _CACHE = raw
    except (OSError, json.JSONDecodeError):
        _CACHE = {}


def _save_cache() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Keep cache bounded
    now = time.time()
    items = [
        (k, v)
        for k, v in _CACHE.items()
        if isinstance(v, dict) and now - float(v.get("at") or 0) < _CACHE_TTL
    ]
    items.sort(key=lambda kv: float(kv[1].get("at") or 0), reverse=True)
    trimmed = dict(items[:2000])
    CACHE_PATH.write_text(json.dumps(trimmed, ensure_ascii=False), encoding="utf-8")
    _CACHE.clear()
    _CACHE.update(trimmed)


def _glossary_translate(title: str) -> str:
    out = title
    for eng, zh in GLOSSARY:
        # Word-boundary safe: avoid war→战争 inside "warn"
        pattern = rf"(?<![A-Za-z]){re.escape(eng)}(?![A-Za-z])"
        out = re.sub(pattern, zh, out, flags=re.I)
    return re.sub(r"\s{2,}", " ", out).strip()


def _looks_translated(text: str) -> bool:
    if not text:
        return False
    cjk = len(_CJK_RE.findall(text))
    if cjk < max(2, len(text) // 10):
        return False
    # Reject heavy English leftovers from partial glossary swaps
    en_words = re.findall(r"[A-Za-z]{3,}", text)
    return len(en_words) <= 5


def _is_cacheable(text: str) -> bool:
    return _looks_translated(text) and len(re.findall(r"[A-Za-z]{3,}", text)) <= 3


def _cache_get(title: str) -> str | None:
    _load_cache()
    row = _CACHE.get(_key(title))
    if not row:
        return None
    if time.time() - float(row.get("at") or 0) > _CACHE_TTL:
        return None
    text = str(row.get("text") or "").strip()
    return text if _is_cacheable(text) else None


def _cache_set(title: str, text: str) -> None:
    if not _is_cacheable(text):
        return
    _load_cache()
    _CACHE[_key(title)] = {"at": time.time(), "text": text}


async def _online_translate(
    client: httpx.AsyncClient, title: str, sem: asyncio.Semaphore
) -> str | None:
    cached = _cache_get(title)
    if cached:
        return cached

    async with sem:
        # 1) Google gtx (unofficial, best-effort)
        try:
            resp = await client.get(
                "https://translate.googleapis.com/translate_a/single",
                params={
                    "client": "gtx",
                    "sl": "en",
                    "tl": "zh-CN",
                    "dt": "t",
                    "q": title[:450],
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                chunks = data[0] if isinstance(data, list) and data else []
                translated = "".join(
                    part[0] for part in chunks if isinstance(part, list) and part
                ).strip()
                if _is_cacheable(translated):
                    _cache_set(title, translated)
                    return translated
        except Exception:  # noqa: BLE001
            pass

        # 2) MyMemory fallback
        try:
            resp = await client.get(
                "https://api.mymemory.translated.net/get",
                params={"q": title[:450], "langpair": "en|zh-CN"},
            )
            resp.raise_for_status()
            data = resp.json()
            translated = (
                (data.get("responseData") or {}).get("translatedText") or ""
            ).strip()
            if not translated or "MYMEMORY WARNING" in translated.upper():
                return None
            if not _is_cacheable(translated):
                return None
            _cache_set(title, translated)
            return translated
        except Exception:  # noqa: BLE001
            return None


async def translate_title(
    title: str,
    *,
    client: httpx.AsyncClient | None = None,
    sem: asyncio.Semaphore | None = None,
    online: bool = True,
) -> str:
    title = (title or "").strip()
    if not title:
        return ""
    if _looks_translated(title):
        return title

    cached = _cache_get(title)
    if cached:
        return cached

    if online and client is not None and sem is not None:
        remote = await _online_translate(client, title, sem)
        if remote:
            return remote

    glossary = _glossary_translate(title)
    # Only show glossary when it is clean Chinese; otherwise keep English title
    if _is_cacheable(glossary):
        _cache_set(title, glossary)
        return glossary
    return title


async def enrich_titles(
    items: list[dict[str, Any]], *, online: bool = True, online_limit: int = 80
) -> list[dict[str, Any]]:
    """Attach title_zh to each item. Uses disk cache; online fills gaps."""
    _load_cache()
    sem = asyncio.Semaphore(5)
    out: list[dict[str, Any]] = []
    dirty_before = len(_CACHE)

    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        tasks = []
        for idx, item in enumerate(items):
            title = item.get("title") or ""
            # Prefer cache; only spend online quota on misses within limit
            if _cache_get(title):
                use_online = False
            else:
                use_online = online and idx < online_limit
            tasks.append(
                translate_title(
                    title,
                    client=client,
                    sem=sem,
                    online=use_online,
                )
            )
        titles_zh = await asyncio.gather(*tasks)

    for item, title_zh in zip(items, titles_zh, strict=False):
        row = dict(item)
        zh = title_zh or _glossary_translate(item.get("title") or "")
        row["title_zh"] = zh
        out.append(row)

    if len(_CACHE) != dirty_before:
        try:
            _save_cache()
        except OSError:
            pass
    return out
