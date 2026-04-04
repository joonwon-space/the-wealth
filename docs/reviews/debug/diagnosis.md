# Bug Diagnosis: test_order_settlement.py — 2 failing tests

**Date:** 2026-04-04
**Confidence:** HIGH
**Severity:** MEDIUM (test infrastructure, not production logic)

---

## Failing Tests

- `tests/test_order_settlement.py::TestSettlePendingOrders::test_settle_fully_filled_order`
- `tests/test_order_settlement.py::TestSettlePendingOrders::test_settle_partial_fill`

## Assertion Failure

Both tests fail at `assert counts["settled"] == 1` (or `partial`) with `assert 0 == N`.
`settle_pending_orders` returns `{"settled": 0, "partial": 0, "unchanged": 0}` because it finds
zero pending orders in the database.

---

## Root Cause

**Session Isolation Mismatch** — the tests use two different database sessions that do not share
the same connection.

### How the test fixture works

`conftest.py: client` fixture overrides `app.dependency_overrides[get_db]` with a test-specific
`async_sessionmaker` bound to a NullPool engine pointing at `the_wealth_test` database. All HTTP
requests go through this override and see committed rows in the test DB.

### What the test does

1. HTTP POST `/portfolios/{pid}/orders` via `client` — order is persisted and committed through
   the **test** session factory.
2. `async with AsyncSessionLocal() as db:` — opens a brand-new session via the **production**
   `AsyncSessionLocal` (imported from `app.db.session`), which is bound to the production DB URL
   (`DATABASE_URL` env var, defaulting to a different DB). No orders exist in that session →
   `pending_orders` is empty → `settle_pending_orders` returns all zeros.

### Exact mismatch

| Step | Session factory | DB |
|------|----------------|----|
| POST /orders (via client fixture) | Test factory (NullPool, test DB URL) | `the_wealth_test` |
| `AsyncSessionLocal()` in test body | Production factory | `the_wealth` (or env `DATABASE_URL`) |

### Why test_settle_no_pending_orders passes

That test does NOT check counts against expected non-zero values — it asserts
`counts == {"settled": 0, "partial": 0, "unchanged": 0}`, which matches trivially whether or not
the production session factory is used.

---

## Fix Plan

**Option A (recommended): Pass the test DB session directly**

The tests should NOT call `AsyncSessionLocal()` at all. Instead, they should inject the same
session that the HTTP client uses, or use a fresh session from the **test** engine/factory.

The cleanest fix: expose the test `factory` from the `client` fixture, or provide an additional
`db_factory` fixture that creates sessions from the same test engine.

**Concrete steps:**

1. Add a `db_factory` session-scoped fixture (or function-scoped) to `conftest.py` that yields an
   `async_sessionmaker` bound to the test engine.
2. In the two failing tests, replace:
   ```python
   from app.db.session import AsyncSessionLocal
   async with AsyncSessionLocal() as db:
       counts = await settle_pending_orders(db=db, ...)
   ```
   with:
   ```python
   async with test_session_factory() as db:
       counts = await settle_pending_orders(db=db, ...)
   ```
3. The `db_factory` fixture must use the same `TEST_DB_URL` as the `client` fixture.

**Option B: Pass the DB session via fixture parameter**

Add a `db_session` fixture argument to the failing tests alongside `client`, then call
`settle_pending_orders(db=db_session, ...)`. However, this has a subtlety: the `db` fixture in
conftest calls `_clean_all_data()` again, which would wipe the order just created via `client`.
Use a separate lightweight session fixture for this purpose.

**Chosen approach: Option A with a new `test_db_session` async fixture** that uses the same
`TEST_DB_URL` without calling `_clean_all_data()` (data is already cleaned by `client` fixture).

---

## Coverage Gap (23%)

`order_settlement.py` has 64 lines, 49 uncovered. The two failing tests cover the main paths but
currently never reach the service logic because of the session mismatch. Once fixed, coverage will
rise to ~85%+. Remaining uncovered paths:

- SELL order settlement (holding deletion / quantity reduction)
- Order with no `order_no`
- Order not present in `filled_map` (unchanged path)
- Holding `avg_price` recalculation on BUY with existing holding

Additional unit tests should be added for these paths.

---

## Files to Change

- `backend/tests/conftest.py` — add `test_session_factory` fixture
- `backend/tests/test_order_settlement.py` — use `test_session_factory` instead of
  `AsyncSessionLocal`

No changes to production code are required.
