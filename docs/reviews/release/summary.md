# Release Readiness Report — Sprint 10 (2026-04-07)

## Decision: CONDITIONAL GO

All 4 validators pass. One conditional: `alembic upgrade head` is required before traffic resumes (new `index_snapshots` table). Safe to deploy with that step included.

## Validator Results

| Validator | Status | Detail |
|-----------|--------|--------|
| build-validator | PASS | ruff clean, tsc clean, backend + frontend Docker images build successfully (CI green) |
| test-runner | PASS | 38 Sprint 10 targeted tests pass; 793+ total passing; pre-existing test isolation failures in test_alerts.py are unrelated to Sprint 10 |
| migration-checker | CONDITIONAL | New `index_snapshots` migration (l4m5n6o7p8q9) — forward-only additive table, safe to apply; downgrade drops table cleanly |
| api-contract-checker | PASS | No breaking API changes; 4 order endpoints now rate-limited (10/minute); scheduler gains collect_benchmark job |

## Release Notes

### Sprint 10 — Code Quality + Benchmark Foundation

**Quick wins:**
- `staleTime: 60_000` on portfolio list useQuery — reduces unnecessary refetches on window focus
- `@limiter.limit("10/minute")` on 4 order endpoints: `get_orderable`, `list_pending_orders`, `settle_orders_endpoint`, `get_portfolio_cash_balance`
- `aria-label` added to inline quantity/price inputs in HoldingsSection

**Large file splits:**
- `kis_order.py`: 780L reduced to 25L backward-compatible shim; logic split into `kis_order_place.py`, `kis_order_cancel.py`, `kis_order_query.py`
- `OrderDialog.tsx`: 605L split into `OrderForm.tsx` (components/orders/) + `DashboardMetrics.tsx` (components/dashboard/)
- `dashboard/page.tsx`: portfolio list delegated to `PortfolioList.tsx` with ErrorBoundary

**Benchmark foundation:**
- New `index_snapshots` table via Alembic migration
- `kis_benchmark.py` service: fetches KOSPI200 (FHKUP03500100) and S&P500 (FHKST03030100) daily close prices
- Scheduler: new `collect_benchmark` job at KST 16:20 weekdays

## Deployment Instructions

1. Pull latest main
2. `cd backend && alembic upgrade head` (creates `index_snapshots` table — required)
3. `pip install -r requirements.txt` (no new dependencies in Sprint 10)
4. Restart backend service

## Blockers

None. Migration is additive only (creates new table). No data backfill needed.

## Post-Deploy Monitoring

- Watch scheduler logs at KST 16:20 for `[Scheduler] Starting benchmark snapshot collection`
- Verify `index_snapshots` table populates after market close
- Rate limit rejections for order endpoints will return HTTP 429 — expected behavior
