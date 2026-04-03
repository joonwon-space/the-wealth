# Release Validation Summary — Sprint 5 (2026-04-03)

## Decision: GO

## Build Validation

| Check | Result |
|-------|--------|
| Frontend tsc --noEmit | PASS (0 errors) |
| Frontend npm run build | PASS (clean, 13 routes) |
| Backend ruff check | PASS (0 errors) |
| ESLint | PASS (0 errors, 14 pre-existing warnings) |
| No new DB migrations | PASS (additive API + UI only) |

## Security Assessment

- SEC-002 (session management): New endpoints are additive. Rate-limited. IDOR-safe via Redis key namespace.
- No breaking changes to existing auth flows.
- No new secrets in code.

## API Contract

- New endpoints: `GET /auth/sessions`, `DELETE /auth/sessions/{jti}` — additive only.
- `GET /dashboard/summary` now returns ETag header — backward compatible (clients ignoring ETag still work).
- No removed or modified endpoint signatures.

## Release Notes

### Sprint 5 (2026-04-03) — Security, Performance, Accessibility, Code Split

**Security**
- Active session management: users can now view and revoke individual login sessions from Settings > 보안 tab
- Security audit log now visible in Settings > 보안 tab

**Performance**
- SSE price stream: TCP connection reused for entire SSE session (was recreated every 30s)
- Dashboard summary: ETag + 304 Not Modified support reduces payload on stable data

**Accessibility (WCAG)**
- Icon-only buttons in journal, compare, watchlist now have aria-label
- HoldingsTable column sort buttons: invalid aria-sort + role=button combination fixed
- Recharts donut chart, history chart, transaction chart: role=img + aria-label added

**Code Quality**
- portfolios/[id]/page.tsx split: 1,252 → 746 lines
- settings/page.tsx split: 901 → 253 lines
- 6 new focused components: HoldingsSection, TransactionSection, AccountSection, KisCredentialsSection, SecurityLogsSection, ActiveSessionsSection
- OrderDialog lazy-loaded via next/dynamic (initial bundle -~20KB)
- npm patch updates: recharts 3.8.1, vitest 4.1.2, @tanstack/react-query 5.96.1

## Remaining (Next Sprint)

- TEST-001: OrderDialog.test.tsx — 0% coverage gap still open
- UX-001: 2FA (TOTP) setup UI (Milestone 20-2, deferred)
- TD-003: SSE overseas price support
- PROD-001: index_snapshots + benchmark overlay
