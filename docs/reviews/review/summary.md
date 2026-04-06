# Code Review Summary — Sprint 10 (2026-04-07)

## Verdict: APPROVE

Sprint 10 is a code quality + benchmark foundation sprint. All CI checks pass (CodeQL, Docker build). 38 Sprint 10 targeted tests pass (test_scheduler.py 16, test_kis_order.py 22). Frontend builds cleanly.

## Must Fix (before merge)

None.

## Should Fix (before or soon after merge)

| # | Title | Severity | Reviewer | Location | Fix |
|---|-------|----------|----------|----------|-----|
| 1 | `_upsert_snapshot` opens a new session inside `collect_snapshots` instead of accepting the caller's session | medium | correctness | kis_benchmark.py:168 | Accept `db: AsyncSession` parameter to allow transaction control from caller |
| 2 | `_consecutive_failures` dict missing `collect_benchmark` key — KeyError possible if job fails before counter initialized | medium | correctness | scheduler.py:51 | Add `"collect_benchmark": 0` to initial dict |
| 3 | `DashboardMetrics.tsx` and `PortfolioList.tsx` in `components/dashboard/` duplicate `WidgetErrorFallback` from `app/dashboard/page.tsx` | low | maintainability | components/dashboard/*.tsx | Extract `WidgetErrorFallback` to shared `ui/` component |

## Consider (optional improvements)

| # | Title | Severity | Reviewer | Location | Fix |
|---|-------|----------|----------|----------|-----|
| 1 | `kis_benchmark.py` creates two separate `httpx.AsyncClient` instances per index fetch — consider passing a shared client | low | performance | kis_benchmark.py:72, 133 | Accept shared `httpx.AsyncClient` from caller |
| 2 | `index_snapshot.py` model uses `Mapped[float]` for `close_price` but column type is `Numeric(18, 4)` — precision mismatch | low | correctness | index_snapshot.py:27 | Use `Mapped[Decimal]` to match DB type |
| 3 | Rate limit on `settle_orders_endpoint` (L396) is 30/minute not 10/minute — inconsistent with other endpoints | low | security | orders.py:355 | Align to 10/minute or document why higher limit is acceptable |

## Sensitive Path Check

Changed files include `backend/app/api/orders.py` (rate limit decorators only) and `backend/app/services/scheduler.py` (new benchmark job). No auth logic, credential handling, or transaction logic modified.

## Review Statistics
- Correctness: approve with 2 findings
- Security: approve with 1 finding (rate limit inconsistency)
- Performance: approve with 1 finding
- Maintainability: approve with 1 finding
- Total unique findings: 5 (after dedup)
