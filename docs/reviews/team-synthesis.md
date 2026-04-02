# Team Analysis Synthesis -- 2026-04-03 (3rd Sprint)

## Executive Summary

The second sprint's 8 tasks (SEC-001 Sentry credential scrubbing, PERF-001 DISTINCT ON query, SEC-002 bcrypt DoS, TD-005 cryptography upgrade, PERF-002 fx-gain-loss cache, PERF-003 metrics overseas routing, PERF-004 SSE conditional polling, UX-001 mutation onError) remain in tasks.md as the immediate queue -- none have been committed yet. This third analysis sprint (2026-04-03) surfaced 58 raw findings across 5 analysts, collapsing to 45 unique items after deduplication against the existing backlog. The most significant new findings are: (1) **RedisCache opens a new TCP connection per operation** (TD-001/PERF-005) causing 40-300ms overhead on every cached endpoint -- the single largest infrastructure performance issue given 40-60 Redis ops per dashboard summary request; (2) **CSP unsafe-eval enabled in production** (SEC-004) -- a configuration gate that should be dev-only but currently permits arbitrary script execution in production builds; (3) **`portfolios/page.tsx` portfolio rename and reorder mutations have no error handling** (UX-004) with reorderMutation lacking an optimistic update rollback; and (4) **analytics and dashboard pages use different TanStack Query keys for the same `/dashboard/summary` endpoint** (PERF-006) triggering a duplicate network request on every page navigation. Eight new items were added to tasks.md. The backlog grew from 73 to 81 items. Product strategy confirms the milestone priority ordering (Milestone 20 security first, then 21 analytics, then 22 infra) remains correct with analytics completeness now measured at 74%.

---

## Impact x Effort Matrix

### Do First -- tasks.md (added this sprint)

| ID | Title | Source Agents | Impact | Effort |
|----|-------|--------------|--------|--------|
| PERF-005 / TD-001 | Redis ConnectionPool module-level singleton | perf, tech-debt | response-time | M |
| UX-004 | portfolios/page.tsx rename/delete/reorder onError + rollback | ux-gap | user-experience | S |
| SEC-004 | CSP unsafe-eval removed from production builds | security | data-breach prevention | M |
| SEC-006 | TransactionMemoUpdate.tags list/item length constraints | security | denial-of-service prevention | S |
| PERF-006 | Unify analytics/dashboard summary query key constant | perf | response-time | S |
| UX-006 | analytics table row keyboard accessibility (tabIndex + onKeyDown) | ux-gap | accessibility | S |
| UX-007 | Replace inline delete confirm overlays with shadcn AlertDialog | ux-gap | consistency, accessibility | S |

*Previously added to tasks.md (still pending -- carried from sprint 2):*

| ID | Title | Source Agents | Impact | Effort |
|----|-------|--------------|--------|--------|
| SEC-001 | Sentry before_send KIS credential scrubbing | security | data-breach prevention | S |
| PERF-001 | get_prev_close DISTINCT ON query (14,600 rows -> 20) | perf | response-time | S |
| SEC-002 | Password max_length=128 to block bcrypt DoS | security | denial-of-service prevention | S |
| TD-005 | cryptography package patch upgrade | tech-debt | security | S |
| PERF-002 | fx-gain-loss Redis cache guard | perf | response-time | S |
| PERF-003 | analytics/metrics overseas ticker routing fix | perf | api efficiency | S |
| PERF-004 | Dashboard polling disabled when SSE is active | perf | response-time | S |
| UX-001 | 7 portfolio detail mutations get onError toast handlers | ux-gap | user-experience | S |

### Plan Carefully -- todo.md P1 (existing)

| ID | Title | Source Agents | Impact | Effort |
|----|-------|--------------|--------|--------|
| SEC-003 | SSE token moved from query-param to HttpOnly cookie | security, perf | privilege-escalation | M |
| PROD-001 | Server-side refresh token revocation (Milestone 20-1) | product, security | risk-mitigation | M |
| PROD-010 | TOTP 2FA phased (backend first, UI second) (Milestone 20-2) | product, security | risk-mitigation | L |
| PROD-002 | Benchmark overlay (Milestones 21-1, 21-2) | product | user-value | L |
| PROD-003 | Neon + Upstash migration (Milestone 22-1/22-2) | product | risk-mitigation | L |
| PROD-004 | Resend email alerts decoupled from infra sprint | product | user-value | S |

