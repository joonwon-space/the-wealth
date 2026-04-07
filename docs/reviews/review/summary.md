# Code Review Summary — Sprint 10 Regression Fix (2026-04-07)

## Verdict: APPROVE

All 21 Sprint 10 test regressions have been resolved. Test count improved from 782 passed / 21 failed (main) to **803 passed / 0 failed** (sprint10-fixes). Build and lint checks pass cleanly.

## Must Fix (before merge)

None.

## Should Fix (before or soon after merge)

| # | Title | Severity | Reviewer | Location | Fix |
|---|-------|----------|----------|----------|-----|
| 1 | `_upsert_snapshot` opens its own `AsyncSessionLocal()` instead of accepting the caller's session — prevents transaction composability | medium | correctness | `kis_benchmark.py:168` | Accept `db: AsyncSession` parameter; pass from `collect_snapshots` caller |
| 2 | `DashboardMetrics.tsx` and `PortfolioList.tsx` in `components/dashboard/` duplicate `WidgetErrorFallback` pattern from `app/dashboard/page.tsx` | low | maintainability | `components/dashboard/*.tsx` | Extract `WidgetErrorFallback` to `ui/` shared component |

## Consider (optional improvements)

| # | Title | Severity | Reviewer | Location | Fix |
|---|-------|----------|----------|----------|-----|
| 1 | `kis_benchmark.py` creates two separate `httpx.AsyncClient` instances per index fetch — consider a shared client | low | performance | `kis_benchmark.py:72, 133` | Accept shared `httpx.AsyncClient` from caller |
| 2 | `index_snapshot.py` model uses `Mapped[float]` for `close_price` but column is `Numeric(18, 4)` — precision mismatch | low | correctness | `index_snapshot.py:27` | Use `Mapped[Decimal]` to match DB type |
| 3 | Rate limit on `settle_orders_endpoint` is 30/minute vs 10/minute on other order endpoints — inconsistent | low | security | `orders.py:355` | Align to 10/minute or document justification |

## Sensitive Path Check

Changed files on this branch include `backend/app/services/kis_domestic_order.py` and `backend/app/services/kis_overseas_order.py`. Both files are now thin re-export shims delegating to `kis_order.py` → `kis_order_place.py`. No order logic, credential handling, or financial calculation code was changed — only module organization and test mock patch paths were corrected.

## Review by Dimension

| Dimension | Verdict | Findings |
|-----------|---------|----------|
| Correctness | APPROVE | 1 medium finding (session isolation in benchmark) |
| Security | APPROVE | No security regressions; sensitive file changes are shims only |
| Performance | APPROVE | 1 low finding (shared httpx client) |
| Maintainability | APPROVE | 1 low finding (duplicated error fallback component) |

## Key Changes Reviewed

### Backend
- `kis_order.py` — backward-compatible re-export shim pointing to `kis_order_place`, `kis_order_cancel`, `kis_order_query`
- `kis_domestic_order.py`, `kis_overseas_order.py` — converted to thin re-exports from `kis_order.py`
- `kis_order_place.py` (384L) — consolidated domestic + overseas order placement, market-open checks, rate limiting, order locks
- `kis_order_cancel.py` (103L) — order cancellation logic
- `kis_order_query.py` (337L) — order query, pending orders, fill check
- `kis_benchmark.py` — unused `sqlalchemy.text` import removed (ruff F401 fix)
- `scheduler.py` — `collect_benchmark` key added to `_consecutive_failures` dict; single daily job at KST 16:20

### Tests
- `test_kis_order.py` — patched `kis_token.get_kis_access_token` directly (correct source module) and `kis_order_place._cache` (correct rate-limit module)
- `test_orders.py` — patched `kis_order_place.datetime` (correct module after split)
- `test_scheduler.py` — asserts 7 jobs (not 6 or 8); verifies `collect_benchmark` job id

### Frontend
- `OrderDialog.tsx` refactored to delegate to `OrderForm.tsx` + `OrderConfirmation.tsx`
- `DashboardPortfolioList.tsx` wraps `PortfolioList` with ErrorBoundary
- Build verified clean: `npm run build` exits 0
