# KIS API Resilience Review -- 2026-03-21

## Summary

Review of the KIS API failure detection and degraded mode implementation completed between 2026-03-19 and 2026-03-21. This subsystem spans backend dashboard API, frontend degraded banner, KIS health service, and error handling in `kis_account.py`.

## Strengths

- **Degraded mode detection**: When all price fetches fail (fetched_count == 0), `kis_status` is set to `"degraded"` in `DashboardSummary`. Frontend displays a warning banner with `TriangleAlert` icon to inform users.
- **Startup health check**: `kis_health.py` performs a HEAD request to KIS API at app startup. On failure, sets a global `KIS_AVAILABLE` flag to false, enabling cache-only mode across the price services.
- **Explicit error propagation**: `kis_account.py` now raises `RuntimeError` on KIS API failures instead of silently returning empty arrays. This prevents incorrect "0 holdings" display when the API is actually down.
- **Graceful degradation**: Even in degraded mode, Redis-cached prices are used as fallback. The dashboard still renders with stale prices rather than showing empty data.
- **Data integrity endpoints**: Three new health check endpoints (`/health/data-integrity`, `/health/holdings-reconciliation`, `/health/orphan-records`) provide operational visibility into data consistency.
- **Backup health integration**: `/api/v1/health` now includes `last_backup_at` and `backup_age_hours` for backup monitoring.
- **Internal API**: `/internal/backup-status` records backup results to `sync_logs` with shared-secret auth (not exposed to public).

## Issues Found

### Critical

- None identified.

### Medium

- **Test regression**: 2 tests in `test_overseas_support.py` fail because they still expect empty arrays from `fetch_overseas_account_holdings` on API error, but the function now raises `RuntimeError`. These tests need to be updated to use `pytest.raises(RuntimeError)`.

### Low / Suggestions

- The `kis_status` field only has two states (`"ok"` and `"degraded"`). A `"partial"` state (some but not all tickers failed) could provide finer granularity.
- The KIS health check at startup is one-shot. Periodic re-checks (e.g., every 5 minutes) could auto-recover from transient KIS outages without requiring a restart.
- Consider adding `kis_status` to the SSE price stream events so real-time clients also see degradation state changes.

## Verdict

The KIS API resilience implementation is well-designed and covers the primary failure scenarios. The degraded banner provides clear user feedback. The main action item is fixing the 2 failing tests in `test_overseas_support.py` to match the updated `RuntimeError` behavior.