### Nice to Have -- todo.md P2

| ID | Title | Source Agents | Impact | Effort |
|----|-------|--------------|--------|--------|
| UX-002/UX-010 | analytics page per-section error + loading states | ux-gap | user-experience | M |
| UX-003 | OrderDialog/KIS balance hardcoded red/blue -> CSS variables | ux-gap | consistency | S |
| UX-005 | CSV/XLSX download try/catch + loading state | ux-gap | user-experience | S |
| UX-008 | Recharts ARIA role=img + aria-label | ux-gap | accessibility | M |
| UX-009 | WatchlistSection icon buttons aria-label | ux-gap | accessibility | S |
| UX-011 | Add-holding form inline server error feedback | ux-gap | user-experience | S |
| UX-012 | Journal BUY/SELL badge text alongside color | ux-gap | accessibility | S |
| UX-013 | Settings KIS test button loading state | ux-gap | user-experience | S |
| SEC-005 | HoldingCreate.name, BulkHoldingItem.name, AlertCreate.ticker max_length | security | denial-of-service | S |
| SEC-007/PERF-011 | revoke_all_refresh_tokens per-user Redis set (O(N) scan fix) | security, perf | scalability | S |
| TD-002 | kis_order.py place_order function extraction | tech-debt | maintainability | M |
| TD-003/TD-004 | analytics/journal/compare frontend tests + OrderDialog.test.tsx | tech-debt | reliability | L |
| TD-007 | 3 analytics endpoints missing response_model | tech-debt | developer-experience | S |
| TD-008 | alert business logic moved to services layer | tech-debt | maintainability | M |
| TD-011 | forward_fill_rates() extracted to fx_utils.py | tech-debt | maintainability | S |
| TD-013 | PortfolioHistoryChart any[] payload type removed | tech-debt | developer-experience | S |
| PERF-007 | analytics/metrics price_snapshots date cutoff (1Y) | perf | response-time | S |
| PERF-008 | SSE holdings fetched once, not per-tick | perf | scalability | S |
| PERF-009 | SSE httpx client moved outside while loop | perf | response-time | S |
| PERF-010 | SSE overseas ticker price support | perf | user-experience | M |
| PERF-012 | analytics DB queries asyncio.gather parallel | perf | response-time | M |
| PROD-005 | risk metrics minimum_history guard (30-day check) | product | technical-foundation | S |
| PROD-007 | DCA analysis view in journal (existing transaction data) | product | user-value | M |
| PROD-008 | Monthly return heatmap frontend (backend endpoint exists) | product | user-value | S |
| PROD-009 | portfolios/[id]/page.tsx component split (1123 lines) | product, tech-debt | maintainability | M |

### Skipped / Parked

| ID | Title | Reason |
|----|-------|--------|
| TD-012 / lucide-react 1.x | Major version upgrade | Already in todo.md P2, low urgency |
| TypeScript 6.0 upgrade | Major version | No blocking issues, optional |
| PERF-006 query key (SSR prefetch P3) | Server component dashboard SSR | P3 complexity vs gain |
| SEC-008 Backend HSTS | Already in P3 todo.md | Infra-level, low urgency |
| SEC-009 pip-audit CI | Already in P3 todo.md | Dependabot partially covers this |
| TD-006 (import bisect) | Minor style issue | No user impact, S cleanup |

---

## Cross-Cutting Themes

Three patterns appear across multiple analysts:

**1. Redis connection discipline (3 agents: perf, tech-debt, security)**
RedisCache, security.py, dashboard.py, and stock_search.py all call `aioredis.from_url()` per-operation rather than sharing a connection pool. This is the highest-ROI single infrastructure change available: one ConnectionPool refactor eliminates per-request TCP overhead across all cache operations and also fixes the O(N) refresh token revocation scan.

**2. Missing error state in mutations and queries (2 agents: ux-gap, product)**
The portfolios ecosystem (list page, detail page) has good success handlers but systematically missing failure handlers. UX-001 (detail mutations), UX-004 (list mutations), and UX-005 (export) are all the same pattern. Once UX-001 is done the fix is a template application across the remaining cases.

