# Pulse Desk — living context (agents must update)

Last updated: 2026-08-16 · shipping `a42/v164`

## Product

- App: **Pulse Desk** (`us-market-pulse`) — FastAPI + Jinja + `static/app.js`
- Live: https://us-market-pulse-6sqa.onrender.com/sectors
- Host: Render free Docker (cold starts common)

## Current shipped FE/SW

- Static `?v=20260811a42` (shipping)
- SW cache `pulse-desk-shell-v164` · reset key `pulse_sw_reset_v164`

## a42/v164 (keep) — fixed status line + anchored crosshair tip

- `#status-line` now fixed width (`flex:0 0 16rem` + nowrap + ellipsis; full text via `title`;
  hidden `@media(max-width:640px)`). WHY: variable-length `setStatus()` text was resizing `.header-meta`
  and shifting the whole nav/栏目. Do NOT drop the fixed width.
- `placeChartCrosshairTip()` pins the OHLC readout to the chart top-left (`left/top=8px`), ignoring the
  cursor — applies to BOTH 分时 and 日/月/季 (one function → all charts). Box shrunk (min-width 8rem,
  font 0.62rem). Do NOT revert to cursor-following float.

## Rank→研判文案 linkage fix (a40, keep)

- BUG: rank click rotation fast path in `renderSectorDesk` (`hasPulseGrid && rotatePaint`)
  updated only `markPulseRankActive` + `paintPulseStockDesk` — the 板块动向研判 analysis
  text (`.sector-pulse-summary/detail/playbook/factors`), bias chip, kicker/blurb, and
  情报交叉 (`.sector-pulse-intel-grid`) stayed on the PREVIOUS sector.
- FIX: `patchPulseAnalysis(data)` updates those sub-nodes IN PLACE (no ranking rebuild →
  keeps scroll + instant switch). Called in the fast path before `paintPulseStockDesk`.
  Backend `sector_pulse.summary` is already per-active-sector (`当前聚焦「{active_label}」`).
- Result: clicking 今日排名 now resyncs the WHOLE 板块动向研判 block + 个股强弱 + 成分股/图表 together.
  Do NOT revert to stock-desk-only patch.

## Cross-section data prefetch (a39, keep)

- `prefetchSectionData(page)` + `scheduleSectionDataWarmup()` (end of app.js):
  warm OTHER sections' `pageDataKey` sessionStorage slots (idle staggered from
  3.5s, /api/sectors last; nav hover/touch re-fires; 4min re-warm; skips fresh
  slots / saveData / logged-out desk). First switch to any 栏目 paints from the
  slot via existing `paintFromPageDataCache`, network refresh follows.
- Slot shapes must stay in sync with `paintFromPageDataCache` branches
  (desk→portfolio, sectors→slim+sectorId, markets/earnings/intel/chains→raw).

## 2026-08-16 hardening (do not regress)

- FE: `safeUrl()` next to `escapeHtml` — ALL server/RSS `href` interpolations
  (indicators, index cards, agenda, listLinks, news/watch/spotlight/holding-intel
  cards, drivers, event nodes, vc-chip, earnings rows) go through it; http(s)/`/`
  only, else `#`. `escapeHtml` alone is NOT URL-safe (javascript: passes).
- BE: `portfolio.py` `_momentum_fields(c)` (was no-op ternary); `quotes.py`
  `_pct_from_change` derives % from price+change (fraction/percent ambiguity) +
  paren-negative `(1.2)` → -1.2 in `_parse_number`; ET dates via
  `datetime.now(_ET).date()` in quotes/sectors/market_map (not server-local);
  `earnings_calendar` rows isinstance guard; `config.py` atomic settings write;
  `auth.py` RLock + atomic register + `_DUMMY_HASH` anti-enumeration;
  `portfolio.py` RLock around add/remove/select; `app.py` `_BG_TASKS` strong
  refs for fire-and-forget `refresh_intel` tasks (2 sites).

## Design linkages that must work

Right pulse ranking click → **same tick**:

1. Rank 聚焦
2. Left 个股强弱与推荐 (`paintLinkedSectorDesk` / `stock_desk`)
3. Bottom 成分股 + selected chart / news / chain
4. URL `?sector=&symbol=`

Also: map tile → desk; pulse stock card → `selectSectorSymbol`; map TF 一周～四周 quiet `fillHorizon` (no force wipe).

## Keep both (do not trade off)

| Capability | Status |
|---|---|
| Map 1w–4w `fill_horizon` + cache merge | Keep |
| Empty stub must not wipe painted UI | Keep |
| Rank ↔ desk linkage | Keep (`paintLinkedSectorDesk`) |
| Unquoted shells not warm-cached | Keep |
| Soft prefetch key `soft:<sectorId>` | Keep |
| `/api/sectors` lite fallback after full timeout | Keep (`mode=lite`) |

**Incident:** User asked to “go back to map-only version”; three linkage commits were reverted and broke the desk. Restored via cherry-pick + rule. **Never repeat.**

## Known ops issues

- Render cold start / 502 during deploy
- Full desk can exceed 14s → API falls back to `mode=lite` (quotes + stock_desk), client upgrades after ~1.8s
- Sticky old SW → hard refresh / site data clear

## Key files

- `.cursor/rules/pulse-desk-linkage.mdc` — linkage guardrails
- `.cursor/rules/agent-memory.mdc` — this memory protocol
- `src/us_market_pulse/static/app.js`
- `src/us_market_pulse/market_map.py`, `sectors.py`, `app.py`, `us_markets.py`

## Open / watch

- After deploy: `/api/sectors?sector=semis` should return quoted picks (not 0) via lite if full times out
- Rank click links left desk + 成分股; map week tabs quiet fill
