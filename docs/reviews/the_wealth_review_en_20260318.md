# The Wealth — Project Review & Improvement Roadmap

> Date: 2026-03-18
> Target: The Wealth (Personal Portfolio Dashboard)
> Purpose: Architecture review + actionable improvement plan

---

## 1. Current State Assessment

### 1.1 Well-Designed Areas

**Architecture**
- Not storing current prices in DB and computing P&L in real-time from KIS API eliminates data consistency issues. The single source of truth for prices is always the KIS API, preventing stale price display.
- `asyncio.gather()` parallel calls + Redis cache fallback is a textbook resilience pattern for external API-dependent services.
- Preemptive token replacement with a 600-second buffer before expiration handles edge cases well.

**Security**
- AES-256-GCM encryption with fresh nonce per encryption for KIS credentials is correctly implemented.
- JWT refresh token rotation with one-time JTI consumption addresses token theft scenarios.
- Consistent `user_id` ownership verification across all resource endpoints prevents IDOR attacks.

**Infrastructure**
- Docker multi-stage builds minimize image sizes; healthcheck-based service dependency chains ensure stable deployments.
- Path-based CI triggers (`paths: ['backend/**']`) skip unnecessary builds.
- CodeQL + Dependabot automation handles security and dependency management at the CI level.

**Cost Management**
- Redis memory usage at ~510KB is extremely efficient for a personal service.
- SSE deactivation during off-market hours eliminates unnecessary API calls.

### 1.2 Areas Requiring Attention

The items below are not causing immediate issues but could become bottlenecks or failure points as the service grows or runs longer.

---

## 2. Architecture Improvements

### 2.1 Single Server Dependency

**Current**: All services (Frontend, Backend, PostgreSQL, Redis) run on one self-hosted server via Docker Compose.

**Problem**: Server failure takes down the entire service. Disk failure causes total data loss.

**Improvements**:

```
[Priority 1] Automated DB Backups
- Add daily pg_dump backup script
- Store backups in external storage (S3, GCS, etc.)
- Document and periodically test restore procedures

[Priority 2] External Monitoring
- Introduce external healthcheck monitoring (UptimeRobot, Betterstack, etc.)
- Receive alerts on server downtime (email, Slack, Telegram)

[Priority 3] Long-term Cloud Migration
- Separate PostgreSQL to managed DB (Supabase, Neon, RDS)
- Consider serverless Redis (Upstash)
- Backend/Frontend can remain self-hosted
```

### 2.2 Single uvicorn Worker

**Current**: Running `uvicorn app.main:app --host 0.0.0.0 --port 8000` with a single worker.

**Problem**: CPU-bound tasks (encryption/decryption, bulk P&L calculations) can block other requests on the single event loop.

**Improvements**:
```
Option A: Increase uvicorn workers
  uvicorn app.main:app --workers 2 --host 0.0.0.0 --port 8000
  → Watch for APScheduler conflicts (ensure scheduler runs in main
    process only, or separate it into its own process)

Option B: gunicorn + uvicorn worker class
  gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 2
  → More stable process management

Caveat:
  - APScheduler may run duplicate jobs in multi-worker setups
  - Solution: Separate scheduler into its own container/process,
    or use Redis-based distributed lock (redlock)
```

### 2.3 SSE Connection Management

**Current**: SSE streams price updates every 30 seconds.

**Potential Issue**: SSE connections hold server resources (file descriptors, memory) for extended periods. Multiple browser tabs or abnormal client terminations can accumulate zombie connections.

**Improvements**:
```
1. Connection Limits
   - Max SSE connections per user (e.g., 3)
   - Close oldest connection on new connect

2. Heartbeat + Timeout
   - Server → client heartbeat events (15s interval)
   - Disconnect if no client response
   - Server-side max connection duration (e.g., 2 hours)

3. Long-term WebSocket Migration
   - WebSocket is more efficient for bidirectional communication
   - Current unidirectional (server→client) suits SSE,
     but reconsider when real-time alerts are added
```

