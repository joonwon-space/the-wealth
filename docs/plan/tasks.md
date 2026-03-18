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

</details>

---

## Lint/Code Quality Fixes

- [x] Fix ruff lint errors in test files (10 errors) -- remove unused imports and variables in `tests/test_dashboard.py`, `tests/test_price_snapshot.py`, `tests/test_scheduler.py`

## Test Coverage Improvement (71% -> 80%)

- [x] `api/chart.py` router tests -- currently 25% coverage, add tests for daily chart data endpoint with KIS API mocking
- [ ] `api/sync.py` router tests -- currently 29% coverage, add tests for balance sync, portfolio sync, sync logs endpoints
- [ ] `api/portfolios.py` router tests -- currently 36% coverage, add tests for holdings CRUD, transactions CRUD, KIS account linking
- [ ] `api/prices.py` router tests -- currently 38% coverage, add tests for price history and SSE stream endpoints
- [ ] `api/stocks.py` router tests -- currently 38% coverage, add tests for stock search and detail endpoints
- [ ] `api/portfolio_export.py` router tests -- currently 48% coverage, add tests for CSV export with various data scenarios
- [ ] `api/users.py` router tests -- currently 54% coverage, add tests for KIS account CRUD and connection test

---
