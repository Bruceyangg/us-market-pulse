# Pulse Desk — living context (agents must update)

Last updated: 2026-08-16 · shipping `a43/v165`

## Product

- App: **Pulse Desk** (`us-market-pulse`) — FastAPI + Jinja + `static/app.js`
- Live: https://us-market-pulse-6sqa.onrender.com/sectors
- Host: Render free Docker (cold starts common)

## Current shipped FE/SW

- Static `?v=20260811a43` (shipping)
- SW cache `pulse-desk-shell-v165` · reset key `pulse_sw_reset_v165`

## a43/v165 (keep) — APK readiness (TWA/PWABuilder) + touch swipe-nav

- manifest is PWABuilder-optimal: `id`, `orientation:any` (tablet landscape; do NOT relock portrait),
  `display_override`, `categories`, `dir`, `prefer_related_applications:false`.
- `GET /.well-known/assetlinks.json` (app.py) serves Digital Asset Links from env
  `TWA_PACKAGE_NAME` + `TWA_SHA256_FINGERPRINTS` (comma-sep colon-hex); empty `[]` until set. Set on
  Render after PWABuilder to drop the TWA URL bar. Do NOT hardcode fingerprints in code.
- Touch-only swipe-nav re-enabled via `bindTouchSwipeNav()` in `bindStickyNavChrome` — horizontal swipe
  runs `cycleNav`, guarded by `canConsumeHorizontalScroll`/`isEditableTarget` + skips `.chart-zoom` +
  vertical-intent. Pointer/trackpad intentionally NOT bound. Do NOT bind swipe to mouse/wheel.

## iOS native .ipa (sideload path, user opted in)

- `ios-app/` = Capacitor v6 wrapper; `capacitor.config.json` `server.url` = live Render URL (thin
  WKWebView shell, no bundled assets). `ios-app/.gitignore` excludes `ios/` + `node_modules/` (CI regenerates).
- `.github/workflows/ios.yml` (macOS runner, no local Mac needed): `npm i` → `cap add/sync ios` →
  `xcodebuild ... CODE_SIGNING_ALLOWED=NO` → zip Payload → **UNSIGNED** `PulseDesk-unsigned.ipa` →
  GitHub Release tag `ios-latest`. Triggers on push to `ios-app/**` or manual dispatch.
- Download (public, no login): https://github.com/Bruceyangg/us-market-pulse/releases/download/ios-latest/PulseDesk-unsigned.ipa
- User side: Sideloadly (Windows) + free Apple ID → USB install → trust profile → re-sign every 7 days.
- `gh` NOT available locally → can't dispatch/read logs; poll GH API for release/run status; ask user for logs on failure.
- Render Docker only copies pyproject/uv.lock/README/src, so `ios-app/` + `.github/` do NOT affect prod.

## iOS install = PWA "Add to Home Screen" (NO Apple cert needed)

- iPhone install path is Safari → Share → 添加到主屏幕 (free, no App Store, no $99 dev program).
  Apple meta tags already in base.html (`apple-mobile-web-app-capable`, status-bar-style, title,
  apple-touch-icon). base.html detection now also treats `display-mode:standalone` /
  `navigator.standalone` as app mode → iOS home-screen AND Android TWA both get `pulse-native-app` chrome.
  base.html is served no-store and SW never intercepts navigations, so this ships without a version bump.

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