---

## 3. Security Hardening

### 3.1 Frontend Token Storage

**Current**: Access token is dual-written to `localStorage + cookie`.

**Problem**: Tokens in localStorage are vulnerable to XSS attacks. Malicious scripts can extract tokens via `localStorage.getItem()`.

**Improvements**:
```
Recommended: HttpOnly Cookie-based Authentication

1. Server sets tokens via HttpOnly + Secure + SameSite=Lax cookies on login
   → Inaccessible to JavaScript (XSS defense)

2. Axios requests use withCredentials: true
   → Browser automatically includes cookies

3. CSRF Defense
   → SameSite=Lax provides baseline defense + add CSRF token if needed

4. Next.js middleware continues checking cookies for auth state

Migration Steps:
  Phase 1: Server issues tokens via Set-Cookie
  Phase 2: Remove localStorage dependency from frontend
  Phase 3: Zustand store manages only auth state (boolean)
```

### 3.2 Granular Rate Limiting

**Current**: Global 60 requests/min (per IP) single policy.

**Problem**: Auth endpoints need stricter limits against brute force. Dashboard polling at 30s intervals is normal traffic and shouldn't be throttled.

**Improvements**:
```
Per-endpoint rate limits:

| Endpoint Group            | Limit        | Reason                        |
|---------------------------|--------------|-------------------------------|
| POST /auth/login          | 5/min        | Brute force defense           |
| POST /auth/register       | 3/min        | Mass account creation defense |
| POST /auth/refresh        | 10/min       | Auto-refresh tolerance        |
| GET /dashboard/*          | 120/min      | 30s polling + SSE traffic     |
| POST /sync/*              | 5/min        | Protect KIS API quota         |
| Others                    | 60/min       | Keep current                  |
```

### 3.3 Input Validation Hardening

**Current**: Basic validation via Pydantic schemas.

**Additional Checks Needed**:
```
1. Ticker field regex validation
   - Domestic: r"^[0-9]{6}$" (6-digit number)
   - International: r"^[A-Z]{1,5}$" (1-5 uppercase letters)
   - String-only acceptance may allow injection

2. Quantity/Price range validation
   - Enforce quantity > 0, price > 0
   - Prevent Numeric overflow (validate against Numeric(18,6) max)

3. Pagination parameter validation
   - Max limit cap (e.g., max 100)
   - Prevent negative offset

4. sync_logs message field
   - Verify error messages don't contain sensitive data
   - Raw KIS API responses may expose tokens if stored as-is
```

### 3.4 Add CSP Header

**Current**: 5 security headers applied, but CSP is missing.

**Improvements**:
```
Content-Security-Policy:
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data:;
  connect-src 'self' https://api.joonwon.dev;
  font-src 'self';
  frame-ancestors 'none';

→ Blocks external script loading during XSS attacks
→ 'unsafe-inline' may be needed for Next.js inline styles
→ Can gradually transition to nonce-based CSP
```

---

## 4. Database Improvements

### 4.1 Index Strategy

**Current**: Only PK, FK, and UNIQUE constraints exist. No explicit query performance indexes documented.

**Improvements**:
```sql
-- 1. User's portfolios (used in nearly every API)
CREATE INDEX idx_portfolios_user_id ON portfolios(user_id);

-- 2. Portfolio holdings (core dashboard query)
CREATE INDEX idx_holdings_portfolio_id ON holdings(portfolio_id);

-- 3. Portfolio transactions + date ordering
CREATE INDEX idx_transactions_portfolio_traded
  ON transactions(portfolio_id, traded_at DESC);

-- 4. Price snapshots (history charts, monthly returns)
CREATE INDEX idx_price_snapshots_ticker_date
  ON price_snapshots(ticker, snapshot_date DESC);

-- 5. Recent sync logs
CREATE INDEX idx_sync_logs_user_synced
  ON sync_logs(user_id, synced_at DESC);

-- 6. User watchlist
CREATE INDEX idx_watchlist_user_id ON watchlist(user_id);

-- 7. Active alerts per user
CREATE INDEX idx_alerts_user_active ON alerts(user_id, is_active)
  WHERE is_active = true;

Note: PostgreSQL does NOT auto-index FK columns
     (unlike MySQL — explicit creation required)
```