**3. analytics.py as a maintenance bottleneck (3 agents: tech-debt, perf, product)**
At 745 lines with 6 repeated query patterns, no shared service layer, sequential DB queries, mixed response_model coverage, and an inline `import bisect` -- analytics.py is the file most likely to introduce bugs during Milestone 21 development. Extracting `_get_user_portfolio_and_holdings()` and `forward_fill_rates()` before adding benchmark and risk metric handlers will reduce regression risk.

---

## Feature Completeness Snapshot (from product-strategy-analyst)

| Feature Area | Completeness |
|---|---|
| Portfolio management | 96% |
| Market data | 85% |
| Analytics | 74% |
| Trading | 88% |
| Alerts | 80% |
| Data management | 90% |
| User experience | 80% |
| Investment journal | 88% |

Analytics at 74% is the largest remaining gap. The missing 26% is benchmark overlay (21-1/21-2), risk metrics (21-3), and dividend tracking (long-term).

---

## Recommended Next Milestones

**1. Complete sprint-2 tasks.md items (P0/P1)** -- 8 items all S/M effort, all security or performance critical. These must ship before starting Milestone 20.

**2. Milestone 20: Security hardening -- trading account protection** -- Now that live trading is active (POST /orders executes real orders), session security must be tightened. Priority order: 20-1 (refresh token server-side) before 20-2 (TOTP 2FA). Phase TOTP: backend endpoints first, UI enrollment second. 20-3 audit log and 20-4 session management follow.

**3. Milestone 21: Analytics engine completion** -- benchmark overlay + risk metrics + DCA analysis. Prep work (portfolios/[id]/page.tsx extraction, analytics.py service layer) should land before the main analytics features to keep those PRs reviewable.

**4. Milestone 22: Infrastructure stabilization** -- Decouple Resend email (22-3) from Neon/Upstash migration. Ship email alerts first (1-2 days standalone), then migrate database and Redis.

---

## Detailed Findings

### tech-debt-analyst (13 findings)
- **TD-001 HIGH**: `_is_domestic()` duplicate in stocks.py (5 min fix, missed in prior consolidation)
- **TD-002 HIGH**: place_domestic_order/place_overseas_order 128/122 lines each, untestable in isolation
- **TD-003 HIGH**: analytics, journal, compare pages have zero frontend test files
- **TD-004 HIGH**: OrderDialog.tsx 605 lines, zero tests, covers real trade execution
- **TD-005 HIGH**: cryptography package patch lag on AES-256 credential encryption path
- **TD-006 MEDIUM**: Hardcoded Decimal(1450) in portfolios.py diverges from centralized constant
- **TD-007 MEDIUM**: 3 analytics endpoints missing response_model, openapi-typescript generates `unknown`
- **TD-008 MEDIUM**: alert business logic in api layer (check_triggered_alerts, check_and_dedup_alerts)
- **TD-009 MEDIUM**: useOrders.ts (260 lines, financial-critical) and useNotifications.ts have no tests
- **TD-010 MEDIUM**: `import bisect` inside nested function body (PEP 8 violation)
- **TD-011 MEDIUM**: forward_fill_rates algorithm buried in 126-line handler, needed by Milestone 21
- **TD-012 MEDIUM**: lucide-react major version gap 0.577 -> 1.7.0
- **TD-013 LOW**: PortfolioHistoryChart `any[]` payload type, suppressible with typed interface

### ux-gap-analyst (13 findings)
- **UX-001 HIGH**: 7 portfolio detail mutations have onError handlers only for success (already in tasks.md)
- **UX-002 HIGH**: analytics page has no error state for 7 independent queries
- **UX-003 HIGH**: OrderDialog and KIS cash balance use hardcoded red/blue bypassing CSS variables
- **UX-004 MEDIUM**: portfolios/page.tsx rename/delete mutations have no onError; reorderMutation no rollback
- **UX-005 MEDIUM**: CSV/XLSX download silently fails on network error
- **UX-006 MEDIUM**: analytics table rows not keyboard accessible (no tabIndex/onKeyDown)
- **UX-007 MEDIUM**: inline delete confirm overlays lack role/focus-trap vs shadcn AlertDialog
- **UX-008 MEDIUM**: Recharts charts have no ARIA role or labels (screen reader inaccessible)
- **UX-009 MEDIUM**: WatchlistSection icon buttons use title= only (WCAG 4.1.2 gap)
- **UX-010 MEDIUM**: analytics 7 queries cause staggered section pop-in on slower connections
- **UX-011 LOW**: add-holding form no inline error for zero/negative values
- **UX-012 LOW**: journal BUY/SELL badge color-only, no text (WCAG 1.4.1)
- **UX-013 LOW**: settings KIS test button no loading state during 3-10 second call

