> **AI Handoff Document** — Pulse Desk design & logic handbook.
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
