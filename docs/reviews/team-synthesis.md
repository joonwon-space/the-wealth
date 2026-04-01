# Team Analysis Synthesis — 2026-04-02

## Executive Summary

The KIS personal asset management dashboard is in excellent shape for a solo-maintained project: 74 API endpoints, full trading capability, SSE real-time prices, 93% test coverage, and CI/CD. The 5-analyst review produced 51 raw findings that reduced to 42 unique items after deduplication. The most critical gaps are: (1) **security** — missing rate limits on write endpoints and no server-side refresh token revocation now that real trading is live, (2) **performance** — no GZip compression on any API responses and analytics endpoints run 3-4 sequential DB round-trips, and (3) **code structure** — `_is_domestic()` is copy-pasted across 5 backend modules, and 3 frontend files exceed 800 lines. Strategically, the analytics completeness sits at 72% (Sharpe/MDD, benchmark overlay unimplemented) and 2FA has been underweighted relative to the trading risk level. Three new milestones (20/21/22) and 12 immediate tasks were added.

---

## Impact x Effort Matrix

### Do First — added to tasks.md (12 items)

| ID | Title | Source Agents | Impact | Effort |
|----|-------|--------------|--------|--------|
| PERF-001 / TD-011 | GZip middleware on FastAPI | perf + tech-debt | High | S |
| TD-001 | Extract `_is_domestic()` to `core/ticker.py` | tech-debt | High | S |
| PERF-005 | Fix analytics cache invalidation (fx/krw missing) | perf | High | S |
| TD-009 | Add index to `transactions.ticker` | tech-debt | Med-High | S |
| PERF-004 / TD-013 | Composite index on `price_snapshots(ticker, date)` | perf + tech-debt | High | S |
| TD-010 / UX-003 | Replace `confirm()` with AlertDialog for deletions | tech-debt + UX | Med | S |
| UX-004 | Compare page empty state (< 2 portfolios) | UX | Med | S |
| SEC-001 | Rate limiting on portfolios/holdings/orders endpoints | security | High | S |
| SEC-004 | CORS allow_methods/allow_headers explicit scope | security | Med | S |
| SEC-008 | localStorage JSON.parse() try-catch defense | security | Low | S |
| SEC-009 | Sentry environment config via env variable | security | Low | S |
| UX-005 | ChartSkeleton for stock detail page | UX | Low | S |

### Plan Carefully — added to todo.md P1 (8 items)

| ID | Title | Source Agents | Impact | Effort |
|----|-------|--------------|--------|--------|
| SEC-002 / PROD-001 | Server-side refresh token revocation | security + product | Critical | M |
| PROD-001 | TOTP 2FA for trading account protection | product | Critical | M |
| PROD-002 / TD-004 | Analytics engine: Sharpe/MDD + benchmark | product + perf | High | L |
| PROD-003 | Neon + Upstash migration (single server risk) | product | High | L |
| SEC-003 | Security audit log (trading events) | security | High | L |
| PROD-004 | Email alerts via Resend | product | Med-High | M |
| PERF-006 | SSE delta detection (only send changed prices) | perf | Med | M |
| PROD-005 | DCA analysis view | product | Med | M |

### Nice to Have — added to todo.md P2-P3 (14 items)

| ID | Title | Source Agents | Impact | Effort |
|----|-------|--------------|--------|--------|
| TD-002 | portfolios/[id]/page.tsx split (1123 lines) | tech-debt | Med | M |
| TD-003 | settings/page.tsx split (901 lines) | tech-debt | Med | M |
| TD-005 | kis_order.py split (780 lines) | tech-debt | Med | M |
| TD-006 | lucide-react v1.x migration | tech-debt | Low | M |
| TD-004 | analytics.py holdings query helper | tech-debt | Med | M |
| PERF-008 | OrderDialog lazy loading | perf | Med | M |
| PERF-003 | Dashboard SSR initial data prefetch | perf | Med | L |
| PERF-007 | Disable dashboard polling when SSE active | perf | Med | M |
| UX-001 | Analytics unified loading state | UX | Med | M |
| UX-002 | Chart ARIA labels (screen reader support) | UX | Med | M |
| UX-007 | Market hours warning in OrderDialog | UX | Med | S |
| UX-008 | Transaction delete optimistic update | UX | Low | S |
| UX-011 | Keyboard focus trap in dialogs | UX | Med | M |
| PROD-006 | Portfolio compare date range picker | product | Med | M |

