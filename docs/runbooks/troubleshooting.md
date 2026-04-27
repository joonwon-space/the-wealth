# Troubleshooting Runbook

Common developer issues, each with: symptom → cause → resolution.
Code references are file-path:line based on current main.

---

## 1. Redis 연결 실패

### Symptom
Backend startup fails with:
```
ConnectionRefusedError: [Errno 111] Connect refused
aioredis.exceptions.ConnectionError: Error connecting to localhost:6379
```
Or the `/health` endpoint returns `redis: error`.

### Cause
Redis is not running, or `REDIS_URL` points to the wrong host/port.

### Resolution

```bash
# 1. Check Docker containers
docker compose -f docker-compose.dev.yml ps

# 2. If Redis container is down, start it
docker compose -f docker-compose.dev.yml up -d redis

# 3. Verify Redis is up
redis-cli ping       # should return PONG

# 4. Check env var
grep REDIS_URL backend/.env   # default: redis://localhost:6379
```

Default config (`backend/app/core/config.py:18`):
```python
REDIS_URL: str = "redis://localhost:6379"
```

If running Docker Desktop on Windows, ensure Docker is using the default bridge and port `6379` is not occupied by another process (`netstat -ano | findstr 6379`).

---

## 2. pytest — DB Connection Refused

### Symptom
```
sqlalchemy.exc.OperationalError: (asyncpg.exceptions.ConnectionDoesNotExistError)
connection to server at "localhost" (127.0.0.1), port 5432 failed
```

### Cause
Integration tests require a live PostgreSQL instance. The test DB URL defaults to:
```
postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test
```
(see `backend/tests/conftest.py:23-25`)

Unit tests (marked `@pytest.mark.unit`) don't need Postgres — integration tests do.

### Resolution

```bash
# 1. Start Postgres via Docker
docker compose -f docker-compose.dev.yml up -d postgres

# 2. Create test database (first-time only)
psql -U postgres -h localhost -c "CREATE DATABASE the_wealth_test;"

# 3. Override DB URL if your username differs
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/the_wealth_test"

# 4. Run only unit tests (no Postgres needed)
cd backend && pytest -m unit -q

# 5. Run all tests including integration
cd backend && pytest -q --tb=short
```

Note: The test suite creates schema once before all tests and drops it after (`conftest.py:49`). Each test gets a transaction-rolled-back session (`conftest.py:105`), so data isolation is automatic.

---

## 3. KIS API 403 / 인증 에러

### Symptom
KIS API calls return HTTP 403, or backend logs show:
```
KIS token endpoint returned HTTP 403
ValueError: KIS token endpoint returned unexpected response format
```
Or trade/balance responses contain `"rt_cd": "1"` with an error `msg1`.

### Cause — Three possible sources

| Cause | Signal |
|-------|--------|
| **Token expired mid-session** | `msg1` contains "기간이 만료" or "토큰이 유효하지 않습니다" |
| **Wrong APP_KEY / APP_SECRET** | HTTP 403 on first token issuance; `msg1` "접근토큰 발급 불가" |
| **IP block** | `msg1` "IP 차단" or "허용되지 않은 IP" |
| **Mock mode URL mismatch** | Wrong TR_ID for mock (`KIS_MOCK_MODE=True` but prod TR_IDs used) |

### Resolution

```bash
# 1. Check if token is cached in Redis
redis-cli get "kis_token:{account_id}"
# If empty, token issuance is failing — check APP_KEY/APP_SECRET

# 2. Force token refresh by deleting cache
redis-cli del "kis_token:{account_id}"
# Next request will re-issue token via kis_token.py

# 3. Verify credentials in DB
# Login → Settings → KIS 계정 → confirm account is visible

# 4. Check KIS developer portal for IP whitelist
# Add your dev machine IP at: https://apiportal.koreainvestment.com/

# 5. Verify KIS_MOCK_MODE setting
grep KIS_MOCK_MODE backend/.env
# True = 모의투자 (vts.koreainvestment.com), False = 실전 (openapi.koreainvestment.com)
```

