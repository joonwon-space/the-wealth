# THE WEALTH — Project Overview

KIS (Korea Investment & Securities) OpenAPI-based personal asset management dashboard.
Follows Korean stock market color convention (up=red, down=blue). Real-time P&L tracking with auto account sync.

## Tech Stack

| Layer | Tech | Notes |
|-------|------|-------|
| **Frontend** | Next.js 16 (App Router), React 19, TypeScript, Tailwind v4 | SSR + CSR |
| **UI** | shadcn/ui (base-nova), TanStack Table v8, Recharts, Sonner | Dialog, Input, Card, Table, Skeleton, Toast |
| **State** | Zustand | Auth state (localStorage + cookie) |
| **HTTP** | Axios | JWT auto-refresh interceptor |
| **Backend** | FastAPI (Python 3.9+), async/await | uvicorn, CORS localhost:3000 |
| **ORM** | SQLAlchemy 2.0 (async) + Alembic | asyncpg driver |
| **DB** | PostgreSQL | Homebrew local or Docker |
| **Cache** | Redis | KIS tokens (24h), stock list (24h), price cache (1h) |
| **Auth** | JWT (access 30min + refresh 7d with jti revocation) | passlib/bcrypt |
| **Encryption** | AES-256-GCM | KIS credentials stored encrypted |
| **Scheduler** | APScheduler | 1h interval auto sync |
| **Rate Limiting** | slowapi | 60 req/min |
| **Stock Data** | KIS MST/COD master files | 16,322 stocks (4,278 domestic + 12,044 overseas) |

## API Endpoints

### Auth (`/auth`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register (8+ char password enforced) |
| POST | `/auth/login` | Login (access + refresh tokens with jti) |
| POST | `/auth/refresh` | Token rotation (one-time use, Redis jti) |

### Portfolios (`/portfolios`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/portfolios` | List portfolios (with holdings_count, total_invested) |
| POST | `/portfolios` | Create portfolio |
| DELETE | `/portfolios/{id}` | Delete portfolio |
| GET | `/portfolios/{id}/holdings` | List holdings |
| GET | `/portfolios/{id}/holdings/with-prices` | Holdings with current price & P&L |
| POST | `/portfolios/{id}/holdings` | Add holding |
| PATCH | `/portfolios/holdings/{id}` | Update holding |
| DELETE | `/portfolios/holdings/{id}` | Delete holding |
| GET | `/portfolios/{id}/transactions` | List transactions (desc, limit 200) |
| POST | `/portfolios/{id}/transactions` | Create transaction (BUY/SELL) |

### Dashboard (`/dashboard`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard/summary` | Total assets, P&L, allocation (uses kis_accounts) |

### Stocks (`/stocks`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/stocks/search?q=` | Search (KOSPI + KOSDAQ + NYSE + NASDAQ + AMEX, max_length=50) |

### Users (`/users`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/users/kis-credentials` | Save KIS credentials (AES encrypted) |

### Sync (`/sync`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/sync/balance` | Query all KIS accounts, auto-create portfolios, reconcile holdings |
| POST | `/sync/{portfolio_id}` | Sync portfolio via linked KIS account |
| GET | `/sync/logs` | Sync history |

## DB Models

| Table | Key Columns | Notes |
|-------|-------------|-------|
| **users** | email, hashed_password, kis_*_enc, kis_account_no | User-level KIS creds (legacy) |
| **kis_accounts** | user_id, label, account_no, acnt_prdt_cd, app_key_enc, app_secret_enc | Multi-account support, AES encrypted |
| **portfolios** | user_id, name, currency, kis_account_id | Linked to KIS account (unique) |
| **holdings** | portfolio_id, ticker, name, quantity, avg_price | Current price NOT stored |
| **transactions** | portfolio_id, ticker, type (BUY/SELL), quantity, price, traded_at | Trade history |
| **sync_logs** | user_id, portfolio_id, status, inserted, updated, deleted | Audit log |

## Frontend Pages

| Path | Description |
|------|-------------|
| `/` | Landing |
| `/login` | Login (shadcn/ui Input, Button) |
| `/register` | Register (8+ char password) |
| `/dashboard` | Summary cards, donut chart, holdings table, skeleton loading, error UI |
| `/dashboard/portfolios` | Portfolio cards (holdings count, invested), create dialog |
| `/dashboard/portfolios/[id]` | Holdings CRUD with prices/P&L, transaction history + create form |
| `/dashboard/analytics` | Placeholder |
| `/dashboard/settings` | KIS credentials, manual sync, multi-account balance inquiry |

## Services

| Service | Role |
|---------|------|
| **kis_token.py** | KIS OAuth token with SHA-256 hash cache key (Redis 24h) |
| **kis_price.py** | Domestic/overseas price fetch (asyncio.gather, Redis cache fallback) |
| **kis_account.py** | KIS balance inquiry (TTTC8434R) |
| **reconciliation.py** | DB vs KIS holdings diff → INSERT/UPDATE/DELETE |
| **stock_search.py** | KIS MST/COD file parsing → Redis cache → local search |
| **scheduler.py** | APScheduler 1h auto sync for all KIS accounts |
