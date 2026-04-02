# Team Analysis Synthesis -- 2026-04-02 (2nd Sprint)

## Executive Summary

The first sprint's 12 tasks are fully complete: GZip compression, `_is_domestic()` consolidation, cache invalidation fixes, DB indexes, AlertDialog replacements, rate limiting, CORS hardening, and UX polish. The second analysis run surfaced 58 raw findings across 5 analysts, reducing to 45 unique items after deduplication. The most critical new finding is **SEC-001: KIS API credentials (appkey, appsecret) leak verbatim into Sentry error events** when httpx raises exceptions -- a direct brokerage credential exposure risk. The second critical gap is **PERF-001: get_prev_close loads all historical price_snapshots without LIMIT**, transferring ~14,600 rows per dashboard request. Eight items were promoted to tasks.md for immediate execution. The P1/P2/P3 backlog grew from 46 to 65 items as the analysis uncovered SSE inefficiencies (new DB session + httpx client every 30 seconds per connected client), missing error handlers across 7 portfolio mutations, and input validation gaps enabling bcrypt DoS via unbounded password length.

---

## Impact x Effort Matrix

### Do First (tasks.md) -- 8 items

| ID | Title | Source Agents | Impact | Effort |
|----|-------|--------------|--------|--------|
| SEC-001 | Sentry KIS credential leakage -- before_send scrubber | security | Critical | S |
| PERF-001 | get_prev_close unbounded query -- DISTINCT ON | perf | Critical | S |
| SEC-002 | Password max_length=128 for bcrypt DoS prevention | security | High | S |
| TD-005 | cryptography package security update (46.0.5 -> latest) | tech-debt | High | S |
| PERF-002 | fx-gain-loss endpoint missing Redis cache | perf | High | S |
| PERF-003 | metrics calls domestic KIS API for overseas tickers | perf | High | S |
| PERF-004 | Dashboard polling runs concurrently with SSE | perf | High | S |
| UX-001 | Portfolio detail 7 mutations lack onError handlers | ux-gap | High | S |

### Plan Carefully (todo.md P1) -- 2 new items

| ID | Title | Source Agents | Impact | Effort |
|----|-------|--------------|--------|--------|
| SEC-003 | SSE access token in URL query string -- migrate to HttpOnly cookie | security | High | M |
| PERF-005 | RedisCache creates new TCP connection per operation | perf | High | M |

### Nice to Have (todo.md P2) -- 12 new items

| ID | Title | Source Agents | Impact | Effort |
|----|-------|--------------|--------|--------|
| TD-004 | OrderDialog.tsx 605 lines with zero tests | tech-debt | High | M |
| TD-003 | analytics/journal/compare pages have no tests | tech-debt | High | L |
| UX-003 | OrderDialog/KIS cash balance hardcoded red/blue | ux-gap | High | S |
| UX-002+010 | Analytics page error states + per-section loading | ux-gap | High | M |
| SEC-005+006 | Missing max_length on name/ticker/tags fields | security | Medium | S |
| UX-005 | CSV/XLSX download silent failure | ux-gap | Medium | S |
| PERF-008 | SSE DB session opened every 30 seconds | perf | Medium | S |
| PERF-009 | SSE httpx client created every 30 seconds | perf | Medium | S |
| PERF-010 | SSE skips overseas holdings (frozen prices) | perf | Medium | M |
| PERF-012 | Analytics sequential DB queries -- asyncio.gather | perf | Medium | M |
| TD-007 | 3 analytics endpoints missing response_model | tech-debt | Medium | S |
| TD-008 | Alert business logic in api layer instead of services | tech-debt | Medium | M |

### Nice to Have (todo.md P3) -- 5 new items

| ID | Title | Source Agents | Impact | Effort |
|----|-------|--------------|--------|--------|
| PERF-013 | SQLAlchemy pool_recycle not configured | perf | Low | S |
| UX-008 | Recharts charts lack ARIA labels | ux-gap | Medium | M |
| UX-009 | WatchlistSection icon buttons lack aria-label | ux-gap | Medium | S |
| SEC-009 | No pip-audit in CI for Python dependencies | security | Low | S |
| SEC-008 | Backend SecurityHeadersMiddleware missing HSTS | security | Low | S |

### Skipped/Parked -- 6 items

| ID | Title | Reason |
|----|-------|--------|
| TD-010 | Inline import bisect in analytics.py | Trivial code smell, negligible impact |
| TD-011 | forward_fill_rates extraction from analytics.py | Useful for M21 but premature extraction now |
| TD-013 | PortfolioHistoryChart any[] Recharts payload | Low impact type cosmetic fix |
| UX-011 | Add-holding form inline error feedback | Low priority -- already has submit disable |
| UX-012 | Journal BUY/SELL badge color-only distinction | Arrow icons already provide non-color info |
| UX-013 | Settings KIS test button loading state | Low frequency interaction |
| TD-006 | Hardcoded Decimal(1450) in portfolios.py | Existing P2 tracking sufficient |
| SEC-004 | CSP nonce-based for production | High effort, Next.js nonce integration complex |

---

## Cross-Cutting Themes

### 1. SSE Stream Inefficiency (PERF-008, PERF-009, PERF-010, PERF-004)

