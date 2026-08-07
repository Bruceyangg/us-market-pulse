#!/usr/bin/env python3
"""Generate Pulse Desk design documentation HTML + PDF for AI handoff."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent
HTML_PATH = OUT_DIR / "Pulse-Desk-设计说明与逻辑手册.html"
PDF_PATH = OUT_DIR / "Pulse-Desk-设计说明与逻辑手册.pdf"
MD_PATH = OUT_DIR / "Pulse-Desk-设计说明与逻辑手册.md"

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>Pulse Desk 设计说明与逻辑手册</title>
<style>
  @page { size: A4; margin: 16mm 14mm 18mm 14mm; }
  :root {
    --ink: #102033;
    --soft: #3a4d63;
    --line: #d5dee7;
    --paper: #f7fafc;
    --panel: #ffffff;
    --sky: #2f6f9f;
    --up: #d92b2b;
    --down: #0f8a6a;
    --code-bg: #f0f4f8;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    color: var(--ink);
    font: 11pt/1.55 "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", "Microsoft YaHei", sans-serif;
    background: #fff;
  }
  h1, h2, h3, h4 {
    font-family: "Fraunces", "Songti SC", "PingFang SC", serif;
    line-height: 1.25;
    margin: 1.4em 0 0.45em;
    page-break-after: avoid;
  }
  h1 { font-size: 26pt; margin-top: 0; }
  h2 { font-size: 16pt; border-bottom: 2px solid var(--ink); padding-bottom: 0.25em; margin-top: 1.8em; }
  h3 { font-size: 13pt; color: var(--sky); }
  h4 { font-size: 11.5pt; margin-bottom: 0.3em; }
  p, li { font-size: 10.5pt; }
  .lede { font-size: 12pt; color: var(--soft); max-width: 42em; }
  .meta { color: var(--soft); font-size: 9.5pt; }
  .cover {
    page-break-after: always;
    min-height: 240mm;
    padding: 28mm 8mm 20mm;
    background:
      radial-gradient(900px 420px at 12% -10%, rgba(47,111,159,.18), transparent 55%),
      radial-gradient(700px 360px at 90% 0%, rgba(15,138,106,.12), transparent 50%),
      linear-gradient(165deg, #e8eef3 0%, #f7f4ee 48%, #edf3f1 100%);
  }
  .cover .kicker {
    letter-spacing: .18em;
    text-transform: uppercase;
    font-size: 10pt;
    color: var(--sky);
    font-weight: 700;
  }
  .cover h1 { font-size: 34pt; margin: 0.35em 0 0.2em; }
  .cover .badge {
    display: inline-block;
    margin-top: 1.2em;
    padding: 0.35em 0.75em;
    border-radius: 999px;
    background: rgba(255,255,255,.75);
    border: 1px solid var(--line);
    font-size: 9.5pt;
  }
  .toc a { color: var(--ink); text-decoration: none; }
  .toc li { margin: 0.25em 0; }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 0.7em 0 1.1em;
    font-size: 9.5pt;
    page-break-inside: avoid;
  }
  th, td {
    border: 1px solid var(--line);
    padding: 0.4em 0.5em;
    text-align: left;
    vertical-align: top;
  }
  th { background: var(--code-bg); }
  code, .mono {
    font-family: "SF Mono", Menlo, Consolas, monospace;
    font-size: 8.8pt;
  }
  pre {
    background: var(--code-bg);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.75em 0.9em;
    overflow-x: auto;
    font-size: 8.2pt;
    line-height: 1.4;
    page-break-inside: avoid;
  }
  .box {
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 0.8em 1em;
    background: var(--paper);
    margin: 0.8em 0;
    page-break-inside: avoid;
  }
  .box.note { border-left: 4px solid var(--sky); }
  .box.warn { border-left: 4px solid var(--up); }
  .box.ok { border-left: 4px solid var(--down); }
  .swatch {
    display: inline-block;
    width: 0.9em; height: 0.9em;
    border-radius: 3px;
    vertical-align: -0.1em;
    margin-right: 0.25em;
  }
  .diagram {
    font-family: "SF Mono", Menlo, Consolas, monospace;
    font-size: 7.6pt;
    line-height: 1.28;
    background: #0b1220;
    color: #d7e2ef;
    border-radius: 10px;
    padding: 1em 1.1em;
    white-space: pre;
    overflow-x: auto;
    page-break-inside: avoid;
  }
  .diagram .c { color: #7dd3fc; }
  .diagram .g { color: #86efac; }
  .diagram .r { color: #fca5a5; }
  .diagram .y { color: #fde68a; }
  .small { font-size: 9pt; color: var(--soft); }
  .page-break { page-break-before: always; }
  ul.tight li { margin: 0.15em 0; }
  .footer-note {
    margin-top: 2em;
    padding-top: 0.8em;
    border-top: 1px solid var(--line);
    font-size: 9pt;
    color: var(--soft);
  }
</style>
</head>
<body>

<section class="cover">
  <p class="kicker">US MARKET PULSE · DESIGN HANDBOOK</p>
  <h1>Pulse Desk<br/>设计说明与逻辑手册</h1>
  <p class="lede">面向二次开发 / 另一 AI 读取修改的完整说明：产品定位、视觉与信息架构、页面细节、数据流、模块入口、性能策略与修改指南。</p>
  <p class="meta">
    产品名：Pulse Desk（美股情报台）<br/>
    代码根目录：<span class="mono">us-market-pulse/</span><br/>
    在线地址：https://us-market-pulse-6sqa.onrender.com<br/>
    文档版本：2026-08-06 · 前端资源 <span class="mono">?v=20260806e15</span> · SW <span class="mono">v98</span><br/>
    技术栈：FastAPI + Jinja2 + 原生 JS/CSS · 部署于 Render
  </p>
  <p class="badge">红涨绿跌 · 持仓/板块共用交易台 · Yahoo 1D 分时 · 日/月/季后台升级 · 1s 自动刷新</p>
</section>

<h2>目录</h2>
<ol class="toc">
  <li><a href="#s1">1. 产品定位与设计原则</a></li>
  <li><a href="#s2">2. 仓库结构（给 AI 的地图）</a></li>
  <li><a href="#s3">3. 信息架构与页面清单</a></li>
  <li><a href="#s4">4. 视觉设计系统</a></li>
  <li><a href="#s5">5. 交易台 UI 细节（持仓 = 板块）</a></li>
  <li><a href="#s6">6. 分时图与 K 线设计</a></li>
  <li><a href="#s7">7. 双行报价（收盘 / 实时 / 时段）</a></li>
  <li><a href="#s8">8. 系统逻辑总图</a></li>
  <li><a href="#s9">9. 关键数据流与性能路径</a></li>
  <li><a href="#s10">10. 后端模块与 API</a></li>
  <li><a href="#s11">11. 前端状态与关键函数</a></li>
  <li><a href="#s12">12. 缓存、主题、PWA、部署</a></li>
  <li><a href="#s13">13. 另一 AI 修改指南（Checklist）</a></li>
  <li><a href="#s14">14. 附录：核心代码锚点</a></li>
</ol>

<h2 id="s1">1. 产品定位与设计原则</h2>
<h3>1.1 产品是什么</h3>
<p>Pulse Desk 是一个<strong>个人美股交易情报台</strong>：把「我的持仓」「热点板块」「市场指数」「财报」「情报流」放在同一视觉语言下。重点不是花哨仪表盘，而是<strong>快速点选个股 → 看分时/K线 → 读财报与产业链 → 决定是否加入持仓</strong>。</p>

<h3>1.2 不可破坏的设计原则</h3>
<table>
  <tr><th>原则</th><th>含义</th><th>落地</th></tr>
  <tr><td>红涨绿跌</td><td>A股习惯配色</td><td>JS <code>TAPE_UP=#d92b2b</code> / <code>TAPE_DOWN=#0f8a6a</code>；CSS <code>.up/.down</code></td></tr>
  <tr><td>持仓 ≡ 板块</td><td>同一交易台逻辑</td><td>共用列表报价、分时渲染、1s 刷新、+/- 持仓按钮</td></tr>
  <tr><td>Yahoo 1D 分时</td><td>盘前到盘后一条带</td><td>ET 04:00–20:00 轴；昨收虚线；会话刻度</td></tr>
  <tr><td>先画后取</td><td>按钮必须即时响应</td><td>本地乐观更新 → 后台请求；add/remove 不阻塞行情</td></tr>
  <tr><td>一屏一焦点</td><td>中间图是主舞台</td><td>左列表、中图+解读、右情报；TF 切换只重绘中间图</td></tr>
  <tr><td>免费源可降级</td><td>Yahoo 429 不白屏</td><td>CNBC 日报价、Nasdaq 分时/回退</td></tr>
</table>

<div class="box note">
<strong>给另一 AI 的硬约束：</strong>修改 UI 时不要把持仓和板块拆成两套图表渲染器；不要改成绿涨红跌；不要在 add/remove 接口里重新引入完整 <code>build_portfolio_view</code> 等待。
</div>

<h2 id="s2" class="page-break">2. 仓库结构（给 AI 的地图）</h2>
<pre>
us-market-pulse/
├── src/us_market_pulse/
│   ├── app.py                 # FastAPI 路由：页面 + API
│   ├── auth.py                # 登录注册 / session
│   ├── quotes.py              # CNBC/Yahoo 日报价 + Nasdaq 分时 + 双行报价字段
│   ├── markets.py             # Yahoo K线/分时 bundle、TIMEFRAMES
│   ├── sectors.py             # 板块台、成分 enrichment、1s snapshot
│   ├── portfolio.py           # 持仓持久化、选中升级、持仓台视图
│   ├── feeds.py               # RSS 情报 + 市场台缓存
│   ├── market_map.py          # 全板块涨跌图
│   ├── earnings_calendar.py   # 财报日历
│   ├── portfolio_intel.py     # 持仓相关情报
│   ├── templates/             # Jinja 页面（desk/sectors/markets/...）
│   └── static/
│       ├── app.js             # 全部前端逻辑（单文件）
│       ├── styles.css         # 设计系统 + 页面样式
│       └── sw.js              # Service Worker 壳缓存
├── data/                      # 运行时：users/portfolios/settings
├── docs/                      # 本手册
├── Dockerfile / render.yaml   # Render 部署
└── README.md
</pre>

<h3>2.1 修改时优先打开的文件</h3>
<table>
  <tr><th>想改什么</th><th>文件</th></tr>
  <tr><td>页面骨架 / 导航</td><td><code>templates/base.html</code> + 各页 html</td></tr>
  <tr><td>颜色、列表、交易台布局</td><td><code>static/styles.css</code></td></tr>
  <tr><td>点选、刷新、报价单元格、图表</td><td><code>static/app.js</code></td></tr>
  <tr><td>收盘/实时/时段字段</td><td><code>quotes.py</code></td></tr>
  <tr><td>分时 snapshot / 板块 enrich</td><td><code>sectors.py</code></td></tr>
  <tr><td>持仓 CRUD / 选中升级</td><td><code>portfolio.py</code> + <code>app.py</code></td></tr>
  <tr><td>缓存版本号</td><td><code>base.html ?v=</code> + <code>sw.js</code> CACHE</td></tr>
</table>

<h2 id="s3">3. 信息架构与页面清单</h2>
<div class="diagram">导航（顶栏 + 移动底栏）
  持仓 → 市场 → 板块 → 财报 → 情报 → 产业链 → 设置
   |       |      |      |      |       |       |
 desk  markets sectors earnings intel chains settings

认证：/login /register   安装引导：/install
在线：https://us-market-pulse-6sqa.onrender.com
</div>

<table>
  <tr><th>路由</th><th>模板</th><th>page id</th><th>核心能力</th></tr>
  <tr><td><code>/</code></td><td>desk.html</td><td>desk</td><td>个人持仓三栏交易台（需登录）</td></tr>
  <tr><td><code>/sectors</code></td><td>sectors.html</td><td>sectors</td><td>美国市场期货 + 热图 + ETF + 成分交易台</td></tr>
  <tr><td><code>/markets</code></td><td>markets.html</td><td>markets</td><td>指数/宏观 + 多周期图</td></tr>
  <tr><td><code>/earnings</code></td><td>earnings.html</td><td>earnings</td><td>财报日历筛选</td></tr>
  <tr><td><code>/intel</code></td><td>intel.html</td><td>intel</td><td>RSS 情报、战争台、持仓筛选</td></tr>
  <tr><td><code>/chains</code></td><td>chains.html</td><td>chains</td><td>产业链搜索 + 思维导图 + 上下游</td></tr>
  <tr><td><code>/settings</code></td><td>settings.html</td><td>settings</td><td>推送/关注设置</td></tr>
</table>

<h2 id="s4" class="page-break">4. 视觉设计系统</h2>
<h3>4.1 字体</h3>
<ul class="tight">
  <li><strong>Display</strong>：Fraunces（标题、品牌感）</li>
  <li><strong>Body</strong>：Sora + PingFang SC / Noto Sans SC</li>
</ul>

<h3>4.2 主题变量</h3>
<p>CSS 变量定义在 <code>styles.css</code>：<code>html[data-theme="light|dark"]</code>。主题模式存 <code>localStorage.pulse_theme_mode</code> = <code>auto|light|dark</code>（auto：本地 06–18 点用浅色）。</p>
<table>
  <tr><th>Token</th><th>浅色</th><th>深色</th><th>用途</th></tr>
  <tr><td><code>--ink</code></td><td>#102033</td><td>#eef3f8</td><td>主文字</td></tr>
  <tr><td><code>--signal</code></td><td><span class="swatch" style="background:#0f8a6a"></span>#0f8a6a</td><td>#2ecf9a</td><td>跌 / 正向信号绿</td></tr>
  <tr><td>涨色（硬编码）</td><td colspan="2"><span class="swatch" style="background:#d92b2b"></span>#d92b2b</td><td>涨幅文字/柱/线</td></tr>
  <tr><td><code>--sky</code></td><td>#2f6f9f</td><td>#6aa8d4</td><td>强调蓝</td></tr>
  <tr><td><code>--body-bg</code></td><td colspan="2">双径向渐变 + 斜向底色</td><td>避免纯平背景</td></tr>
</table>

<h3>4.3 组件语言</h3>
<ul class="tight">
  <li>圆角约 11–18px；细边框 <code>--line</code>；柔和阴影 <code>--shadow</code></li>
  <li>筛选按钮 <code>.filter</code> / <code>.tf-filters</code>，激活态 <code>.is-active</code></li>
  <li>列表行 <code>.holding-row.sector-pick-row</code>，选中 <code>.is-active</code>，持仓中 <code>.in-holding</code></li>
  <li>涨跌标签：收盘用实心胶囊（白字红/绿底）；实时用小字红/绿字 + 灰底时段徽章</li>
</ul>

<h2 id="s5">5. 交易台 UI 细节（持仓 = 板块）</h2>
<div class="diagram">三栏交易台（desk / sectors 共用结构）

┌───────────────┬────────────────────────────┬──────────────────┐
│ 左：成分/持仓列表 │ 中：分时/K线 + 财报/解读     │ 右：产业链/情报   │
│               │                            │                  │
│ 名称          │  [分时][日][月][季]         │ 业务与产业链     │
│ 代码·板块·月幅 │  标题 · 涨跌幅               │ 热点利空         │
│ ┌spark┐ 报价  │  现价 开 高 低 月涨幅        │ 板块/持仓信息流  │
│        ┌收盘%┐│  ════ Yahoo 1D 分时 SVG ═══ │ 财报日历片段     │
│        └实时%┘│  个股财报 / 涨跌解读         │                  │
│           [+] │  个股信息流                 │                  │
└───────────────┴────────────────────────────┴──────────────────┘
</div>

<h3>5.1 左侧列表行</h3>
<ol>
  <li><strong>主按钮区</strong>（点选切换图表）：公司名 + 可选「涨势/强/持仓」标签；副行代码·板块·月涨幅；spark 迷你分时；双行报价。</li>
  <li><strong>+/− 按钮</strong>：加入/移除持仓；乐观更新；失败回滚。</li>
  <li>选中行左边条/边框高亮；涨跌决定左边指示条颜色。</li>
</ol>

<h3>5.2 中间图区交互</h3>
<ul class="tight">
  <li>TF 切换：只调用 <code>renderPortfolioChart</code> / <code>renderSectorPickChart</code>，不重绘列表；若日/月/季缺点，触发 <code>ensureMultiTfChartUpgrade()</code>。</li>
  <li>缩放：捏合/滚轮 + 角控按钮；分时不切片（整段 Yahoo 日轴）。</li>
  <li>持仓页支持悬停预览（preview）与键盘 ↑↓ / 1–5 切周期。</li>
</ul>

<h3>5.3 板块页额外层</h3>
<ul class="tight">
  <li>顶部「全板块涨跌图」热力/树图（<code>market_map.py</code>）</li>
  <li>ETF / 热点 chips 条，点击切换 <code>sectorId</code></li>
</ul>

<h2 id="s6" class="page-break">6. 分时图与 K 线设计</h2>
<h3>6.1 分时（intraday）</h3>
<table>
  <tr><th>项</th><th>设计</th></tr>
  <tr><td>数据窗口</td><td>Yahoo 1D · 1m · prepost=true；失败回退 Nasdaq chart</td></tr>
  <tr><td>画布时间轴</td><td>固定美东 04:00–20:00（不是按首末点拉伸）</td></tr>
  <tr><td>刻度</td><td>5AM / 7 / 9:30 开盘 / 11 / 1PM / 4PM 收盘 / 7PM</td></tr>
  <tr><td>昨收</td><td>水平虚线 <code>previous_close</code></td></tr>
  <tr><td>颜色</td><td>相对涨跌红/绿折线</td></tr>
  <tr><td>渲染函数</td><td><code>renderSessionIntradaySvg</code> ← <code>paintZoomableChart</code></td></tr>
  <tr><td>自动刷新</td><td>持仓/板块在分时 TF 下每 <strong>1 秒</strong> 调 <code>/api/quote/intraday</code></td></tr>
  <tr><td>刷新策略</td><td>服务端 Nasdaq 优先（快）；TTL 1s；客户端 <code>patchZoomableIntraday</code> 补点</td></tr>
</table>

<h3>6.2 K 线（day / month / quarter）</h3>
<ul class="tight">
  <li><code>renderCandleSvg</code> + MA5/10/30/60/120/250（红涨绿跌实体）</li>
  <li>可缩放平移；默认可见窗口由 <code>CHART_DEFAULT_VISIBLE</code> 控制</li>
  <li><strong>就绪判定</strong>：<code>pickHasChart</code> = day 或 month 点数 ≥ 2；仅有分时不算「多周期就绪」</li>
  <li>缺 K 线时：<code>ensureMultiTfChartUpgrade()</code> 后台拉日/月/季，无需整页刷新</li>
</ul>

<div class="box ok">
<strong>一致性要点：</strong>列表 spark、中间分时、1s poll 三者都应表现「同一交易日扩展时段带」，不要再引入夜盘合成假直线（免费源无可靠 20:00–04:00 ticks）。
</div>

<h2 id="s7">7. 双行报价（收盘 / 实时 / 时段）</h2>
<div class="diagram">列表右侧报价单元格 listQuoteHtml(pick)

  ┌ price(大)  ┌ chg-close 胶囊 ┐
  │ 317.74     │   +7.85%      │   ← 收盘/常规日涨跌（红底白字 / 绿底白字）
  └──────────  └───────────────┘
  ┌ rt-price   rt-chg     session-tag ┐
  │ 315.00     -0.86%     [盘前]       │ ← 实时扩展时段（小字红/绿）+ 时段徽章
  └───────────────────────────────────┘

字段来源（quotes.fetch_cnbc_quotes）：
  price/change_pct     ← CNBC last + change_pct（盘前时 last≈昨收，change=当日收盘涨跌）
  rt_*                 ← ExtendedMktQuote
  session_label        ← curmktstatus / ExtendedMktQuote.type / ET 时钟
                         盘前 | 盘中 | 盘后 | 夜盘
</div>

<p>分时 poll 只更新 <code>rt_*</code>，<strong>不覆盖</strong>收盘 <code>change_pct</code>，避免盘前把收盘涨幅冲掉。</p>

<h2 id="s8" class="page-break">8. 系统逻辑总图</h2>
<div class="diagram"><span class="c">┌─────────────────────────── 浏览器 ───────────────────────────┐</span>
│  Jinja 页面壳 base.html                                      │
│  app.js state + bootPage()                                   │
│   ├─ desk: loadPortfolio / select / 1s refresh               │
│   ├─ sectors: loadSectorDesk / select / 1s refresh           │
│   └─ SW: HTML/API network-first; static cache-first          │
<span class="c">└────────────────────────────┬────────────────────────────────┘</span>
                             │ HTTPS JSON
<span class="g">┌────────────────────────────▼────────────────────────────────┐</span>
│ FastAPI app.py                                               │
│  /api/portfolio*  /api/sectors  /api/quote/intraday  ...     │
<span class="g">└───────┬───────────────┬──────────────────┬──────────────────┘</span>
        │               │                  │
   <span class="y">portfolio.py</span>    <span class="y">sectors.py</span>         <span class="y">quotes.py / markets.py</span>
   持仓 JSON        板块台组装          日报价 + Yahoo bundle
   upgrade 选中     snapshot 1s         Nasdaq intraday
        │               │                  │
        └───────────────┴──────────┬───────┘
                                   ▼
              <span class="r">外部源：CNBC · Yahoo Finance · Nasdaq · RSS · FRED</span>
</div>

<h3>8.1 数据源职责矩阵</h3>
<table>
  <tr><th>源</th><th>职责</th><th>失败时</th></tr>
  <tr><td>CNBC</td><td>批量日报价 + 扩展时段（双行报价）</td><td>Yahoo light quote</td></tr>
  <tr><td>Yahoo</td><td>多周期 K 线 / 1D 分时初始包 / 财报摘要</td><td>Nasdaq OHLC / intraday</td></tr>
  <tr><td>Nasdaq</td><td>1s 分时 poll、列表 spark、Yahoo 429 回退</td><td>保留上一帧缓存</td></tr>
  <tr><td>RSS/FRED</td><td>情报与宏观</td><td>空状态文案</td></tr>
</table>

<h2 id="s9" class="page-break">9. 关键数据流与性能路径</h2>
<h3>9.1 点选个股（持仓）</h3>
<div class="diagram">click 列表行
  → selectPortfolioSymbol(sym)
      → 仅当同代码且 pickHasChart(board) 时跳过网络
      → applyPortfolioSelectionLocal  (同步本地 board/cache)
      → paintPortfolioSelection       (高亮+中图+右侧，不重绘整表)
      → 合并并发：portfolioSelectPending
      → POST /api/portfolio/select
          → select_holding + upgrade_selected_board
             (cache_fresh 要求已有 day/month；仅分时不算命中)
      → mergePortfolioSelectResponse
          → 再 paint，必要时补 spark/报价
</div>

<h3>9.2 点选个股（板块）</h3>
<div class="diagram">click 成分
  → selectSectorSymbol(sym)
      → 本地改 selected_pick
      → paintSectorSelection          (不重建整表)
      → 若 pickHasChart(pick)：可直接结束（分时可继续 1s poll）
      → 否则后台 loadSectorDesk() 升级多周期（即使已有分时）
</div>

<h3>9.3 分时 1 秒刷新</h3>
<div class="diagram">setInterval 1000ms (仅 TF=intraday)
  → refreshActiveIntraday
      → GET /api/quote/intraday?symbol=
          → fetch_intraday_snapshot
             Nasdaq-first (≤2s) → 标注 session → TTL 1s 缓存
      → applyIntradaySnapshot
          更新 rt_* + series.intraday
          patchZoomableIntraday (不拆缩放壳)
</div>

<h3>9.4 板块 +/− 持仓（必须快）</h3>
<div class="diagram">click +
  → 乐观：holdingSymbols.add + paintHoldingToggle(+→−)
  → POST /api/portfolio/add
       只 resolve + save JSON
       立即返回 _portfolio_stub_view   ← 不再 await build_portfolio_view
  → 成功：同步 Set；失败：回滚按钮
</div>

<div class="box warn">
历史坑：add/remove 曾 <code>wait_for(build_portfolio_view, 8s)</code>，导致板块「+」极慢。现已禁止。
</div>

<h3>9.5 日 / 月 / 季：无整页刷新升级</h3>
<div class="diagram">场景：board 只有 series.intraday（分时 OK），用户点「日图」
  → render*Chart 先画（可能暂空）
  → pickHasTfSeries(pick, tf) === false
  → ensureMultiTfChartUpgrade()
       desk   → selectPortfolioSymbol(quiet) → /api/portfolio/select
       sectors→ loadSectorDesk({force})
  → 后端 _pick_has_chart 才算 cache_fresh
  → 返回 day/month/quarter → merge → 按当前 TF 重绘
首屏 boot 后若缺多周期，也会预取一次，避免必须硬刷新。
</div>
<div class="box note">
<strong>历史坑：</strong>曾用 <code>deskChartReady = pickHasChart || pickHasIntraday</code> 作为跳过升级条件，导致有分时时永远不拉 K 线，只有整页刷新才出日/月/季。现改为仅 <code>pickHasChart</code> 可跳过。
</div>

<h2 id="s10">10. 后端模块与 API</h2>
<h3>10.1 关键 REST</h3>
<table>
  <tr><th>方法</th><th>路径</th><th>说明</th></tr>
  <tr><td>GET</td><td><code>/api/portfolio</code></td><td>完整持仓台（可 refresh；超时 stub）</td></tr>
  <tr><td>POST</td><td><code>/api/portfolio/add|remove</code></td><td>秒回 stub</td></tr>
  <tr><td>POST</td><td><code>/api/portfolio/select</code></td><td>只升级选中板</td></tr>
  <tr><td>GET</td><td><code>/api/sectors</code></td><td>板块台 payload</td></tr>
  <tr><td>GET</td><td><code>/api/sectors/map</code></td><td>全市场图</td></tr>
  <tr><td>GET</td><td><code>/api/quote/intraday</code></td><td>共用分时快照</td></tr>
  <tr><td>GET</td><td><code>/api/markets</code></td><td>指数台</td></tr>
  <tr><td>GET</td><td><code>/api/earnings</code></td><td>财报</td></tr>
  <tr><td>GET</td><td><code>/api/intel</code></td><td>情报</td></tr>
  <tr><td>*</td><td><code>/api/auth/*</code></td><td>登录注册登出</td></tr>
</table>

<h3>10.2 关键后端函数</h3>
<pre>
quotes.session_from_status / apply_list_quote_fields / fetch_day_quotes
quotes.fetch_cnbc_quotes / fetch_nasdaq_intraday
markets.fetch_symbol_bundle / PORTFOLIO_TIMEFRAMES
sectors.build_sector_desk / fetch_intraday_snapshot / _fetch_quote_limited
portfolio.build_portfolio_view / upgrade_selected_board / add_holding / remove_holding
app._portfolio_stub_view
</pre>

<h3>10.3 持仓持久化</h3>
<ul class="tight">
  <li>路径：<code>data/portfolios/{username}.json</code></li>
  <li>上限：20 只</li>
  <li>字段：symbol / name / note / added_at；另存 selected</li>
  <li>会话：cookie <code>pulse_session</code>，30 天</li>
</ul>

<h2 id="s11" class="page-break">11. 前端状态与关键函数</h2>
<h3>11.1 state 关键字段</h3>
<pre>
portfolio, portfolioTf, portfolioBoardCache, portfolioSelectBusy/Pending
sectors, sectorId, sectorSymbol, sectorTf, sectorCache
holdingSymbols, holdingToggleBusySyms, intradayPollBusy
chartZoom, chartZoomScope
PAGE, AUTHED
</pre>

<h3>11.2 共享渲染入口（改 UI 必看）</h3>
<table>
  <tr><th>函数</th><th>作用</th></tr>
  <tr><td><code>listQuoteHtml</code></td><td>双行报价 HTML</td></tr>
  <tr><td><code>renderSessionIntradaySvg</code></td><td>Yahoo 风格分时</td></tr>
  <tr><td><code>paintZoomableChart</code> / <code>bindZoomableChart</code></td><td>统一上色与缩放壳</td></tr>
  <tr><td><code>refreshActiveIntraday</code> / <code>applyIntradaySnapshot</code></td><td>1s 刷新</td></tr>
  <tr><td><code>paintPortfolioSelection</code> / <code>paintSectorSelection</code></td><td>点选快路径</td></tr>
  <tr><td><code>paintHoldingToggle</code> / <code>toggleSectorHolding</code></td><td>+/− 乐观更新</td></tr>
  <tr><td><code>mergePickPreserveIntraday</code> / <code>mergeListQuoteFields</code></td><td>刷新不丢分时/报价</td></tr>
  <tr><td><code>pickHasChart</code> / <code>pickHasTfSeries</code></td><td>多周期就绪判定</td></tr>
  <tr><td><code>ensureMultiTfChartUpgrade</code></td><td>缺日/月/季时后台升级</td></tr>
</table>

<h2 id="s12">12. 缓存、主题、PWA、部署</h2>
<table>
  <tr><th>层</th><th>机制</th><th>典型 TTL / 版本</th></tr>
  <tr><td>资源 bust</td><td><code>app.js?v=</code> <code>styles.css?v=</code></td><td>20260806e15</td></tr>
  <tr><td>SW</td><td><code>pulse-desk-shell-v98</code></td><td>改静态必升版本</td></tr>
  <tr><td>HTML</td><td><code>Cache-Control: no-store</code></td><td>始终网络</td></tr>
  <tr><td>sessionStorage</td><td><code>pulse_data:{page}</code></td><td>3 分钟首屏恢复</td></tr>
  <tr><td>分时 snap</td><td><code>_INTRADAY_SNAP_TTL</code></td><td>1s</td></tr>
  <tr><td>板块/符号</td><td><code>_SYM_TTL</code> 等</td><td>180s</td></tr>
  <tr><td>持仓 board</td><td><code>_QUOTE_TTL</code></td><td>90s</td></tr>
</table>
<p>部署：Docker → Render 服务 <code>us-market-pulse-6sqa</code>；推送 <code>main</code> 触发自动部署。本地常用 <code>uv run us-market-pulse</code>。</p>

<h2 id="s13" class="page-break">13. 另一 AI 修改指南（Checklist）</h2>
<ol>
  <li><strong>先定位页面</strong>：改结构找 <code>templates/*.html</code>；改交互找 <code>app.js</code>；改样式找 <code>styles.css</code>。</li>
  <li><strong>保持双端一致</strong>：任何列表报价/分时改动必须同时覆盖 desk 与 sectors（优先改共享函数）。</li>
  <li><strong>改完静态资源</strong>：同步 bump <code>base.html ?v=</code> 与 <code>sw.js</code> CACHE/SHELL。</li>
  <li><strong>性能红线</strong>：点选不要 <code>innerHTML</code> 重建整表；add/remove 不要拉全量行情；TF 切换只重绘图。</li>
  <li><strong>分时红线</strong>：保持 ET 04:00–20:00 轴与昨收线；poll 只补 <code>rt_*</code> + points。</li>
  <li><strong>多周期红线</strong>：不要用「有分时」跳过 day/month 升级；<code>cache_fresh</code> / 前端 early-return 必须以 <code>pickHasChart</code> 为准。</li>
  <li><strong>验证</strong>：硬刷新后检查版本号；测盘前双行报价；测 + 按钮瞬时反馈；测 1s 分时；测日/月/季无需整页刷新。</li>
  <li><strong>不要做</strong>：引入重型前端框架（当前刻意单文件原生 JS）；绿涨红跌；为夜盘造假点。</li>
</ol>

<div class="box note">
<strong>推荐工作流给 AI：</strong>用 Grep 搜函数名 → 小范围改共享路径 → 本地 <code>py_compile</code> → bump 版本 → 部署 → curl 验证 <code>app.js?v=</code> 与关键 API 字段。
</div>

<h2 id="s14">14. 附录：核心代码锚点</h2>
<pre>
# 后端
app.py                 api_portfolio_add/remove/select, api_quote_intraday, api_sectors
quotes.py              fetch_cnbc_quotes, session_from_status, apply_list_quote_fields
sectors.py             fetch_intraday_snapshot, build_sector_desk, _annotate_intraday_sessions
portfolio.py           build_portfolio_view, upgrade_selected_board
markets.py             PORTFOLIO_TIMEFRAMES, fetch_symbol_bundle, render 用的 session helpers

# 前端
app.js                 state, bootPage, listQuoteHtml, renderSessionIntradaySvg,
                       selectPortfolioSymbol, selectSectorSymbol, refreshActiveIntraday,
                       ensureMultiTfChartUpgrade, pickHasChart, pickHasTfSeries,
                       toggleSectorHolding, paintHoldingToggle
styles.css             :root 主题变量, .chg-close, .quote-rt, .session-tag, .sectors-desk
templates/desk.html    持仓三栏
templates/sectors.html 热图 + 三栏
templates/base.html    导航、主题、?v=、SW 注册
static/sw.js           壳缓存版本
</pre>

<h3>14.1 列表报价字段契约（前后端约定）</h3>
<pre>
{
  "symbol": "LRCX",
  "price": 317.74,              // 收盘/常规价
  "change_pct": 7.85,           // 收盘涨跌幅
  "rt_price": 315.0,            // 实时价
  "rt_change_pct": -0.86,       // 实时涨跌幅
  "session": "pre",             // pre|regular|post|night
  "session_label": "盘前",
  "series": { "intraday": { "points": [...], "previous_close": ... } }
}
</pre>

<div class="footer-note">
本文档与同目录 Markdown / PDF 同步生成；完整注解源码见 <code>Pulse-Desk-完整代码与注解.txt</code>。在线站点：https://us-market-pulse-6sqa.onrender.com · 仓库：us-market-pulse · 版本 <code>?v=20260806e15</code> / SW <code>v98</code> · 生成日：2026-08-06。
</div>

</body>
</html>
"""

