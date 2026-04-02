# Release Validation Summary — sprint-3 (2026-04-03)

## Decision: GO

## Build Validation

| Check | Result |
|-------|--------|
| Frontend tsc --noEmit | PASS (0 errors) |
| Frontend npm run build | PASS (clean, 13 routes) |
| Backend ruff check | PASS (0 errors) |
| DB migrations | None (no schema changes) |
| API contract | No breaking changes |

## Security Assessment

All changes are hardening (additive restrictions, not removals):
- SEC-001: Sentry credential scrubbing — no functional change, adds protection
- SEC-002: Password max_length validation — strictly more restrictive, clients sending >128-char passwords fail (correct behavior)
- SEC-004: CSP unsafe-eval removed from production — reduced attack surface
- SEC-006: Tags field length constraints — additive validation

## Migration Notes

- `cryptography==46.0.6`: Patch upgrade, backward compatible with existing AES-256 encrypted credentials in DB
- `ConnectionPool` singleton: Zero-downtime change — pool is lazily created on first Redis operation. No reconnection needed.
- PERF-001 DISTINCT ON: Raw SQL added via `text()` — PostgreSQL-specific, no issue since the project targets PostgreSQL exclusively

## Rollback Plan

All changes are backward compatible. If rollback needed:
1. `git revert` the branch or checkout previous main
2. No DB migration rollback required (no migrations)
3. Redis cache keys are unchanged — no cache invalidation needed

## Release Notes

**sprint-3 — 2026-04-03**

Security:
- Sentry now strips KIS API credentials (appkey, appsecret, authorization) from error reports
- Passwords capped at 128 characters to prevent bcrypt DoS attacks
- CSP no longer permits unsafe-eval in production builds
- Transaction memo tags are limited to 20 items of 50 characters each
- cryptography upgraded to 46.0.6 (security patch for AES-256 credential encryption)

Performance:
- Dashboard polling suspends when SSE is active (eliminates redundant /dashboard/summary calls)
- Redis now uses a shared ConnectionPool (eliminates 40-300ms TCP overhead per request)
- get_prev_close query reduced from 14,600 rows to 20 rows (DISTINCT ON)
- fx-gain-loss endpoint now cached (3 DB queries + O(N×M) bisect eliminated on cache hit)
- Overseas tickers in analytics/metrics now use the correct KIS API endpoint
- Analytics page no longer makes a duplicate /dashboard/summary request on navigation

UX:
- All portfolio mutations now show error toasts on failure
- Drag-to-reorder rollback on network error
- Analytics table rows are keyboard-navigable (tabIndex, Enter/Space)
- Holding and transaction delete dialogs use shadcn AlertDialog (proper focus trap, ARIA role)
