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

### PATCH /portfolios/reorder
- **Auth**: Required
- **Request body**: `{ "portfolio_ids": int[] }` (ordered list)
- **Response** (204): No content
- **Notes**: Updates `display_order` for all portfolios in the list

### DELETE /portfolios/{portfolio_id}
- **Auth**: Required (ownership verified)
- **Response** (204): No content
- **Side effect**: Cascade deletes holdings, transactions

---

## Holdings (`/portfolios`)

### GET /portfolios/{portfolio_id}/holdings
- **Auth**: Required (ownership verified)
- **Rate limit**: 30/min
- **Response** (200): `HoldingResponse[]`

### GET /portfolios/{portfolio_id}/holdings/with-prices
- **Auth**: Required (ownership verified)
- **Rate limit**: 30/min
- **Response** (200): Holdings with current prices, P&L, market values fetched live from KIS API
- **Notes**: Uses `asyncio.gather()` for parallel price fetching; falls back to Redis cache on KIS API failure

### POST /portfolios/{portfolio_id}/holdings
- **Auth**: Required (ownership verified)
- **Request body**: `{ "ticker": string, "name": string, "quantity": decimal, "avg_price": decimal }`
- **Response** (201): `HoldingResponse`

### POST /portfolios/{portfolio_id}/holdings/bulk
- **Auth**: Required (ownership verified)
- **Request body**: `{ "holdings": [{ "ticker": string, "name": string, "quantity": decimal, "avg_price": decimal, "market"?: string }] }`
- **Response** (200): `BulkHoldingResult` -- `{ created: int, updated: int, errors: [{ ticker, reason }] }`
- **Notes**: Max 100 items per request. New tickers create new holdings; existing tickers merge (quantity added, weighted average price recalculated). Validation errors are skipped and returned in the errors list.

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
- **Rate limit**: 60/min
- **Response** (200): `TransactionResponse[]`

### GET /portfolios/{portfolio_id}/transactions/paginated
- **Auth**: Required (ownership verified)
- **Rate limit**: 60/min
- **Query params**: `cursor: int` (default 0, last transaction ID from previous page), `limit: int` (default 20, max 100)
- **Response** (200): `TransactionPage` -- `{ items: TransactionResponse[], next_cursor: int | null, has_more: boolean }`
- **Notes**: Cursor-based pagination for infinite scroll. `cursor=0` returns the first page. Excludes soft-deleted transactions.

### POST /portfolios/{portfolio_id}/transactions
- **Auth**: Required (ownership verified)
- **Rate limit**: 60/min
- **Request body**: `{ "ticker": string, "type": "BUY"|"SELL", "quantity": decimal, "price": decimal, "traded_at": datetime }`
- **Response** (201): `TransactionResponse`

### DELETE /portfolios/transactions/{transaction_id}
- **Auth**: Required (ownership verified)
- **Rate limit**: 60/min
- **Response** (204): No content

### PATCH /portfolios/{portfolio_id}/transactions/{transaction_id}
- **Auth**: Required (ownership verified)
- **Rate limit**: 60/min
- **Request body**: `{ "memo": string | null }`
- **Response** (200): `TransactionResponse`
- **Notes**: Updates transaction memo (inline edit for investment journal)

### GET /portfolios/{portfolio_id}/kis-transactions
- **Auth**: Required (ownership verified)
- **Rate limit**: 60/min
- **Query params**: `from_date: string (YYYYMMDD)`, `to_date: string (YYYYMMDD)`
- **Response** (200): List of KIS settlement records (domestic + overseas)
- **Notes**: Requires linked KIS account. Fetches from KIS API `TTTC8001R` (domestic) and `TTTS3035R` (overseas by exchange)

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

### GET /portfolios/{portfolio_id}/export/xlsx
- **Auth**: Required (ownership verified)
- **Response**: Excel file download (Sheet 1: holdings, Sheet 2: transactions)
- **Content-Type**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

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

### GET /analytics/fx-history
- **Auth**: Required
- **Response** (200): USD/KRW exchange rate history from `fx_rate_snapshots` table
- **Notes**: Returns time-series FX rate data used for overseas holdings valuation

### GET /analytics/fx-gain-loss
- **Auth**: Required
- **Response** (200): `[{ "ticker": string, "name": string, "stock_gain_usd": decimal, "fx_gain_krw": decimal, "quantity": decimal, "avg_price": decimal }]`
- **Description**: For each overseas holding, separates stock price gain (USD-denominated) from FX gain/loss (KRW impact of exchange rate change since purchase). Purchase-date FX rate is sourced from the nearest `fx_rate_snapshots.rate` entry (matched by `currency_pair = "USDKRW"` and `snapshot_date`); current price falls back to `avg_price` if Redis cache miss.

