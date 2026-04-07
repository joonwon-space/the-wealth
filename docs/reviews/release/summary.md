# Release Readiness Report — Sprint 12 (2026-04-07)

## Decision: GO

Sprint 12 changes are production-ready.

---

## Validation Results

### Build Validator
- Backend ruff: PASS (0 errors)
- Frontend tsc --noEmit: PASS (0 errors)
- Frontend npm build: PASS (production build successful)
- npm audit: PASS (0 vulnerabilities, vite 8.0.6 installed)

### Test Runner
- 824 tests collected
- No new tests added (changes are config/decorator additions and UI improvements, existing tests cover the endpoints)
- Previous CI run on branch: Backend CI SUCCESS, Frontend CI SUCCESS

### Migration Checker
- No Alembic migrations changed or added
- No schema changes required
- PASS — no migration risk

### API Contract Checker
- Rate limit decorators added to existing endpoints — no breaking changes to response shape
- `Request` parameter added to function signatures (FastAPI internal, not exposed to clients)
- Benchmark query now sends additional `from`/`to` query params — backend already supports optional date filtering per the analytics.py implementation
- PASS — no API contract breakage

### Security Assessment
- SEC-001/SEC-004: Rate limits close coverage gaps on 8 previously unprotected endpoints
- TD-001: CVE GHSA-4w7w-66w2-5vf9 patched (vite path traversal)
- No sensitive paths modified

---

## Release Notes

### Sprint 12 — Security Quick Wins + UX Polish

**Security**
- 6 transaction endpoints now rate-limited at 60/minute (SEC-001)
- 2 holdings GET endpoints now rate-limited at 30/minute (SEC-004)
- Vite CVE GHSA-4w7w-66w2-5vf9 patched (vite 8.0.4 -> 8.0.6)

**UX Improvements**
- Journal page: filter empty state now shows '필터 조건에 맞는 거래가 없습니다' with a Reset button
- Analytics metrics: informational banner when all advanced metrics (Sharpe/MDD/CAGR) are null
- Benchmark overlay: now synced with the active period filter (from/to dates passed to API)

**Code Quality**
- AccountSection userMe query: staleTime 60_000ms added (reduces unnecessary refetches)
- tasks.md: all Sprint 12 items marked complete