### 4.2 Legacy Column Cleanup in users Table

**Current**: `users` table retains legacy columns (`kis_app_key_enc`, `kis_app_secret_enc`, `kis_account_no`, `kis_acnt_prdt_cd`) alongside the separate `kis_accounts` table.

**Improvements**:
```
1. Verify if any code still references legacy columns
2. Migrate all references to kis_accounts table
3. Remove legacy columns via Alembic migration
   - Staged approach for live service:
     Phase 1: Stop reading legacy columns (code removal)
     Phase 2: DROP columns after sufficient observation period
```

### 4.3 Soft Delete Consideration

**Current**: CASCADE deletes physically remove all related data immediately.

**Recommendation**:
```
Transaction history is core investment data —
consider soft delete instead of physical deletion:

- Add deleted_at column (nullable DateTime)
- On delete request: SET deleted_at = now()
- On query: WHERE deleted_at IS NULL filter
- Optionally batch-purge after retention period

Priority:
  1st: transactions (preserve investment history)
  2nd: holdings (recover accidentally deleted stocks)
  3rd: portfolios (preserve child data)
```

### 4.4 price_snapshots Growth Planning

**Current**: Stores OHLCV once daily. No issue at current scale, but data grows linearly (stocks × days).

**Projection**:
```
50 stocks × 365 days = 18,250 rows/year
50 stocks × 365 days × 5 years = 91,250 rows

→ Partitioning unnecessary at current scale
→ Maintain design compatible with future snapshot_date
   range partitioning if user base grows
```

---

## 5. API Design Improvements

### 5.1 API Versioning

**Current**: No versioning — endpoints exposed directly as `/auth/login`, `/portfolios`.

**Improvements**:
```
Current:  /auth/login
Proposed: /api/v1/auth/login

Benefits:
- Deploy new API versions without breaking backward compatibility
- Support independent frontend/backend releases
- Allow per-client migration periods

Implementation:
  Add prefix="/api/v1" to FastAPI APIRouter
  Update frontend Axios baseURL
```

### 5.2 Standardized Error Responses

**Current**: HTTPException returns errors, but response format may vary across endpoints.

**Improvements**:
```json
// Standard error response
{
  "error": {
    "code": "PORTFOLIO_NOT_FOUND",
    "message": "Portfolio not found.",
    "details": null
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}

// Validation error (422)
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input.",
    "details": [
      { "field": "quantity", "message": "Must be greater than 0." }
    ]
  },
  "request_id": "..."
}
```

```
Implementation:
1. Register custom exception handlers
2. Define business error code enums (PORTFOLIO_NOT_FOUND, KIS_API_ERROR, etc.)
3. Auto-include request_id in error responses
4. Frontend maps error.code to user-facing messages
```

### 5.3 Pagination Consistency

**Current**: Pagination approach for transaction lists, sync logs, etc. is not specified.

**Improvements**:
```json
// Cursor-based pagination (recommended)
GET /portfolios/{id}/transactions?cursor=eyJpZCI6MTAwfQ&limit=20

{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTIwfQ",
    "has_more": true
  }
}

Benefits:
- Better performance than offset-based for large datasets
- No duplicate/missing records on data changes
- Natural fit for time-ordered data like transactions
```

### 5.4 Bulk Operation API

**Current**: Holdings create/update/delete only supports individual operations.

