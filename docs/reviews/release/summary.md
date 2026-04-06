# Release Readiness Report — Sprint 9 (2026-04-06)

## Decision: GO

All 4 validators pass. Ready to deploy.

## Validator Results

| Validator | Status | Detail |
|-----------|--------|--------|
| build-validator | PASS | ruff clean, tsc clean, CI green (both pipelines) |
| test-runner | PASS | 794 tests pass, pytest-asyncio 1.3.0 compatible |
| migration-checker | PASS | No schema changes, no migration needed |
| api-contract-checker | PASS | No breaking changes, all URLs preserved |

## Release Notes

### Sprint 9 — Dependency upgrades & code quality

**Security / CVE patches:**
- requests 2.32.5 -> 2.33.0 (CVE-2026-25645)
- starlette 0.52.1 -> 1.0.0 (includes security fixes)

**Dependency upgrades:**
- pytest-asyncio 0.25.3 -> 1.3.0
- All CVEs confirmed clear via pip-audit

**Code quality (refactoring):**
- analytics.py 762L -> 16L backward-compat shim
- portfolios.py 751L split into portfolio_holdings.py (266L) + portfolio_transactions.py (212L) + portfolios.py (170L)
- dashboard/page.tsx 603L split into DashboardMetrics.tsx (225L) + PortfolioList.tsx (136L) + page.tsx (~280L)

**UX improvements:**
- analytics/page.tsx: MetricsSection, HistorySection, MonthlyReturnsSection, SectorFxSection each wrapped with ErrorBoundary
- KisCredentialsSection delete toast updated to "KIS 계좌가 삭제되었습니다"

## Deployment Instructions

1. `pip install -r requirements.txt` (starlette + pytest-asyncio upgrades)
2. No `alembic upgrade head` needed (no schema changes)
3. Deploy as normal

## Blockers

None.