### security-posture-analyst (9 findings)
- **SEC-001 CRITICAL**: KIS credentials captured in Sentry via httpx exception chain (already in tasks.md)
- **SEC-002 HIGH**: unbounded password enables bcrypt DoS (already in tasks.md)
- **SEC-003 HIGH**: SSE token in URL query param exposed in all server logs
- **SEC-004 MEDIUM**: CSP unsafe-eval and unsafe-inline active in production builds
- **SEC-005 MEDIUM**: HoldingCreate.name, BulkHoldingItem.name, AlertCreate.ticker have no max_length
- **SEC-006 MEDIUM**: TransactionMemoUpdate.tags unbounded (list length, per-item length)
- **SEC-007 MEDIUM**: revoke_all_refresh_tokens_for_user O(N keyspace) Redis SCAN on every logout
- **SEC-008 LOW**: backend SecurityHeadersMiddleware missing HSTS header
- **SEC-009 LOW**: no automated pip dependency vulnerability scanning in CI

### perf-bottleneck-analyst (13 findings)
- **PERF-001 CRITICAL**: get_prev_close loads all historical rows without LIMIT (already in tasks.md)
- **PERF-002 HIGH**: fx-gain-loss endpoint has no cache (already in tasks.md)
- **PERF-003 HIGH**: analytics/metrics calls domestic KIS endpoint for overseas tickers (already in tasks.md)
- **PERF-004 HIGH**: dashboard polling runs concurrently with SSE (already in tasks.md)
- **PERF-005 HIGH**: RedisCache creates new TCP connection per operation
- **PERF-006 MEDIUM**: analytics/dashboard use different query keys for same summary endpoint
- **PERF-007 MEDIUM**: analytics/metrics loads all price_snapshots history without date cutoff
- **PERF-008 MEDIUM**: SSE opens new DB session every 30 seconds per client
- **PERF-009 MEDIUM**: SSE creates and destroys httpx client every 30-second tick
- **PERF-010 MEDIUM**: SSE silently skips overseas holdings (stale prices for non-KRX stocks)
- **PERF-011 MEDIUM**: revoke_all_refresh_tokens O(N) Redis SCAN (same as SEC-007)
- **PERF-012 MEDIUM**: analytics endpoints run 3 sequential DB queries instead of 2 parallel
- **PERF-013 LOW**: SQLAlchemy pool has no recycle interval (intermittent overnight errors)

### product-strategy-analyst (10 findings)
- **PROD-001 CRITICAL**: server-side refresh token revocation not yet started (Milestone 20-1)
- **PROD-002 HIGH**: benchmark overlay is the highest-value remaining analytics feature (Milestone 21)
- **PROD-003 HIGH**: single-server PostgreSQL primary unmitigated production risk (Milestone 22)
- **PROD-004 HIGH**: Resend email alerts should be decoupled from infra migration (S effort standalone)
- **PROD-005 MEDIUM**: risk metrics need minimum_history guard (30-day check before Sharpe/MDD)
- **PROD-006 LOW**: chart skeleton in stocks/[ticker]/page.tsx is last item clearing tasks.md
- **PROD-007 MEDIUM**: DCA analysis achievable from existing transaction data (Milestone 21-4)
- **PROD-008 MEDIUM**: monthly return heatmap frontend missing (backend endpoint already exists)
- **PROD-009 MEDIUM**: portfolios/[id]/page.tsx (1123 lines) and settings/page.tsx (901) need splitting
- **PROD-010 MEDIUM**: TOTP 2FA should be phased (backend first) to ship security improvement sooner