### Skipped / Parked (8 items)

| ID | Title | Reason |
|----|-------|--------|
| TD-007 | Python minor package updates (cryptography etc.) | Already tracked in CI dependency updates |
| TD-008 | PortfolioHistoryChart `any[]` type fix | Low risk, test-adjacent code |
| UX-006 | WatchlistSection empty state | Low impact, watchlist is secondary feature |
| UX-009 | Journal recall widget null price | Corner case, low user impact |
| UX-010 | KIS test button loading state | Minor polish |
| UX-012 | Holdings table mobile scroll indicator | CSS-only, low risk |
| PERF-009 | Scheduler ticker deduplication | Premature optimization for current scale |
| PERF-010 | ETag on dashboard endpoint | Already P3 in todo.md |
| SEC-007 | Concurrent session limit | Partially addressed by SEC-002 (refresh token store) |

---

## Cross-Cutting Themes

Three themes appeared consistently across multiple analysts:

**1. Security escalation due to trading feature**
- SEC-001 (rate limits), SEC-002 (refresh token revocation), SEC-003 (audit log), PROD-001 (2FA) all relate to the same root cause: the trading feature changed the risk profile from "data privacy" to "direct financial harm". This is the highest-priority cross-cutting concern.

**2. Backend code consolidation**
- TD-001 (_is_domestic duplication), TD-004 (analytics query pattern), TD-005 (kis_order size), PERF-002 (analytics DB round-trips) all point to the same pattern: the backend grew feature-first without periodic refactoring. A "code consolidation sprint" would address all four simultaneously.

**3. Performance through infrastructure, not optimization**
- PERF-001 (GZip), PERF-003 (SSR), PERF-004/TD-013 (DB indexes), PROD-003 (Neon/Upstash) all require infrastructure changes rather than algorithmic optimization. These are high-leverage, low-complexity wins.

---

## Feature Completeness Snapshot

From product-strategy-analyst:

| Feature Area | Completeness | Key Gap |
|---|---|---|
| Portfolio Management | 95% | Minor UX polish |
| Market Data | 85% | Moving avg overlays, volume charts |
| Analytics | 72% | Benchmark overlay, Sharpe/MDD unimplemented |
| Trading | 88% | Market hours indicator, overseas order UX |
| Alerts | 78% | Email delivery channel missing |
| Data Management | 88% | PDF reports (parked) |
| User Experience | 78% | A11y gaps, some empty states missing |
| Investment Journal | 85% | Retrospective widget could be richer |

---

## Recommended Next Milestones

1. **Milestone 20: 보안 강화 — 트레이딩 계정 보호** — Rationale: trading is live; account compromise = financial harm. Server-side refresh token revocation (SEC-002) and TOTP 2FA (PROD-001) are the two items that reduce the most critical risk. The security audit log completes the picture for a financial-grade app.

2. **Milestone 21: 분석 엔진 완성 — 벤치마크 + DCA + 리스크 지표** — Rationale: analytics at 72% is the largest visible gap from a user perspective. The benchmark overlay is the single most-asked question in portfolio apps ("did I beat the market?"). Building on the index data collection and metrics.py already partially present, this is achievable in 2-3 sprints.

3. **Milestone 22: 인프라 안정화 — Neon + Upstash + 이메일 알림** — Rationale: single-server PostgreSQL is a production risk for a trading app. Neon+Upstash gives HA with minimal ops burden. Bundling email alerts here converts the already-complete alert system into a genuinely useful out-of-app notification mechanism.

---

## Detailed Findings

### Tech Debt (13 findings)

| ID | Severity | Category | Location | Effort |
|----|----------|----------|----------|--------|
| TD-001 | High | code-smell | analytics/dashboard/portfolios/orders/chart.py | S |
| TD-002 | High | code-smell | portfolios/[id]/page.tsx (1123 lines) | M |
| TD-003 | High | code-smell | settings/page.tsx (901 lines) | M |
| TD-004 | Med | code-smell | analytics.py (748 lines, 7x repeated pattern) | M |
| TD-005 | Med | code-smell | kis_order.py (780 lines) | M |
| TD-006 | Med | dependency | lucide-react 0.577 vs 1.7, typescript 5.9 vs 6.0 | M |
| TD-007 | Med | dependency | cryptography, gunicorn, boto3 minor updates | S |
| TD-008 | Low | type-safety | PortfolioHistoryChart.tsx:45,156 (any[]) | S |
| TD-009 | Med | architecture | transactions.ticker missing index | S |
| TD-010 | Low | code-smell | portfolios/page.tsx:231 uses confirm() | S |
| TD-011 | Med | architecture | FastAPI GZipMiddleware not configured | S |
| TD-012 | Med | code-smell | OrderDialog.tsx (605 lines) | M |
| TD-013 | Med | architecture | price_snapshots composite index missing | S |