KIS token lifecycle (`backend/app/services/kis_token.py`):
- Default TTL: 24h (`_TOKEN_TTL_SECONDS = 86400`, line 23)
- Redis key: `kis_token:{account_id}` (proactive renewal happens before expiry)
- Token URL: `{KIS_BASE_URL}/oauth2/tokenP` (line 73)

Common `rt_cd` / `msg1` values:

| rt_cd | msg1 (partial) | Meaning |
|-------|----------------|---------|
| `0` | 정상처리 | Success |
| `1` | 기간이 만료 | Token expired — delete Redis key, retry |
| `1` | 허용되지 않은 IP | IP not whitelisted in KIS developer portal |
| `1` | 접근토큰 발급 불가 | Wrong APP_KEY or APP_SECRET |
| `1` | 주문수량 오류 | Order quantity invalid |

---

## 4. Alembic Head Conflict (두 PR 동시 머지 시)

### Symptom
```
alembic.util.exc.CommandError: Multiple head revisions are present for given argument 'head'
```

### Cause
Two branches each created a migration. After both are merged, Alembic sees two "latest" revisions with no common successor.

### Resolution

```bash
# 1. See the conflicting heads
cd backend && alembic heads

# 2. Create a merge migration
alembic merge heads -m "merge conflicting heads"
# This creates a new migration file with both heads as down_revision

# 3. Apply it
alembic upgrade head

# 4. Commit the merge migration file
git add alembic/versions/
git commit -m "fix: merge alembic heads"
```

Prevention: Before creating a new migration, always `git pull` and run `alembic upgrade head` first.

---

## 5. SSE Not Connecting in Dev

### Symptom
The real-time price stream (SSE) does not connect, or the browser shows the EventSource failing with HTTP 401/403/500.

### Cause — Two likely sources

1. **Ticket fetch failing**: The frontend calls `POST /auth/sse-ticket` before opening the EventSource. If that POST fails (auth expired, CORS issue), the EventSource URL gets no ticket and the server rejects it.
2. **Max connection limit**: The server allows max 3 concurrent SSE connections per user (`backend/app/api/prices.py:43`). Exceeding this returns 429.

### Resolution

```bash
# In browser DevTools → Network tab:
# 1. Look for POST /auth/sse-ticket — must return 200 with {"ticket": "..."}
# 2. Then look for GET /api/v1/prices/stream?ticket=... — must show status 200 (EventStream)

# If the ticket POST returns 401:
#   → User is not logged in or access token expired
#   → Axios interceptor should auto-refresh — check /auth/refresh call in Network tab

# If 429 (too many connections):
#   → Close other tabs/windows that have the dashboard open
#   → Reload

# Verify SSE ticket Redis TTL (30s — ticket must be used quickly):
redis-cli ttl "sse-ticket:{uuid}"
```

SSE ticket flow (`backend/app/api/auth.py:356-363`, `deps.py:56-68`):
1. Frontend POSTs `/auth/sse-ticket` → server stores `sse-ticket:{uuid}` in Redis (TTL 30s)
2. Frontend opens `EventSource("/api/v1/prices/stream?ticket={uuid}")`
3. Server reads & deletes ticket on first connection

---

## 6. `next build` OOM on Windows

### Symptom
```
FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory
```
During `npm run build` in the `frontend/` directory.

### Cause
Next.js build process (especially with Tailwind v4 and many pages) can exhaust Node.js's default heap (~1.5 GB) on Windows with limited RAM or WSL2 memory limits.

### Resolution

```bash
# Option A: Increase Node heap before building
cd frontend
NODE_OPTIONS="--max-old-space-size=4096" npm run build

# Option B: Add to package.json scripts (permanent fix)
# "build": "NODE_OPTIONS='--max-old-space-size=4096' next build"

# Option C: If using WSL2 — add to %USERPROFILE%\.wslconfig
# [wsl2]
# memory=8GB
```

If OOM persists after increasing heap, check for import cycles or unnecessarily large server-side data fetches that inflate the build-time bundle.

---

## 7. Frontend Dev Server Port Conflict

### Symptom
```
Error: listen EADDRINUSE: address already in use :::3000
```

### Resolution

```bash
# Find and kill the process using port 3000 (Windows)
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Or run on a different port
cd frontend && npm run dev -- -p 3001
# Then update backend CORS_ORIGINS in backend/.env to include http://localhost:3001
```