Four findings converge on the SSE price stream: it opens a new DB session every 30 seconds, creates a new httpx TLS client every 30 seconds, silently drops overseas tickers, and the dashboard polls in parallel making SSE partially redundant. Collectively these represent the single largest backend performance improvement opportunity. Fixing all four would reduce per-user backend load by approximately 60%.

### 2. Missing Error Handlers Across Mutations (UX-001, UX-004, UX-005)

Three analysts independently flagged silent failure on mutations. Portfolio detail has 7 handlers without onError, the portfolios page has 2 more, and CSV/XLSX downloads swallow network errors. The pattern is consistent: onSuccess toast exists but onError is omitted. A single sweep applying the settings/page.tsx pattern would resolve all.

### 3. Redis Operations Architecture (PERF-005, SEC-007/PERF-011)

Redis is used for caching, KIS token storage, SSE session tracking, and refresh token management. Two structural problems: (a) every operation opens a new TCP connection (40-300ms overhead per request), and (b) logout scans the entire keyspace. Both require the same fix direction -- connection pooling and per-user key sets.

### 4. Input Validation Gaps (SEC-002, SEC-005, SEC-006)

Multiple Pydantic schemas accept unbounded input. Password fields have no max_length (enabling bcrypt DoS), holding names and tags have no length limits. These are all S-effort fixes with Field constraints.

### 5. Credential Exposure Risk (SEC-001, SEC-003)

KIS API credentials appear in two unexpected places: Sentry error events (via httpx exception headers) and server access logs (via SSE query parameter JWT). Both are high-severity leaks that could enable unauthorized trading.

---

## Feature Completeness Snapshot

From product-strategy-analyst:

| Area | Completeness | Key Gap |
|------|-------------|---------|
| Portfolio Management | 96% | -- |
| Data Management | 90% | -- |
| Trading | 88% | Order history view |
| Investment Journal | 88% | DCA analysis |
| Market Data | 85% | Benchmark index data |
| Alerts | 80% | Email delivery channel |
| User Experience | 80% | Error handling consistency |
| Analytics | 74% | Benchmark overlay, risk metrics |

**Overall: ~85% feature-complete** for a personal asset management dashboard with trading capability.

---

## Recommended Next Milestones

### 1. Immediate Sprint: Security + Performance Quick Wins (tasks.md, 1-2 days)

Complete the 8 tasks.md items. All are S-effort and address critical/high severity findings. This sprint eliminates the Sentry credential leak, fixes the dashboard's worst query, and prevents bcrypt DoS.

### 2. Milestone 20: Security Hardening (P1, 2-3 weeks)

Order: 20-1 (server-side refresh tokens) first, then 20-2 Phase 1 (TOTP backend), then 20-3 (audit log), then 20-2 Phase 2 (2FA settings UI), then 20-4 (session management). Security before features because trading is live.

### 3. Milestone 21: Analytics Engine Completion (P1, 2-3 weeks)

Order: Prep (portfolio page split) -> 21-1 (index data collection) -> 21-2 (benchmark overlay) -> 21-3 (risk metrics with minimum history guard) -> 21-4 (DCA analysis) -> monthly return heatmap bonus. This raises analytics from 74% to ~95%.

### 4. Milestone 22: Infrastructure + Email (P2, 1-2 weeks)

Decouple Resend email from infra migration. Ship email alerts first (1-2 days standalone). Then Neon PostgreSQL migration, then Upstash Redis migration. This ordering delivers user value (email alerts) before the riskier infrastructure changes.

---

## Detailed Findings

### Merged Findings (SEC-007 + PERF-011)

**Redis SCAN on logout** -- Both security-posture-analyst and perf-bottleneck-analyst independently identified that `revoke_all_refresh_tokens_for_user` scans the entire `refresh_jti:*` keyspace. Security framed it as a DoS vector; performance framed it as O(N) scalability concern. Resolution: per-user Redis set `user_jtis:{user_id}` for O(1) user-scoped revocation.

### Already Tracked in todo.md (not duplicated)

- TD-012 (lucide-react v1.x) -> P2 #24
- PROD-001 (server-side refresh token) -> Milestone 20-1
- PROD-002 (benchmark overlay) -> Milestone 21-1/21-2
- PROD-003 (Neon/Upstash) -> Milestone 22-1/22-2
- PROD-009 (page splits) -> P2 #19-20

### Findings from Previous Sprint (completed)

All 12 items from the 2026-04-02 first sprint are resolved:
- PERF-001 (old): GZip middleware
- TD-001 (old): _is_domestic() consolidation (5/6 files -- stocks.py now flagged as TD-001 new)
- PERF-005 (old): analytics cache invalidation
- TD-009/PERF-004 (old): DB indexes
- TD-010/UX-003 (old): AlertDialog replacements
- UX-004 (old): Compare page empty state
- SEC-001 (old): Rate limiting
- SEC-004 (old): CORS methods/headers scoping
- SEC-008 (old): localStorage defense
- SEC-009 (old): Sentry environment variable
- UX-005 (old): Chart skeleton

### Full Finding Index

**Tech-Debt (13):** TD-001 through TD-013
**UX-Gap (13):** UX-001 through UX-013
**Security (9):** SEC-001 through SEC-009
**Performance (13):** PERF-001 through PERF-013
**Product-Strategy (10):** PROD-001 through PROD-010

Total: 58 raw -> 45 unique after deduplication and overlap with existing backlog.