**Improvements**:
```
POST /portfolios/{id}/holdings/bulk
{
  "actions": [
    { "action": "create", "ticker": "005930", "name": "Samsung", "quantity": 100, "avg_price": 60000 },
    { "action": "update", "id": 5, "quantity": 150 },
    { "action": "delete", "id": 3 }
  ]
}

Benefits:
- Apply KIS sync results in a single API call
- Reduce network calls for multi-stock edits on frontend
- Guarantee transactional consistency
```

---

## 6. Frontend Improvements

### 6.1 Error Boundaries & User Feedback

**Improvements**:
```
1. React Error Boundary
   - Page-level error boundaries prevent white screens
   - Fallback UI with "Retry" button

2. API Error Toast System
   - KIS API failure: "Price fetch failed. Showing cached prices."
   - Network error: "Server connection unstable."
   - Auth expired: Redirect to login if auto-refresh fails

3. Consistent loading/error/empty states
   - Skeleton UI (loading)
   - Error state component
   - Empty state component ("No holdings yet")
```

### 6.2 Data Fetching Layer

**Current**: Axios + manual state management.

**Improvements**:
```
Consider TanStack Query (React Query)

Benefits:
- Auto caching + background refetch (replace 30s polling with refetchInterval)
- Built-in stale-while-revalidate pattern
- Automatic loading/error/success state management
- SSE integration via queryClient.setQueryData() for real-time prices
- Optimistic updates (instant UI on stock add/delete)

Example:
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', portfolioId],
    queryFn: () => fetchDashboardSummary(portfolioId),
    refetchInterval: 30_000,
    staleTime: 10_000,
  });
```

### 6.3 Bundle Size Optimization

**Improvements**:
```
1. Dynamic imports for chart libraries
   - lightweight-charts: load only on candlestick chart page
   - Recharts: load only on dashboard/analytics pages
   → Use next/dynamic or React.lazy()

2. Analyze with @next/bundle-analyzer
   → Discover unexpectedly large dependencies

3. Image optimization
   - Use next/image component (auto resize, WebP conversion)
   - Inline SVG for chart icons
```

### 6.4 Accessibility (a11y)

**Improvements**:
```
1. Add non-color indicators for P&L
   - Gain: Red + ▲ icon
   - Loss: Blue + ▼ icon
   → Supports color-blind users

2. Chart accessibility
   - aria-label with data summary for candlestick charts
   - Alternative text table for donut charts

3. Keyboard navigation
   - Sidebar menu keyboard traversal
   - HoldingsTable keyboard-driven sort switching
```

---

## 7. Testing Strategy

### 7.1 Test Coverage Expansion

**Current**: Backend pytest + Frontend vitest + Playwright E2E.

**Enhancements**:
```
[Backend]

1. KIS API Mocking Tests
   - Mock httpx responses for scenarios:
     * Normal response
     * Rate limit exceeded (429)
     * Token expired (401)
     * Timeout
     * Partial failure (2 of 5 stocks succeed)
   - Verify Redis cache fallback works correctly

2. Sync Logic Integration Tests
   - reconciliation.py insert/update/delete scenarios
   - Data consistency under concurrent sync requests

3. Security Tests
   - IDOR attempt (access another user's portfolio)
   - Request with expired JWT
   - Refresh with already-consumed JTI
   - Verify 429 on rate limit exceeded

[Frontend]

4. SSE Connection Tests
   - Connect/reconnect scenarios
   - Off-market deactivation verification
   - Data parsing error handling

5. E2E Core Scenarios
   - Register → Login → KIS account setup → Sync → Dashboard check
   - Add stock → Record trade → Verify P&L calculation
   - Token expiry → Auto-refresh → Request retry
```

### 7.2 Coverage Targets

```
Backend overall: 70%+
  - services/ (business logic): 85%+
  - core/security.py (auth): 90%+
  - api/ (routers): 60%+
Frontend unit tests: 50%+
  - hooks/ (custom hooks): 80%+
  - lib/ (utilities): 90%+
E2E: Cover 3-5 core user flows
```

