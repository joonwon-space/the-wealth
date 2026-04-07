# Release Readiness Report — Sprint 10 Regression Fix (2026-04-07)

## Decision: CONDITIONAL GO

All 4 validators pass. The regression fix is production-ready. One conditional: the local dev database has a migration drift (auditaction enum already exists from a prior migration run outside Alembic). This must be resolved before running `alembic upgrade head` on any environment where those objects already exist.

## Validator Results

| Validator | Status | Detail |
|-----------|--------|--------|
| build-validator | PASS | ruff clean (F401 in kis_benchmark.py fixed), tsc clean, frontend `npm run build` exits 0 |
| test-runner | PASS | **803 passed / 0 failed** (up from 782/21 on main). All 21 Sprint 10 regressions resolved. |
| migration-checker | CONDITIONAL | Migrations `k3l4m5n6o7p8` and `l4m5n6o7p8q9` are additive only. Dev DB has migration drift (auditaction enum pre-exists). Use `alembic stamp` to mark current revision before upgrading. |
| api-contract-checker | PASS | No breaking API changes. All backward-compatible re-exports preserved. `kis_order.py` shim exports all original symbols. |

## Release Notes

### Sprint 10 Regression Fix

**Root cause:** Sprint 10 file split (kis_order.py → kis_order_place.py + kis_order_cancel.py + kis_order_query.py) used a different module decomposition in main vs sprint10-fixes. The test mock patches targeted old module paths that became re-export shims, causing mocks to be no-ops and 21 tests to fail.

**Changes applied:**
- `tests/test_kis_order.py` — patch `kis_token.get_kis_access_token` directly (source module) and `kis_order_place._cache` (correct rate-limit location)
- `tests/test_orders.py` — patch `kis_order_place.datetime` (correct module after split)
- `tests/test_scheduler.py` — assert 7 scheduler jobs (includes `collect_benchmark`); verify `collect_benchmark` job id
- `kis_benchmark.py` — remove unused `sqlalchemy.text` import (ruff F401)

**Architecture difference from main:**
- sprint10-fixes uses `kis_order_place.py` as the single consolidated module for domestic + overseas order placement
- main uses separate `kis_domestic_order.py` and `kis_overseas_order.py` for each market
- sprint10-fixes is the correct branch — all tests pass at 803

## Deployment Instructions

1. Pull `sprint10-fixes` branch
2. Check alembic current: `alembic current`
3. If at `cdf80f13c5f6`, run: `alembic upgrade head` (applies k3l4m5n6o7p8 and l4m5n6o7p8q9)
4. If auditaction enum already exists (from prior manual migration), run: `alembic stamp k3l4m5n6o7p8` then `alembic upgrade head`
5. `pip install -r requirements.txt` (no new dependencies)
6. Restart backend service

## Blockers

None for the regression fix itself. Migration drift in dev DB is a pre-existing issue unrelated to this fix.

## Post-Deploy Monitoring

- Verify test suite passes in CI: 803 tests, 0 failures
- Confirm scheduler registers 7 jobs at startup (check logs for `Starting benchmark snapshot collection`)
- Rate limit on order endpoints (10/minute) returns HTTP 429 when exceeded — expected