---

## 8. Backend Import Errors After Refactor

### Symptom
`uvicorn app.main:app --reload` fails with `ImportError` or `ModuleNotFoundError`.

### Common causes
- Scheduler split files (`scheduler_portfolio_jobs.py`, `scheduler_market_jobs.py`, `scheduler_ops_jobs.py`) may not be wired — see `TD-102` in `docs/plan/tasks.md`
- A service was moved but the old import path was kept somewhere

### Resolution

```bash
cd backend
source venv/bin/activate
python -c "from app.main import app; print('OK')"
# Full import chain validation — shows exact error location
```

---

## 9. KIS API 단절

### Symptom

Backend logs show repeated:
```
ConnectTimeout: ...
ValueError: second argument (exceptions) must be a non-empty sequence
All price fetches failed — returning degraded dashboard
```

Dashboard shows `—` for all holdings prices. Login may be slow if sync was not yet background-tasked.

### Cause

KIS API server (`openapi.koreainvestment.com:9443`) is temporarily unreachable — network outage, KIS maintenance, or DNS failure.

The `ValueError` about "non-empty sequence" is an anyio 4.x happy-eyeballs bug: when all connect attempts are cancelled before raising `OSError`, anyio tries to build `ExceptionGroup("...", [])` with an empty list, which Python 3.11+ rejects. It masks the real `ConnectTimeout`. Our `except ValueError` backstop in `fetch_domestic_price` / `fetch_overseas_price` catches this.

### 1차 확인

```bash
# Check backend logs for KIS health events
docker logs the-wealth-backend-1 2>&1 | grep -i "KisHealth\|kis-unreachable\|bulk fetch"

# Check Sentry: search fingerprint "kis-unreachable" — all outage events grouped under 1 issue.

# Check is KIS actually reachable from the container
docker exec the-wealth-backend-1 curl -sv --max-time 5 https://openapi.koreainvestment.com:9443/ 2>&1 | grep -E "Connected|SSL|timed out|refused"
```

### 자동 복구 동작

- `fetch_prices_parallel` detects ≥80% ticker failures → calls `set_kis_availability(False, "runtime: bulk connect failure")` → subsequent calls skip KIS and return Redis-cached prices.
- `scheduler.py` runs `_kis_health_recheck_job` every **30 seconds**:
  - When `is_available=False`: immediately calls `check_kis_api_health()`. On recovery, logs `KIS API recovered — is_available=True`.
  - When `is_available=True`: applies a 10-minute cooldown to limit proactive checks.
- `settle_orders_job` (order settlement) checks `get_kis_availability()` at start and skips when `False` to prevent error accumulation.
- Login `_bg_sync_user` skips KIS sync and logs `Login sync skipped: KIS unavailable`.

No manual action needed if KIS recovers within minutes — the system self-heals.

### 수동 강제 복구

If the auto health-check is not picking up recovery (e.g. after a prolonged outage), restart the backend container:

```bash
docker compose restart backend
```

This triggers `check_kis_api_health()` at startup (`app/main.py lifespan`) and resets `is_available` to the current truth.

### 진짜 KIS 측 장애 vs 우리 네트워크 구분

```bash
# From the container — if this times out, KIS is down on their end
docker exec the-wealth-backend-1 curl -sv --max-time 5 https://openapi.koreainvestment.com:9443/

# From your local machine — if this works but container doesn't, it's a Docker network issue
curl -sv --max-time 5 https://openapi.koreainvestment.com:9443/
```

If curl from local works but not from container: check Docker network settings, DNS resolution inside the container (`docker exec the-wealth-backend-1 nslookup openapi.koreainvestment.com`), or firewall rules blocking outbound HTTPS on port 9443.

---

## Related

- [`docs/architecture/kis-integration.md`](../architecture/kis-integration.md) — KIS token lifecycle, TR_IDs, error codes
- [`docs/architecture/auth-flow.md`](../architecture/auth-flow.md) — SSE ticket flow, JWT refresh
- [`docs/runbooks/deploy.md`](./deploy.md) — production deployment troubleshooting