---

## 8. Operational Stability

### 8.1 Monitoring Dashboard

**Current**: Structured logging via structlog, but no visualization or aggregation tooling.

**Improvements**:
```
[Low-cost Monitoring Stack]

Option A: Grafana + Loki (self-hosted, free)
  - Loki: log collection/search (parse structlog JSON directly)
  - Grafana: dashboard visualization
  - Add 2 services to Docker Compose

Option B: Betterstack (SaaS, free tier)
  - Unified log collection + alerts + uptime monitoring
  - No additional infrastructure needed

Key Metrics to Track:
  - KIS API success/failure rate (by time of day)
  - Average response time (by endpoint)
  - Sync success/failure trends
  - Redis cache hit rate
  - SSE concurrent connection count
```

### 8.2 Alert System Implementation

**Current**: alerts table and CRUD API exist, but no actual notification dispatch logic on price trigger is documented.

**Improvements**:
```
Price Alert Check Logic:

1. Check alert conditions during SSE price streaming
   → Compare active alerts on every 30s price update

2. Notification Channels
   - Phase 1: In-app notifications (toast + notification list)
   - Phase 2: Email notifications (SendGrid, Resend, etc.)
   - Phase 3: Telegram Bot notifications (free, real-time)

3. Duplicate Alert Prevention
   - Auto-deactivate triggered alerts (is_active = false)
   - Or add last_triggered_at column for cooldown
```

### 8.3 Graceful Shutdown

**Current**: entrypoint.sh runs uvicorn directly.

**Improvements**:
```
Zero-downtime shutdown on deployment:

1. On SIGTERM:
   - Stop accepting new requests
   - Send close event to active SSE connections
   - Shut down APScheduler gracefully
   - Clean up DB/Redis connection pools
   - Wait up to 30s, then force exit

2. Docker Compose config:
   stop_grace_period: 30s

3. Implement cleanup in FastAPI lifespan event
   (if lifespan is already in use, enhance the shutdown section)
```

---

## 9. Feature Expansion Roadmap

### 9.1 Short-term (1-2 months)

```
□ Automated DB backups + external storage
□ Migrate frontend token storage to HttpOnly cookies
□ Standardize error responses + frontend error boundaries
□ Add DB indexes (section 4.1)
□ Clean up legacy columns in users table
□ Granular per-endpoint rate limiting
□ External uptime monitoring
```

### 9.2 Mid-term (3-6 months)

```
□ Adopt TanStack Query for data fetching layer
□ Implement actual price alert dispatch (in-app + Telegram)
□ Introduce API versioning (/api/v1/)
□ Achieve test coverage targets (Backend 70%, Frontend 50%)
□ Bundle analysis + dynamic import optimization
□ Add CSP header
□ Implement cursor-based pagination
```

### 9.3 Long-term (6+ months)

```
□ Build monitoring dashboard (Grafana or SaaS)
□ Enhanced international stock support (auto currency conversion)
□ Benchmark comparison (vs KOSPI, S&P 500)
□ Dividend tracking and yield analysis
□ Target allocation setting + rebalancing alerts
□ Multi-worker + scheduler separation architecture
□ PWA support (offline dashboard viewing)
```

---

## 10. Summary

The Wealth demonstrates high maturity in tech stack selection, security design, and cost optimization for a personal project. The handling of KIS API as an external dependency — via Redis caching, parallel calls, and graceful degradation — is particularly well-executed.

The three most urgent improvements are **automated DB backups**, **HttpOnly cookie token storage**, and **DB index additions**. These three deliver significant stability and security gains with relatively low effort.

In the mid-to-long term, investing in TanStack Query adoption, monitoring infrastructure, and test coverage expansion will meaningfully elevate the service's maintainability and reliability.
