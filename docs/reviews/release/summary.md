# Release Validation Summary -- Sprint 4 (2026-04-03)

## Decision: GO

## Build Validation

| Check | Result |
|-------|--------|
| Frontend tsc --noEmit | PASS (0 errors) |
| Frontend npm run build | PASS (clean, 13 routes) |
| Backend ruff check | PASS (0 errors) |
| Python syntax (new files) | PASS |
| DB migration (k3l4m5n6o7p8) | Reversible, additive only |

## Security Assessment

- SEC-001 (refresh token key format): Breaking change for existing sessions -- intentional. All users re-authenticate on next token refresh. New format enables O(1) per-user revocation.
- SEC-003 (audit log): Additive new table and service. Non-blocking (errors swallowed). No new attack surface.
- SEC-007 (pip-audit): CI-only addition. No runtime impact.

## Migration Notes

1. Run `alembic upgrade head` BEFORE restarting backend.
2. Existing refresh tokens with prefix `refresh_jti:` will be ignored -- all active sessions invalidated. Expected behavior.
3. No Redis cache invalidation required.
4. No frontend env changes.

## Rollback Plan

1. `alembic downgrade -1` -- drops security_audit_logs table and auditaction enum.
2. Revert security.py to restore old refresh token key format (existing sessions already invalidated, cannot un-invalidate).
3. No data loss risk (audit logs are append-only; holding/analytics data unchanged).

## Release Notes

**Sprint 4 -- 2026-04-03**

Security:
- Refresh token Redis key changed to refresh:{user_id}:{jti} -- logout now O(1) per-user scan instead of O(N) global scan
- Security audit log table + service: login, logout, KIS credential add/delete, password change events recorded
- GET /users/me/security-logs endpoint (last 50 entries)
- pip-audit added to backend CI pipeline for CVE auto-detection

Reliability:
- SQLAlchemy pool_recycle=1800 -- prevents idle connection errors (required before Neon migration)

Performance / Code Quality:
- analytics.py price_snapshots limited to 1Y by default (metrics endpoint)
- forward_fill_rates extracted to fx_utils.py (reusable across analytics + scheduler)
- stocks.py removes duplicate _is_domestic() in favor of shared core.ticker.is_domestic

UX:
- Analytics page: all 6 queries now show per-section skeletons and retry buttons on error
- Portfolio detail: add holding form shows inline validation errors (qty > 0, price >= 0)
- Portfolio detail: CSV/XLSX export buttons show spinner and disable during download, toast on error
- Investment journal: BUY/SELL badges now include TrendingUp/TrendingDown icons (WCAG 1.4.1)

Type Safety:
- PortfolioHistoryChart: removed any[] cast, typed ChartPayloadItem interface
