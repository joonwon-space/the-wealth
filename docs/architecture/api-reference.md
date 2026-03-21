# API Reference

Base URL: `/api/v1`

All endpoints except `/auth/register`, `/auth/login`, `/auth/refresh`, and `/health` require authentication via `Authorization: Bearer {access_token}` header or `access_token` HttpOnly cookie.

Standardized error response envelope:
```json
{
  "error": {
    "code": "STATUS_CODE",
    "message": "Human-readable message",
    "request_id": "uuid4"
  }
}
```

---

## Authentication (`/auth`)

Rate-limited endpoints for brute force protection.

### POST /auth/register
- **Rate limit**: 3/min
- **Auth**: None
- **Request body**: `{ "email": string, "password": string }`
- **Response** (201): `{ "id": int, "email": string, "created_at": datetime }`
- **Errors**: 400 (duplicate email)

### POST /auth/login
- **Rate limit**: 5/min
- **Auth**: None
- **Request body**: `{ "email": string, "password": string }`
- **Response** (200): `{ "access_token": string, "refresh_token": string, "token_type": "bearer" }`
- **Side effect**: Sets `access_token` HttpOnly cookie
- **Errors**: 401 (invalid credentials)

### POST /auth/refresh
- **Auth**: None (refresh token in body)
- **Request body**: `{ "refresh_token": string }`
- **Response** (200): `{ "access_token": string, "refresh_token": string, "token_type": "bearer" }`
- **Side effect**: Consumes old JTI in Redis, issues new token pair
- **Errors**: 401 (invalid/expired/consumed refresh token)

### POST /auth/change-password
- **Auth**: Required
- **Request body**: `{ "current_password": string, "new_password": string }`
- **Response** (204): No content
- **Side effect**: Revokes all refresh tokens for the user
- **Errors**: 400 (incorrect current password)

### POST /auth/logout
- **Auth**: Required
- **Response** (204): No content
- **Side effect**: Clears `access_token` cookie

---

## Portfolios (`/portfolios`)

### GET /portfolios
- **Auth**: Required
- **Response** (200): `PortfolioResponse[]`
- **Notes**: Returns only portfolios owned by the authenticated user

### POST /portfolios
- **Auth**: Required
- **Request body**: `{ "name": string, "currency"?: string }`
- **Response** (201): `PortfolioResponse`

### PATCH /portfolios/{portfolio_id}
- **Auth**: Required (ownership verified)
- **Request body**: `{ "name"?: string, "currency"?: string }`
- **Response** (200): `PortfolioResponse`

### DELETE /portfolios/{portfolio_id}
- **Auth**: Required (ownership verified)
- **Response** (204): No content
- **Side effect**: Cascade deletes holdings, transactions

### PATCH /portfolios/{portfolio_id}/kis-account
- **Auth**: Required (ownership verified)
- **Request body**: `{ "kis_account_id": int | null }`
- **Response** (200): `PortfolioResponse`

---

## Holdings (`/portfolios`)

### GET /portfolios/{portfolio_id}/holdings
- **Auth**: Required (ownership verified)
- **Response** (200): `HoldingResponse[]`

### GET /portfolios/{portfolio_id}/holdings/with-prices
- **Auth**: Required (ownership verified)
- **Response** (200): Holdings with current prices, P&L, market values fetched live from KIS API
- **Notes**: Uses `asyncio.gather()` for parallel price fetching; falls back to Redis cache on KIS API failure

### POST /portfolios/{portfolio_id}/holdings
- **Auth**: Required (ownership verified)
- **Request body**: `{ "ticker": string, "name": string, "quantity": decimal, "avg_price": decimal }`
- **Response** (201): `HoldingResponse`

### PATCH /portfolios/holdings/{holding_id}
- **Auth**: Required (ownership verified)
- **Request body**: `{ "quantity"?: decimal, "avg_price"?: decimal }`
- **Response** (200): `HoldingResponse`

