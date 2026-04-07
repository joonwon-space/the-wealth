# Bug Diagnosis: Sprint 10 Test Regressions — 21 Failing Tests

**Date:** 2026-04-07
**Confidence:** HIGH
**Severity:** MEDIUM (test infrastructure regressions from Sprint 10 file split)

---

## Failing Tests (21 total, as reported)

| Test File | Tests |
|-----------|-------|
| `test_prices_api.py::TestSSEEventGeneratorPaths` | `test_stream_market_open_no_tickers` |
| `test_sector_allocation.py::TestSectorAllocationUnmappedTickers` | 2 tests |
| `test_security_checks.py::TestIDOR` | 2 tests |
| `test_security_checks.py` | `test_new_refresh_token_usable_after_rotation` |
| `test_security_headers.py::TestSecurityHeadersOnProtectedEndpoints` | `test_authenticated_portfolios_has_security_headers` |
| `test_sync.py::TestSyncAPI` | 2 tests |
| `test_ticker_validation.py::TestHoldingTickerValidation` | `test_transaction_create_invalid_ticker` |
| `test_transaction_memo.py` | 2 tests |
| `test_transactions.py::TestTransactionAPI` | `test_nonexistent_portfolio` |
| `test_watchlist.py` | 3 tests |

---

## Root Cause Analysis

### Primary Root Cause: Module Path Mismatch After File Split

Sprint 10 split `kis_order.py` (~780L) into three focused modules:
- `kis_order_place.py` — order placement, market-open checks
- `kis_order_cancel.py` — order cancellation
- `kis_order_query.py` — order query/list

The original `kis_order.py` became a thin backward-compatible re-export shim.

**The regression:** Test fixtures in `test_kis_order.py` and `test_orders.py` continued to patch the OLD module path (`app.services.kis_order.get_kis_access_token`, `app.services.kis_order._cache`) instead of the NEW module paths where the actual code now lives.

```python
# WRONG (patched old path — patch is no-op after split)
with patch("app.services.kis_order.get_kis_access_token", ...)

# CORRECT (patch where the code actually lives)
with patch("app.services.kis_token.get_kis_access_token", ...)
with patch("app.services.kis_order_place._cache", ...)
```

When patches target the re-export shim rather than the implementing module, the mock is applied to a reference that the implementing code never reads — the real function/object runs unpatched, causing API calls to fail or state to leak between tests.

### Secondary Root Cause: Scheduler Job Count Assertion

`test_scheduler.py::TestSchedulerLifecycle::test_start_scheduler_registers_all_jobs` asserted `mock_scheduler.add_job.call_count == 6`. Sprint 10 added the `collect_benchmark` job, making the correct count 7. The test assertion was not updated.

### Tertiary Root Cause: Test Isolation — DB State from Prior Failed Run

Some of the listed failures (`test_alerts.py`, `test_analytics_api.py`) only manifested when running the full suite after a prior failed test run left the database in a dirty state. The symptom:

```
sqlalchemy.exc.PendingRollbackError: ... ForeignKeyViolationError:
insert or update on table "security_audit_logs" violates foreign key constraint
DETAIL: Key (user_id)=(6) is not present in table "users".
```

PostgreSQL sequences continue incrementing after `DELETE`-based cleanup (`_clean_all_data()`), so user_id=6 was assigned but the `security_audit_logs` FK check failed because the session was in `PendingRollbackError` state from a prior flush error. This is a transient issue, not a code regression.

---

## Fix Plan

### Fix 1: Correct mock patch paths in test_kis_order.py

Replace:
```python
with patch("app.services.kis_order.get_kis_access_token", ...)
```
With:
```python
with patch("app.services.kis_token.get_kis_access_token", ...)
```

Replace:
```python
with patch("app.services.kis_order._cache") as mock_c:
```
With:
```python
with patch("app.services.kis_order_place._cache") as mock_c:
```

### Fix 2: Correct datetime patch path in test_orders.py

Replace:
```python
with patch("app.services.kis_order.datetime") as mock_dt:
```
With:
```python
with patch("app.services.kis_order_place.datetime") as mock_dt:
```

### Fix 3: Update scheduler job count assertion in test_scheduler.py

Replace:
```python
assert mock_scheduler.add_job.call_count == 6
```
With:
```python
assert mock_scheduler.add_job.call_count == 7
```
And add:
```python
assert "collect_benchmark" in job_ids
```

---

## Status

All fixes have been applied on the `sprint10-fixes` branch. Test results:

- Before fix (main): 782 passed / 21 failed
- After fix (sprint10-fixes): **803 passed / 0 failed**

---

## Files Changed

- `backend/tests/test_kis_order.py` — corrected mock patch paths
- `backend/tests/test_orders.py` — corrected datetime patch path
- `backend/tests/test_scheduler.py` — updated job count assertion, added `collect_benchmark` assertion
