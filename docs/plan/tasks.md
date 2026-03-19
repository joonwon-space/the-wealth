# THE WEALTH — Tasks

Current work items. Read by `/auto-task` and `/next-task`.
Each item should be completable in a single commit.

---

## Completed (archive)

<details>
<summary>Previously completed items</summary>

- [x] `filelock` 3.19.1 -> 3.25.2 upgrade
- [x] `python-jose` -> `PyJWT` migration
- [x] `passlib` -> `bcrypt` direct usage migration
- [x] `backend/.env.example` CORS_ORIGINS addition
- [x] KIS credential API connection test endpoint + UI
- [x] Milestone 11-1: Mobile UX (all items)
- [x] Milestone 11-2: Analytics page enhancement (all items)
- [x] Milestone 11-3: Holdings table 52-week high/low (all items)
- [x] Milestone 11-3: Watchlist (all items)
- [x] Milestone 11-4: Stock detail page (all items)
- [x] Milestone 11-5: UX convenience features (all items)
- [x] Milestone 12-1: Price history & day change (all items)
- [x] Milestone 12-2: SSE real-time prices (all items)
- [x] Milestone 12-3: Performance optimization (all items)
- [x] Milestone 12-3b: Query optimization (all items)
- [x] Milestone 12-4: Alert system (all items)
- [x] Milestone 12-5: API quality improvement (all items)
- [x] Milestone 13-1: Portfolio history API + chart (all items)
- [x] Milestone 14: Dockerfile multi-stage build
- [x] Milestone 14-2: Backend structured logging (structlog)
- [x] Milestone 14-3: CI/CD Docker build verification
- [x] Milestone 14-3 / 16-3: CI/CD & code quality (all items)
- [x] Milestone 14-4: Security headers (all items)
- [x] Milestone 15-4: Data export - CSV (all items)
- [x] Milestone 16-1: Claude Code agent expansion (all items)
- [x] Milestone 16-2: Test coverage 70%+ (all items)
- [x] Milestone 16-2: Playwright E2E test setup (all items)
- [x] Milestone 16-2b: Test coverage expansion (all items)
- [x] Milestone 16-3: openapi-typescript type generation (all items)
- [x] Short-term improvements: DB indexes, legacy columns, rate limits, ticker validation, pagination cap, soft delete, HttpOnly cookies, Error Boundary, bundle optimization, Graceful Shutdown
- [x] Milestone 10: AI browser agent (all items)
- [x] portfolios.py split - CSV export to portfolio_export.py
- [x] Fix ruff lint errors in test files (10 errors)
- [x] Test coverage 71% -> 93% (add router tests + .coveragerc sysmon fix)
- [x] Milestone 16-3: Commitlint config + Husky hook
- [x] Milestone 12-2: SSE connection hardening (per-user limit, heartbeat, 2h timeout)
- [x] Next.js middleware deprecation fix
- [x] Test coverage gaps (prices.py 61%, dashboard.py 85%)
- [x] P0 Automated DB Backup: daily pg_dump script + retention policy
- [x] P0 Single Server Resilience: restart policy + managed DB/Redis docs

</details>

---

## Current work

### Milestone 12-4: Alert Notification Logic (P1)
Alert CRUD exists but no price-triggered notification logic.

- [ ] Add `last_triggered_at` column to `alerts` table via Alembic migration
- [ ] Integrate alert condition check into SSE stream loop — emit `alerts` event when triggered; dedup with 1h cooldown; auto-deactivate after trigger
- [ ] Add `PATCH /alerts/{id}` endpoint to reactivate/update alert `is_active` and `threshold`

### Milestone 16-2: Frontend Test Coverage (P1)
Backend coverage 93% vs frontend minimal.

- [ ] Add `lib/format.ts` unit tests (formatKRW, formatUSD, formatPrice, formatNumber, formatRate, formatPnL)
- [ ] Add `store/auth.ts` Zustand store tests (login, logout, initialize with cookie mock)
- [ ] Add `hooks/usePriceStream.ts` tests (connect, skip when disabled, skip when no token, close on unmount)

### Milestone 13-5c: Adaptive Cache TTL (P2)
After market close, price cache TTL should extend from 300s to 24h to reduce KIS API calls.

- [ ] Add `get_adaptive_ttl()` helper in `services/kis_price.py` — returns 300s during market hours, 86400s after close
- [ ] Apply adaptive TTL in `services/kis_price.py` Redis cache write

### Milestone 13-5b: Data Integrity Health Checks (P2)

- [ ] Add `GET /health/data-integrity` endpoint — check for `price_snapshots` gaps (missing weekday snapshots in last 7 days) and return summary JSON
