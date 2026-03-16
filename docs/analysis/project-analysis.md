# THE WEALTH — Project Analysis

Technical strengths, weaknesses, risks, and improvement opportunities.

---

## 1. Current State

### Completeness

| Area | Status | Notes |
|------|--------|-------|
| Backend API | Complete | Auth, CRUD, sync, search, transactions |
| DB Schema | Complete | 6 tables, 5 migrations |
| Frontend UI | Complete | All pages, CRUD, mobile responsive |
| KIS Integration | Complete | Multi-account, tokens, prices, balance, auto-sync |
| Testing | Solid | Backend 55 + Frontend 14 = 69 tests |
| Security | Hardened | jti token revocation, password policy, secret validation, error sanitization |
| Deployment | Not done | Dockerfiles exist, no actual deploy |

### Strengths

- **Full vertical integration**: Auth → Portfolios → Stocks → Prices → P&L
- **Security**: AES-256 encryption, IDOR prevention, JWT rotation with jti revocation, rate limiting, startup secret validation
- **Multi-account**: Multiple KIS accounts per user with auto-portfolio creation
- **Real-time calc**: Prices fetched dynamically, never stored stale in DB
- **Stock search**: 16,322 stocks (KIS MST files, domestic + overseas)
- **Redis resilience**: Price cache fallback (1h TTL), startup preloading

### Remaining Weaknesses

- **Analytics page**: Only placeholder, no charts/analysis implemented
- **Transaction history charts**: API exists but no visualization
- **Price history**: No daily snapshots for "vs previous day" display

---

## 2. Risks

### High

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Python 3.9 EOL** | No security patches, limits package upgrades | Milestone 8: upgrade to 3.10+ |

### Medium

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Redis SPOF** | Redis down → token/search unavailable | In-memory fallback |

### Resolved

- ~~KRX/Naver scraping~~ → Replaced with KIS MST files (stable)
- ~~KIS API failure~~ → Redis price cache fallback + error UI
- ~~No tests~~ → 60 tests (pytest + vitest)
- ~~Token replay~~ → jti + Redis one-time use
- ~~Weak passwords~~ → 8-char minimum enforced server-side
- ~~Cache key collision~~ → SHA-256 hash of full app_key
- ~~Exception detail leak~~ → Generic error messages

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
| CORS | OK (localhost:3000 only) |
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
