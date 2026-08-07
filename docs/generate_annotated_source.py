#!/usr/bin/env python3
"""Bundle Pulse Desk core web sources into one annotated TXT for handoff."""

from __future__ import annotations

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "us_market_pulse"
OUT = Path(__file__).resolve().parent / "Pulse-Desk-完整代码与注解.txt"

# (relative path from SRC, Chinese module annotation)
FILES: list[tuple[str, str]] = [
    (
        "app.py",
        "FastAPI 入口：页面路由、认证门控、持仓/板块/行情 API。"
        "注意 add/remove 必须走 _portfolio_stub_view，禁止等待完整 build_portfolio_view。"
        "共用 GET /api/quote/intraday 给持仓与板块 1 秒分时刷新。",
    ),
    (
        "auth.py",
        "登录/注册/会话：cookie pulse_session，用户与持仓文件按 username 隔离。",
    ),
    (
        "config.py",
        "运行时配置：data/settings.json + 环境变量覆盖（PORT / PULSE_*）。",
    ),
    (
        "quotes.py",
        "日报价与扩展时段：CNBC ExtendedMktQuote → price/change_pct + rt_* + session_label。"
        "Nasdaq 分时拉取；apply_list_quote_fields 保证列表双行报价字段齐全。",
    ),
    (
        "markets.py",
        "Yahoo 多周期 bundle（分时/日/月/季）与指数台 TIMEFRAMES；分时轴按美东会话标注。",
    ),
    (
        "portfolio.py",
        "持仓持久化与选中板升级。upgrade_selected_board / build_portfolio_view 的 cache_fresh "
        "必须以 _pick_has_chart 为准（仅有分时不算命中），否则日/月/季不会后台补齐。",
    ),
    (
        "sectors.py",
        "板块交易台：热图成分、enrich、selected 多周期图表、fetch_intraday_snapshot（Nasdaq-first）。"
        "报价坏缓存自动修复；缺分时也触发升级；列表行 _slim_pick_row 保留选中股完整 series。"
        "时段 restamp_list_session / session_from_clock。",
    ),
    (
        "us_markets.py",
        "板块页「美国市场」：CNBC/Yahoo 指数期货 strip + NQ/ES/YM 多周期。"
        "mode=tape|full；整体硬超时；超时返回 stale/partial，禁止无限挂起。",
    ),
    (
        "chains.py",
        "产业链台 API：搜索/目录/节点全景（与 chain_generate 协作）。",
    ),
    (
        "chain_generate.py",
        "产业链主题包与节点生成（航空/银行/军工/AI 等 + 中英别名）。",
    ),
    (
        "feeds.py",
        "RSS 情报与 Google News 按需拉取（板块/个股新闻 hydrate）。",
    ),
    (
        "market_map.py",
        "全板块涨跌图（sectors 页顶部热力/树图数据）。",
    ),
    (
        "earnings_calendar.py",
        "财报日历数据源与筛选。",
    ),
    (
        "portfolio_intel.py",
        "持仓相关情报映射（desk 情报栏）。",
    ),
    (
        "static/app.js",
        "全部前端逻辑（单文件）。关键：listQuoteHtml、renderSessionIntradaySvg、"
        "selectPortfolioSymbol / selectSectorSymbol、refreshActiveIntraday、"
        "pickHasChart / pickHasTfSeries / ensureMultiTfChartUpgrade、paintHoldingToggle。"
        "红涨绿跌 TAPE_UP/TAPE_DOWN；持仓与板块必须共用这些路径。",
    ),
    (
        "static/styles.css",
        "设计系统与页面样式：主题变量、交易台三栏、双行报价 .chg-close/.quote-rt/.session-tag。",
    ),
    (
        "static/sw.js",
        "Service Worker 壳缓存。改静态资源必须同步 bump CACHE 与 SHELL 里的 ?v=。",
    ),
    (
        "templates/base.html",
        "全局壳：导航、主题、资源 ?v= bust、SW 注册。当前应与 app.js/styles 版本一致。",
    ),
    (
        "templates/desk.html",
        "持仓三栏交易台骨架（左列表 / 中图 / 右情报）。",
    ),
    (
        "templates/sectors.html",
        "板块页：美国市场期货 + 全板块涨跌图 + ETF chips + 与持仓同构的三栏交易台。",
    ),
    (
        "templates/markets.html",
        "市场指数 / 宏观页。",
    ),
    (
        "templates/earnings.html",
        "财报日历页。",
    ),
    (
        "templates/intel.html",
        "情报流 / 战争台页。",
    ),
    (
        "templates/chains.html",
        "产业链页：搜索 + 左右脑思维导图 + 上下游面板。",
    ),
    (
        "templates/settings.html",
        "设置页（推送/关注等）。",
    ),
    (
        "templates/login.html",
        "登录 / 注册页。",
    ),
    (
        "templates/install.html",
        "PWA / 添加到主屏幕引导。",
    ),
]


HEADER = f"""================================================================================
Pulse Desk · 完整代码与注解
================================================================================
产品：Pulse Desk（美股情报台）
仓库：us-market-pulse
在线：https://us-market-pulse-6sqa.onrender.com
生成日：{date.today().isoformat()}
前端资源版本：?v=20260806e15 · Service Worker：pulse-desk-shell-v98
在线固定 URL：https://us-market-pulse-6sqa.onrender.com

【阅读说明】
1. 本文件按模块拼接源码，每个文件前有中文注解（职责 / 红线 / 关键函数）。
2. 设计逻辑总览请同时阅读同目录：
   - Pulse-Desk-设计说明与逻辑手册.md / .html / .pdf
   - Pulse-Desk-网页设计介绍.pptx（若有）
3. 不可破坏原则：
   - 红涨绿跌（非绿涨红跌）
   - 持仓 ≡ 板块（共用列表报价、分时、刷新、+/-）
   - Yahoo 1D 分时轴固定美东 04:00–20:00，勿造夜盘假点
   - 时段徽章跟美东时钟：盘前 / 盘中 / 盘后 / 夜盘（session_from_clock）
   - add/remove 秒回 stub，禁止等待完整行情重建
   - 有分时 ≠ 多周期就绪；日/月/季靠 pickHasChart / ensureMultiTfChartUpgrade
   - 美国市场 /api/us-markets 必须有硬超时与降级，禁止拖死板块页

【目录】
"""


def main() -> None:
    lines: list[str] = [HEADER]
    for i, (rel, note) in enumerate(FILES, 1):
        lines.append(f"{i:02d}. {rel}")
    lines.append("")
    lines.append("=" * 80)
    lines.append("")

    missing: list[str] = []
    for rel, note in FILES:
        path = SRC / rel
        banner = (
            f"\n{'=' * 80}\n"
            f"FILE: src/us_market_pulse/{rel}\n"
            f"{'=' * 80}\n"
            f"[注解]\n{note}\n"
            f"{'-' * 80}\n"
        )
        lines.append(banner)
        if not path.is_file():
            missing.append(rel)
            lines.append(f"<< MISSING: {path} >>\n")
            continue
        text = path.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
        lines.append(text)

    OUT.write_text("".join(lines), encoding="utf-8")
    size = OUT.stat().st_size
    print("wrote", OUT, "bytes", size)
    if missing:
        print("MISSING", missing)


if __name__ == "__main__":
    main()
