# Release Readiness Report — Bug Fix: test_order_settlement (2026-04-04)

## Decision: GO

- Build: no production code changed, no build impact
- Tests: 3/3 pass in test_order_settlement.py (was 1/3); ruff lint clean
- Migrations: no schema changes
- API contracts: no API changes
- Coverage: order_settlement.py improved 23% -> 75%

# Release Readiness Report — 2026-04-04 (Sprint 8)

## Decision: GO

All 4 validators pass. No blockers. No pending migrations. CI is green on both Backend and Frontend.

---

## Check Results

| Check | Verdict | Key Metric |
|-------|---------|------------|
| Build | pass | 0 lint errors, frontend build clean (13 routes) |
| Tests | pass | 792/794 passed, 78% coverage (2 pre-existing failures) |
| Migrations | pass | No new migrations, head: k3l4m5n6o7p8 |
| API Contract | pass | 0 breaking changes, 1 new endpoint (fx-history) |

## Blockers

None.

## Warnings

- 2 pre-existing test failures in test_order_settlement.py (unrelated to Sprint 8).
- 15 frontend lint warnings (pre-existing, 0 errors).

---

## Release Notes

### Features
- Rate limiting applied to stocks, chart, alerts, and watchlist endpoints (30 req/min) — protects against API abuse
- Analytics page split into independently-loading sections (Metrics, Monthly Returns, Sector/FX, History) for better perceived performance
- Journal page now shows month-specific empty state with link to add trade when filtering by month
- Compare page period filter always visible (no longer hidden until portfolio is selected)

### Performance
- FX gain/loss endpoint now fetches prices in parallel (asyncio.gather) — eliminates N sequential Redis calls
- Analytics metrics exception fallback now uses parallel cache reads

### Security & Dependencies
- Fixed CVEs: pygments 2.20.0 (CVE-2026-4539), requests 2.33.0 (CVE-2026-25645)
- Updated: fastapi 0.135.3, redis 7.4.0, sentry-sdk 2.57.0, sqlalchemy 2.0.49, ruff 0.15.9
- Added currency_pair allowlist validation on /analytics/fx-history endpoint
- Analytics router code split into domain-specific modules (analytics_metrics, analytics_history, analytics_fx)
- KIS order service split into domain-specific re-export modules (kis_domestic_order, kis_overseas_order, kis_order_query)

### Internal
- Analytics module split: analytics.py kept as backward-compat shim with docstring
- Shared analytics utility functions extracted to analytics_utils.py service

## Pre-Release Checklist
- [x] All blockers resolved
- [x] No new migrations (skip alembic upgrade)
- [x] No new environment variables required
- [x] CI green (Backend + Frontend)
- [x] CVEs patched

Generated: 2026-04-04