MD = """> **AI Handoff Document** — Pulse Desk design & logic handbook.
> Companion PDF/HTML in same folder. Live: https://us-market-pulse-6sqa.onrender.com
> Frontend bust: `?v=20260806e15` · SW `v98` · Generated 2026-08-06

# Pulse Desk 设计说明与逻辑手册

面向二次开发 / 另一 AI 读取修改的完整说明。HTML/PDF 同目录；完整注解源码见 `Pulse-Desk-完整代码与注解.txt`。

## 1. 产品定位与硬原则

核心路径：**点选个股 → 分时/K线 → 财报与产业链 → +/- 持仓**。

1. **红涨绿跌**（`TAPE_UP=#d92b2b` / `TAPE_DOWN=#0f8a6a`）
2. **持仓 ≡ 板块**（共用报价/分时/1s 刷新/+-）
3. **Yahoo 1D 分时**（ET 04:00–20:00 + 昨收线）
4. **先画后取**（乐观 UI；add/remove 返回 stub，禁止等待 `build_portfolio_view`）
5. **免费源可降级**（CNBC / Yahoo / Nasdaq）
6. **多周期升级**：有分时 ≠ 已有日/月/季；必须以 `pickHasChart` 判定

## 2. 仓库地图

| 路径 | 用途 |
|------|------|
| `app.py` | 路由/API + `_portfolio_stub_view` |
| `quotes.py` | 日报价+扩展时段+Nasdaq 分时 |
| `markets.py` | Yahoo bundle / TIMEFRAMES |
| `sectors.py` | 板块台 + 1s snapshot |
| `portfolio.py` | 持仓存储；`upgrade_selected_board`（cache_fresh 需 day/month） |
| `static/app.js` | 全部前端 |
| `static/styles.css` | 设计系统 |
| `templates/*` | 页面骨架 |
| `static/sw.js` | 壳缓存 `pulse-desk-shell-v98` |
| `us_markets.py` | 美国市场期货 strip + 日/月/季（硬超时） |
| `chains.py` / `chain_generate.py` | 产业链台 |

## 3. 页面

`/` desk · `/sectors` · `/markets` · `/earnings` · `/intel` · `/chains` · `/settings` · `/login` · `/install`  
在线：https://us-market-pulse-6sqa.onrender.com

## 4. 交易台布局

左列表 | 中图+财报解读 | 右产业链/情报  
列表报价：`listQuoteHtml` 收盘胶囊 + 实时小字 + 时段徽章（盘前/盘中/盘后/夜盘）

## 5. 分时与 K 线

- 分时渲染：`renderSessionIntradaySvg`；Poll：每 1s `GET /api/quote/intraday`
- K 线：`renderCandleSvg` + MA；就绪：`pickHasChart`（day/month 点数≥2）
- TF 切换只重绘中图；缺序列时 `ensureMultiTfChartUpgrade()`
- 后端 `cache_fresh` 仅当 `_pick_has_chart`；仅有分时必须继续升级

## 6. 关键性能路径

- 点选：本地 paint → 后台 select/upgrade；不整表重绘；early-return 仅 `pickHasChart`
- +/-：乐观按钮 + stub API
- 分时：1s；服务端 TTL 1s
- 日/月/季：TF 点击或缺点预取 → `/select` 或 `loadSectorDesk`，无需硬刷新

## 7. API 速查

- `POST /api/portfolio/add|remove|select`
- `GET /api/sectors` · `/api/sectors/map` · `/api/us-markets?mode=tape|full`
- `GET /api/quote/intraday`
- `GET /api/portfolio` · `/api/markets` · `/api/earnings` · `/api/intel` · `/api/chains`

## 8. 修改 Checklist（给 AI）

1. 优先改共享函数，保持 desk/sectors 一致
2. bump `base.html ?v=` + `sw.js` CACHE
3. 不要用「有分时」跳过 day/month 升级
4. 不要绿涨红跌；不要造夜盘假点
5. 验证：版本号、双行报价、+ 按钮瞬时、1s 分时、日/月/季无需整页刷新

## 9. 字段契约

```json
{
  "price": 317.74,
  "change_pct": 7.85,
  "rt_price": 315.0,
  "rt_change_pct": -0.86,
  "session_label": "盘前",
  "series": {"intraday": {"points": [], "previous_close": 0}, "day": {}, "month": {}, "quarter": {}}
}
```

## 10. 关键函数名

后端：`fetch_intraday_snapshot` `apply_list_quote_fields` `upgrade_selected_board` `_pick_has_chart` `build_sector_desk`  
前端：`listQuoteHtml` `renderSessionIntradaySvg` `refreshActiveIntraday` `paintHoldingToggle` `selectPortfolioSymbol` `selectSectorSymbol` `pickHasChart` `pickHasTfSeries` `ensureMultiTfChartUpgrade`
"""


def main() -> None:
    HTML_PATH.write_text(HTML, encoding="utf-8")
    MD_PATH.write_text(MD, encoding="utf-8")
    print("wrote", HTML_PATH)
    print("wrote", MD_PATH)

    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_PATH}",
        HTML_PATH.as_uri(),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print("wrote", PDF_PATH, "bytes", PDF_PATH.stat().st_size)


if __name__ == "__main__":
    main()