### GET /analytics/krw-asset-history
- **Auth**: Required
- **Query params**: `period: string` (default "ALL"; accepts 1M, 3M, 6M, 1Y, ALL)
- **Response** (200): `[{ "date": string (YYYY-MM-DD), "value": decimal, "domestic_value": decimal, "overseas_value_krw": decimal }]`
- **Description**: Time-series total asset value in KRW, combining domestic holdings (KRW) and overseas holdings (USD converted at the day's FX rate from `fx_rate_snapshots`, forward-filled when missing). Sourced from `price_snapshots` joined with `fx_rate_snapshots`.

### GET /analytics/benchmark
- **Auth**: Required
- **Rate limit**: 30/minute
- **Query params**: `index_code: string` (default "KOSPI200"; accepts KOSPI200, SP500), `from: string (YYYY-MM-DD)` (optional), `to: string (YYYY-MM-DD)` (optional)
- **Response** (200): `[{ "date": string (YYYY-MM-DD), "close_price": decimal }]`
- **Description**: Returns daily close price time-series for the specified benchmark index from the `index_snapshots` table. Data is collected by the `collect_benchmark` scheduler job (KST 16:20 weekdays).
- **Errors**: 400 (invalid `index_code`)

### GET /analytics/stocks/{ticker}/sma
- **Auth**: Required
- **Rate limit**: 30/minute
- **Path params**: `ticker: string`
- **Query params**: `period: int` (default 20, min 2, max 200), `from: string (YYYY-MM-DD)` (optional), `to: string (YYYY-MM-DD)` (optional)
- **Response** (200): `[{ "date": string (YYYY-MM-DD), "sma": decimal }]`
- **Description**: Returns the simple moving average (SMA) time-series for a ticker from `price_snapshots`. Points where SMA cannot be computed (insufficient preceding data) are excluded from the response. Fetches `period-1` extra days before `from` to ensure accurate SMA at the start of the requested range.

---

## Alerts (`/alerts`)

### GET /alerts
- **Auth**: Required
- **Response** (200): `AlertOut[]`

### POST /alerts
- **Auth**: Required
- **Request body**: `{ "ticker": string, "name": string, "condition": "above"|"below", "threshold": decimal }`
- **Response** (201): `AlertOut`

### PATCH /alerts/{alert_id}
- **Auth**: Required (ownership verified)
- **Request body**: `{ "is_active"?: boolean, "threshold"?: decimal }`
- **Response** (200): `AlertOut`
- **Notes**: Toggle active/inactive or update threshold value

### DELETE /alerts/{alert_id}
- **Auth**: Required (ownership verified)
- **Response** (204): No content

---

## Notifications (`/notifications`)

### GET /notifications
- **Auth**: Required
- **Response** (200): `NotificationOut[]` (max 100, unread first, then newest)

### PATCH /notifications/{notification_id}/read
- **Auth**: Required (ownership verified)
- **Response** (200): `NotificationOut`

### POST /notifications/read-all
- **Auth**: Required
- **Response** (204): No content
- **Notes**: Marks all unread notifications as read for the authenticated user

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

## Orders (`/portfolios`)

### POST /portfolios/{portfolio_id}/orders
- **Auth**: Required (ownership verified)
- **Rate limit**: 10/minute per user
- **Request body**: `{ "ticker": string, "name"?: string, "order_type": "BUY"|"SELL", "order_class": "limit"|"market", "quantity": int, "price"?: decimal, "exchange_code"?: string, "memo"?: string }`
- **Response** (200): `OrderResult` -- order record with KIS order number
- **Side effects**: Creates `orders` DB record; on success (pending), creates `transaction` and updates `holdings` (weighted avg price recalculation for BUY, quantity reduction for SELL); invalidates cash balance cache
- **Notes**: Domestic/overseas auto-detected by ticker pattern. Account-type-specific TR_ID routing (regular/ISA/pension/IRP). Duplicate order prevention via Redis lock (TTL 10s).
- **Errors**: 400 (no KIS account linked), 502 (KIS API failure)

### GET /portfolios/{portfolio_id}/orders/orderable
- **Auth**: Required (ownership verified)
- **Query params**: `ticker: string`, `price: int` (default 0), `order_type: string` (default "BUY")
- **Response** (200): `OrderableInfoResponse` -- `{ orderable_quantity, orderable_amount, current_price?, currency }`

### GET /portfolios/{portfolio_id}/orders/pending
- **Auth**: Required (ownership verified)
- **Query params**: `is_overseas: bool` (default false)
- **Response** (200): `PendingOrderResponse[]` -- list of unfilled orders from KIS API

### POST /portfolios/{portfolio_id}/orders/settle
- **Auth**: Required (ownership verified)
- **Response** (200): `{ "settled": int, "failed": int }` — counts of orders checked against KIS API and updated in DB
- **Description**: Manually triggers a check of all pending orders for the portfolio against KIS API. Updates order status to "filled" or "partial" where applicable. Useful when auto-settle has not yet run.
- **Errors**: 400 (no KIS account linked), 502 (KIS API failure)

### DELETE /portfolios/{portfolio_id}/orders/{order_no}
- **Auth**: Required (ownership verified)
- **Query params**: `ticker: string`, `quantity: int`, `price: int` (default 0), `is_overseas: bool` (default false), `exchange_code: string` (default "")
- **Response** (204): No content
- **Side effect**: Updates order status to "cancelled" in DB

### GET /portfolios/{portfolio_id}/cash-balance
- **Auth**: Required (ownership verified)
- **Response** (200): `CashBalanceResponse` -- `{ total_cash, available_cash, total_evaluation, total_profit_loss, profit_loss_rate, currency, foreign_cash?, usd_krw_rate? }`
- **Notes**: Combines domestic balance (TTTC8434R) with overseas holdings evaluation (converted to KRW). When overseas holdings have `frcr_evlu_pfls_amt == 0`, falls back to `sum(quantity * avg_price)`. Result cached in Redis for 30 seconds.

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

### GET /health/disk
- **Auth**: Required
- **Response** (200): Disk usage statistics for the server filesystem
- **Notes**: Reports used/total/free disk space; used for proactive disk capacity monitoring

---

## Internal API (`/internal`)

### POST /internal/backup-status
- **Auth**: `X-Internal-Secret` header (not JWT)
- **Request body**: `{ "status": "success"|"error", "message"?: string }`
- **Response** (204): No content
- **Notes**: Called by `backup-postgres.sh` to record backup results to `sync_logs` (sync_type='db_backup'). Returns 503 if `INTERNAL_SECRET` env var is not configured.
