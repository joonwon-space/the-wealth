# Team Review Summary — sprint-3 (2026-04-03)

## Verdict: APPROVE

## Changes Reviewed

19 files changed across backend (Python) and frontend (TypeScript/React) — 329 insertions, 137 deletions.

---

## Correctness Review

**Verdict: APPROVE — 1 finding (minor)**

- PASS: SEC-001 Sentry scrubbing: `before_send` header dict comprehension is correct. The `from None` re-raise chain in kis_order/kis_token correctly strips httpx exception context.
- PASS: PERF-001 DISTINCT ON: Raw SQL via `text()` with parameterized `:tickers` and `:today` — no SQL injection risk. `fetchall()` returns named rows (`row.ticker`, `row.close`) correctly accessed.
- PASS: SEC-002 bcrypt DoS: `Field(min_length=8, max_length=128)` + existing `field_validator` both run — valid defense in depth.
- PASS: PERF-002 fx-gain-loss cache: cache_key includes `current_user.id` — no cross-user cache leak.
- PASS: PERF-005 ConnectionPool: Pool is lazily initialized and shared; `client.aclose()` in finally block correctly returns connection to pool without closing the pool itself. `decode_responses=True` matches prior behavior.
- MINOR: PERF-004 SSE polling: `streamActiveRef.current` in the `refetchInterval` closure is captured at render time. The ref will update via `useEffect`, but the query's `refetchInterval` only re-evaluates on re-render. This is correct behavior for refs in TanStack Query — the interval check runs on each refetch cycle, not just at render. No issue.
- PASS: UX-007 AlertDialog: `onOpenChange` guard `if (!open)` correctly resets state on close or backdrop click. `deleteTxnId !== null` and `deleteConfirmId !== null` null-checks before `.mutate()` prevent null mutations.

---

## Security Review

**Verdict: APPROVE — 0 findings**

- PASS: SEC-001: `appkey`, `appsecret`, `authorization` scrubbed from Sentry events. `from None` chain eliminates httpx credential leak in exception context.
- PASS: SEC-002: 128-char password limit applied at schema validation layer — reaches bcrypt before length could be abused.
- PASS: SEC-004: `process.env.NODE_ENV === "development"` evaluated at build time in next.config.ts — production builds will NOT include `unsafe-eval`.
- PASS: SEC-006: `Annotated[str, Field(max_length=50)]` with outer `Field(None, max_length=20)` — Pydantic v2 applies both list length and item length constraints.
- PASS: PERF-005: No credentials exposed in pool URL — `settings.REDIS_URL` is env-var sourced.
- PASS: PERF-001: Parameterized SQL (`text()` + bind params) — safe from SQL injection.
- PASS: PERF-002: Cache key scoped to `current_user.id` — no cache poisoning or cross-user data exposure.

---

## Performance Review

**Verdict: APPROVE — 0 findings**

- PASS: PERF-001: DISTINCT ON (ticker) returns N rows (one per ticker) vs full history table scan. Correct index usage — `price_snapshots` has index on `(ticker, snapshot_date)`.
- PASS: PERF-005: Single `ConnectionPool` lazily created, `max_connections=20` reasonable for this workload. `client.aclose()` returns connection to pool, not closing TCP. All 4 call sites migrated.
- PASS: PERF-002: `analytics:fx_gain_loss:{user_id}` cache guard saves 3 DB queries + O(N×M) bisect on cache hit.
- PASS: PERF-003: `domestic_tickers` and `overseas_tickers` correctly classified by `is_domestic()`. `asyncio.gather(*domestic_coros, *overseas_coros)` executes all in parallel.
- PASS: PERF-004: `streamActiveRef` approach is valid — avoids stale closure for `refetchInterval` check.
- PASS: PERF-006: `["dashboard", "summary"]` key matches dashboard/page.tsx — TanStack Query will serve from cache on navigation.

---

## Maintainability Review

**Verdict: APPROVE — 2 findings (minor)**

- PASS: `get_redis_client` is well-documented with type hints and an example in docstring. Exported from `redis_cache.py` cleanly.
- PASS: AlertDialog replaces raw fixed overlay — accessibility and consistency improved.
- MINOR-1: `_get_pool()` creates a pool for a given URL but the singleton is global — if called with two different URLs in tests, the second URL is ignored. This is acceptable for production (one Redis URL) but test isolation with `reset_fallback_cache()` doesn't reset `_pool`. Consider adding `_pool = None` to `reset_fallback_cache()` for test parity. Low urgency — tests use mocking.
- MINOR-2: In portfolios/page.tsx `handleDragEnd`, the snapshot is saved before the optimistic update but the `reorderMutation.mutate()` inline `onError` callback and the `reorderMutation` definition's `onError` both trigger — double toast on error. The mutation-level `onError` should be removed since the call-site `onError` handles it. No user-visible bug (toast appears once since the inline overrides the mutation-level for this call), but the mutation-level `onError` fires on any call without an inline override.

---

## Summary

All 15 tasks implemented correctly. Build passes (ruff, tsc, npm run build). Two minor issues identified:

1. `reset_fallback_cache()` should also reset `_pool = None` for test isolation (non-blocking)
2. `reorderMutation` has redundant `onError` at mutation definition level — the `handleDragEnd` inline `onError` supersedes it, but the mutation-level fires for other callers

Neither issue is a security or correctness risk. Both are easy to fix.

## Decision: APPROVE — proceed to Phase 4 Release