### DELETE /portfolios/holdings/{holding_id}
- **Auth**: Required (ownership verified)
- **Response** (204): No content

---

## Transactions (`/portfolios`)

### GET /portfolios/{portfolio_id}/transactions
- **Auth**: Required (ownership verified)
- **Response** (200): `TransactionResponse[]`

### POST /portfolios/{portfolio_id}/transactions
- **Auth**: Required (ownership verified)
- **Request body**: `{ "ticker": string, "type": "BUY"|"SELL", "quantity": decimal, "price": decimal, "traded_at": datetime }`
- **Response** (201): `TransactionResponse`

### DELETE /portfolios/transactions/{transaction_id}
- **Auth**: Required (ownership verified)
- **Response** (204): No content

---

## CSV Export (`/portfolios`)

### GET /portfolios/{portfolio_id}/export/csv
- **Auth**: Required (ownership verified)
- **Response**: CSV file download (holdings data)
- **Content-Type**: `text/csv`

### GET /portfolios/{portfolio_id}/transactions/export/csv
- **Auth**: Required (ownership verified)
- **Response**: CSV file download (transaction history)
- **Content-Type**: `text/csv`

---

## Dashboard (`/dashboard`)

### GET /dashboard/summary
- **Auth**: Required
- **Rate limit**: 120/min
- **Query params**: `refresh?: boolean` (clears price cache when true)
- **Response** (200): `DashboardSummary` -- aggregated portfolio data with live prices
  - `kis_status`: `"ok"` | `"degraded"` -- indicates KIS API availability
  - `usd_krw_rate`: USD/KRW exchange rate used (when overseas holdings present)
  - `triggered_alerts`: list of alerts whose conditions are currently met
- **Notes**: Fetches current prices from KIS API via `asyncio.gather()`; computes P&L dynamically. When all price fetches fail, returns `kis_status: "degraded"` and frontend shows a warning banner.

---

## Analytics (`/analytics`)

### GET /analytics/metrics
- **Auth**: Required
- **Response** (200): Key performance metrics (total return, daily change, etc.)

### GET /analytics/monthly-returns
- **Auth**: Required
- **Response** (200): `MonthlyReturn[]` -- monthly return percentages from price snapshots

### GET /analytics/portfolio-history
- **Auth**: Required
- **Response** (200): `PortfolioHistoryPoint[]` -- time-series portfolio value data

### GET /analytics/sector-allocation
- **Auth**: Required
- **Response** (200): `SectorAllocation[]` -- sector-wise distribution of holdings

---

## Alerts (`/alerts`)

### GET /alerts
- **Auth**: Required
- **Response** (200): `AlertOut[]`

### POST /alerts
- **Auth**: Required
- **Request body**: `{ "ticker": string, "name": string, "condition": "above"|"below", "threshold": decimal }`
- **Response** (201): `AlertOut`

### DELETE /alerts/{alert_id}
- **Auth**: Required (ownership verified)
- **Response** (204): No content

---

## Stocks (`/stocks`)

### GET /stocks/search
- **Auth**: Required
- **Query params**: `q: string` (search term, supports Korean initial consonant search)
- **Response** (200): Matching stock list from Redis-cached KRX+NYSE+NASDAQ master

### GET /stocks/{ticker}/detail
- **Auth**: Required
- **Response** (200): Stock detail with current price from KIS API

---

## Sync (`/sync`)

### POST /sync/balance
- **Auth**: Required
- **Rate limit**: 5/min
- **Response** (200): Sync results for all user portfolios with linked KIS accounts
- **Notes**: Fetches balances from KIS API and reconciles with DB holdings

### POST /sync/{portfolio_id}
- **Auth**: Required (ownership verified)
- **Rate limit**: 5/min
- **Response** (200): Sync results for the specific portfolio

### GET /sync/logs
- **Auth**: Required
- **Response** (200): Sync history log entries (inserted/updated/deleted counts)

---

## KIS Account Management (`/users`)

