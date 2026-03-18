# THE WEALTH — Project Analysis

Technical strengths, weaknesses, risks, and improvement opportunities.

---

## 1. Current State

### Completeness

| Area | Status | Notes |
|------|--------|-------|
| Backend API | Complete | Auth, CRUD, sync, search, transactions, watchlist, analytics, CSV export |
| DB Schema | Complete | 9 tables, 10 migrations |
| Frontend UI | Complete | All pages, CRUD, mobile responsive, sector chart, watchlist |
| KIS Integration | Complete | Multi-account, tokens, prices, balance, auto-sync |
| Testing | Solid | Backend 19 test files + Frontend 6 test files + 2 E2E specs |
| Security | Hardened | jti revocation, password policy, secret validation, security headers middleware |
| CI/CD | Done | 6 workflows: backend, frontend, e2e, docker-build, codeql, deploy |
| Deployment | Not done | Dockerfiles exist, no actual deploy |

### Strengths

- **Full vertical integration**: Auth → Portfolios → Stocks → Prices → P&L
- **Security**: AES-256 encryption, IDOR prevention, JWT rotation with jti revocation, rate limiting, startup secret validation, security headers middleware
- **Multi-account**: Multiple KIS accounts per user with auto-portfolio creation
- **Real-time calc**: Prices fetched dynamically, never stored stale in DB
- **Stock search**: 16,322 stocks (KIS MST files, domestic + overseas)
- **Redis resilience**: Price cache fallback (1h TTL), startup preloading
- **Watchlist**: User watchlist with duplicate prevention (unique constraint)
- **Sector allocation**: Ticker-to-sector mapping with PieChart visualization
- **Data export**: CSV streaming export for holdings and transactions
- **CI/CD breadth**: 6 workflows including E2E (Playwright), Docker build, CodeQL security scanning
- **Auto-generated types**: openapi-typescript for frontend API type safety

### Remaining Weaknesses

- ~~Analytics page~~ → **Done**: summary cards, allocation donut, performance table, sector chart
- ~~Price history~~ → **Done**: price_snapshots table and service
- ~~Input validation gaps~~ → **Fixed**: name min/max, qty/price gt=0, Literal type
- ~~No pagination~~ → **Fixed**: transactions + sync logs now paginated
- ~~N+1 query~~ → **Fixed**: list_portfolios uses LEFT JOIN GROUP BY
- ~~Missing error handling~~ → **Fixed**: Settings page try-catch + toast on all actions
- ~~Mobile overflow~~ → **Fixed**: responsive padding, 2-col grid form, card views for tables on mobile
- **Test gaps**: No tests for watchlist API, CSV export endpoints, security headers middleware, sector allocation API
- **Frontend component tests**: WatchlistSection and SectorAllocationChart lack unit tests

---

## 2. Risks

### High

| Risk | Description | Mitigation |
|------|-------------|------------|
| **passlib crypt deprecation** | `crypt` module removed in Python 3.13, passlib uses it | Migrate to `bcrypt` directly or use passlib fork |
| **ecdsa vulnerability** | GHSA-wj6h-64fc-37mp via python-jose | Replace python-jose with PyJWT |

### Medium

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Redis SPOF** | Redis down → token/search unavailable | In-memory fallback |

### Resolved

- ~~KRX/Naver scraping~~ → Replaced with KIS MST files (stable)
- ~~KIS API failure~~ → Redis price cache fallback + error UI
- ~~No tests~~ → 19 backend test files + 6 frontend test files + 2 E2E specs
- ~~Token replay~~ → jti + Redis one-time use
- ~~Weak passwords~~ → 8-char minimum enforced server-side
- ~~Cache key collision~~ → SHA-256 hash of full app_key
- ~~Exception detail leak~~ → Generic error messages
- ~~Python 3.9 EOL~~ → Upgraded to Python 3.12

---

## 3. Security Checklist

| Item | Status |
|------|--------|
| JWT with jti revocation | OK |
| Password min 8 chars | OK |
| bcrypt hashing | OK |
| AES-256-GCM encryption | OK (strict 64-char hex key) |
| IDOR prevention | OK |
| SQL Injection | OK (SQLAlchemy ORM) |
| Rate limiting | OK (60 req/min) |
| CORS | OK (configurable via CORS_ORIGINS env) |
| XSS | OK (React escaping) |
| CSRF | OK (SameSite=Lax) |
| Startup secret validation | OK (rejects placeholders) |
| HTTPS enforcement | OK (KIS_BASE_URL must be https) |
| Error sanitization | OK (no internal details in responses) |

---

## 4. Performance

| Area | Current | Improvement |
|------|---------|-------------|
| Stock search | 16K items O(n) scan | Trie or Redis indexing |
| Price fetch | asyncio.gather per ticker | Batch API if available |
| Dashboard | 30s polling | WebSocket/SSE |