### UX Gaps (12 findings)

| ID | Severity | Category | Location | Effort |
|----|----------|----------|----------|--------|
| UX-001 | High | loading-state | analytics/page.tsx (7 independent queries) | M |
| UX-002 | High | a11y | AllocationDonut, PortfolioHistoryChart, MonthlyHeatmap | M |
| UX-003 | High | feedback | portfolios/[id]/page.tsx holding delete | S |
| UX-004 | High | empty-state | compare/page.tsx (<2 portfolios) | S |
| UX-005 | Med | loading-state | stocks/[ticker]/page.tsx chart blank | S |
| UX-006 | Med | empty-state | WatchlistSection.tsx (no items) | S |
| UX-007 | Med | feedback | OrderDialog overseas market hours | S |
| UX-008 | Med | feedback | Transaction delete optimistic update | S |
| UX-009 | Med | error-handling | Journal recall null current price | S |
| UX-010 | Low | loading-state | Settings KIS test button no spinner | S |
| UX-011 | Med | a11y | OrderDialog/StockSearchDialog focus trap | M |
| UX-012 | Low | responsive | HoldingsTable horizontal scroll indicator | S |

### Security (9 findings)

| ID | Severity | Category | Location | Effort |
|----|----------|----------|----------|--------|
| SEC-001 | High | api-security | portfolios.py, orders.py (no rate limits) | S |
| SEC-002 | High | auth | auth.py (no server-side token revocation) | M |
| SEC-003 | High | data-protection | orders.py, portfolios.py, users.py | L |
| SEC-004 | Med | api-security | main.py (wildcard CORS methods/headers) | S |
| SEC-005 | Med | data-protection | kis_token.py, kis_order.py (log masking) | S |
| SEC-006 | Med | input-validation | portfolio schemas (memo/tags length) | S |
| SEC-007 | Med | auth | Unlimited concurrent sessions | M |
| SEC-008 | Low | frontend-security | StockSearchDialog.tsx localStorage | S |
| SEC-009 | Low | data-protection | main.py Sentry environment hardcoded | S |

### Performance (10 findings)

| ID | Severity | Category | Location | Effort |
|----|----------|----------|----------|--------|
| PERF-001 | High | network | main.py (no GZip middleware) | S |
| PERF-002 | High | database | analytics.py (3-4 sequential DB trips) | M |
| PERF-003 | High | rendering | dashboard/page.tsx (fully client-side) | L |
| PERF-004 | High | database | price_snapshots composite index | S |
| PERF-005 | Med | caching | analytics.py invalidate_analytics_cache() | S |
| PERF-006 | Med | network | prices.py SSE (unconditional 30s push) | M |
| PERF-007 | Med | network | dashboard/page.tsx (polling + SSE parallel) | M |
| PERF-008 | Med | bundle | OrderDialog.tsx not lazy-loaded | M |
| PERF-009 | Med | api | scheduler.py ticker deduplication | M |
| PERF-010 | Low | caching | dashboard.py (no ETag support) | M |

### Product Strategy (7 findings + 3 proposed milestones)

| ID | Severity | Category | Impact |
|----|----------|----------|--------|
| PROD-001 | High | priority-misalignment | 2FA urgency elevated (trading live) |
| PROD-002 | High | missing-capability | Benchmark overlay (highest UX value) |
| PROD-003 | High | technical-enabler | Neon+Upstash (reliability) |
| PROD-004 | Med | deferred-value | Email alerts (alert infra complete) |
| PROD-005 | Med | missing-capability | DCA analysis (Korean investor pattern) |
| PROD-006 | Med | deferred-value | Portfolio compare completion |
| PROD-007 | Low | technical-enabler | Storybook component catalog |