### POST /users/kis-accounts
- **Auth**: Required
- **Request body**: `{ "label": string, "account_no": string, "acnt_prdt_cd": string, "app_key": string, "app_secret": string }`
- **Response** (201): KIS account (app_key/app_secret stored AES-256-GCM encrypted)

### GET /users/kis-accounts
- **Auth**: Required
- **Response** (200): List of user's KIS accounts (credentials not returned)

### PATCH /users/kis-accounts/{account_id}
- **Auth**: Required (ownership verified)
- **Request body**: Partial update fields
- **Response** (200): Updated KIS account

### DELETE /users/kis-accounts/{account_id}
- **Auth**: Required (ownership verified)
- **Response** (204): No content

### POST /users/kis-accounts/{account_id}/test
- **Auth**: Required (ownership verified)
- **Response** (200): KIS token issuance test result
- **Notes**: Decrypts credentials and attempts KIS OAuth2 token request

---

## Prices (`/prices`)

### GET /prices/{ticker}/history
- **Auth**: Required
- **Response** (200): Historical price data from `price_snapshots` table

### GET /prices/stream
- **Auth**: via query param `token` (SSE does not support headers)
- **Response**: Server-Sent Events stream
- **Behavior**:
  - 30-second interval price updates for user's holdings
  - Active only during KST 09:00-15:30 (market hours)
  - 15-second heartbeat events
  - Per-user max 3 concurrent connections
  - 2-hour max connection duration

---

## Chart (`/chart`)

### GET /chart/daily
- **Auth**: Required
- **Query params**: `ticker: string`, date range params
- **Response** (200): Daily OHLCV data from KIS API (`FHKST01010400` TR)

---

## Watchlist (`/watchlist`)

### GET /watchlist
- **Auth**: Required
- **Response** (200): `WatchlistOut[]`

### POST /watchlist
- **Auth**: Required
- **Request body**: `{ "ticker": string, "name": string, "market": "KRX"|"NYSE"|"NASDAQ" }`
- **Response** (201): `WatchlistOut`

### DELETE /watchlist/{item_id}
- **Auth**: Required (ownership verified)
- **Response** (204): No content

---

## Health Check

### GET /health
- **Auth**: None
- **Response** (200): `{ "status": "ok" }`

### GET /api/v1/health
- **Auth**: None
- **Response** (200): `{ "status": "ok", "last_backup_at": "ISO-8601 | null", "backup_age_hours": float | null }`
- **Notes**: Versioned health check with last DB backup information (filesystem mtime or sync_logs fallback)

---

## Data Integrity (`/health`)

### GET /health/data-integrity
- **Auth**: Required
- **Response** (200): `{ "status": "ok"|"degraded", "checked_weekdays": 7, "missing_snapshots": [...], "present_snapshots": [...] }`
- **Notes**: Checks for missing `price_snapshots` entries over the last 7 weekdays

### GET /health/holdings-reconciliation
- **Auth**: Required
- **Response** (200): `{ "status": "ok"|"degraded", "checked_holdings": int, "mismatches": [...] }`
- **Notes**: Compares `holdings.quantity` against transaction history (BUY - SELL) sum; excludes soft-deleted transactions

### GET /health/orphan-records
- **Auth**: Required
- **Response** (200): `{ "status": "ok"|"degraded", "orphan_holdings": int, "orphan_transactions": int, "orphan_sync_logs": int }`
- **Notes**: Detects records referencing non-existent portfolio IDs (should be 0 if CASCADE DELETE works correctly)

---

## Internal API (`/internal`)

### POST /internal/backup-status
- **Auth**: `X-Internal-Secret` header (not JWT)
- **Request body**: `{ "status": "success"|"error", "message"?: string }`
- **Response** (204): No content
- **Notes**: Called by `backup-postgres.sh` to record backup results to `sync_logs` (sync_type='db_backup'). Returns 503 if `INTERNAL_SECRET` env var is not configured.
