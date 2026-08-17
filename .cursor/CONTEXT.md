# Pulse Desk — living context (agents must update)

Last updated: 2026-08-16 · tip pending `a38`

## Product

- App: **Pulse Desk** (`us-market-pulse`) — FastAPI + Jinja + `static/app.js`
- Live: https://us-market-pulse-6sqa.onrender.com/sectors
- Host: Render free Docker (cold starts common)

## Current shipped FE/SW

- Static `?v=20260811a38` (shipping)
- SW cache `pulse-desk-shell-v160` · reset key `pulse_sw_reset_v160`

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
