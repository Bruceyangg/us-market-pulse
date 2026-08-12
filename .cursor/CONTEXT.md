# Pulse Desk — living context (agents must update)

Last updated: 2026-08-12 · tip pending `a37`

## Product

- App: **Pulse Desk** (`us-market-pulse`) — FastAPI + Jinja + `static/app.js`
- Live: https://us-market-pulse-6sqa.onrender.com/sectors
- Host: Render free Docker (cold starts common)

## Current shipped FE/SW

- Static `?v=20260811a37` (shipping)
- SW cache `pulse-desk-shell-v159` · reset key `pulse_sw_reset_v159`

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
