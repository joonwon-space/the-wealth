# THE WEALTH — Tasks

Current work items. Read by `/auto-task` and `/next-task`.
Each item should be completable in a single commit.

---

## Completed (archive)

<details>
<summary>Previously completed items</summary>

- [x] `filelock` 3.19.1 -> 3.25.2 upgrade
- [x] `python-jose` -> `PyJWT` migration
- [x] `passlib` -> `bcrypt` direct usage migration
- [x] `backend/.env.example` CORS_ORIGINS addition
- [x] KIS credential API connection test endpoint + UI
- [x] Milestone 11-1: Mobile UX (all items)
- [x] Milestone 11-2: Analytics page enhancement (all items)
- [x] Milestone 11-3: Holdings table 52-week high/low (all items)
- [x] Milestone 11-3: Watchlist (all items)
- [x] Milestone 11-4: Stock detail page (all items)
- [x] Milestone 11-5: UX convenience features (all items)
- [x] Milestone 12-1: Price history & day change (all items)
- [x] Milestone 12-2: SSE real-time prices (all items)
- [x] Milestone 12-3: Performance optimization (all items)
- [x] Milestone 12-3b: Query optimization (all items)
- [x] Milestone 12-4: Alert system (all items)
- [x] Milestone 12-5: API quality improvement (all items)
- [x] Milestone 13-1: Portfolio history API + chart (all items)
- [x] Milestone 14: Dockerfile multi-stage build
- [x] Milestone 14-2: Backend structured logging (structlog)
- [x] Milestone 14-3: CI/CD Docker build verification
- [x] Milestone 14-3 / 16-3: CI/CD & code quality (all items)
- [x] Milestone 14-4: Security headers (all items)
- [x] Milestone 15-4: Data export - CSV (all items)
- [x] Milestone 16-1: Claude Code agent expansion (all items)
- [x] Milestone 16-2: Test coverage 70%+ (all items)
- [x] Milestone 16-2: Playwright E2E test setup (all items)
- [x] Milestone 16-2b: Test coverage expansion (all items)
- [x] Milestone 16-3: openapi-typescript type generation (all items)
- [x] Short-term improvements: DB indexes, legacy columns, rate limits, ticker validation, pagination cap, soft delete, HttpOnly cookies, Error Boundary, bundle optimization, Graceful Shutdown
- [x] Milestone 10: AI browser agent (all items)
- [x] portfolios.py split - CSV export to portfolio_export.py
- [x] Fix ruff lint errors in test files (10 errors)
- [x] Test coverage 71% -> 93% (add router tests + .coveragerc sysmon fix)
- [x] Milestone 16-3: Commitlint config + Husky hook
- [x] Milestone 12-2: SSE connection hardening (per-user limit, heartbeat, 2h timeout)

</details>

---

## Current work

### Next.js middleware deprecation fix
- [x] Migrate `frontend/src/middleware.ts` from `middleware` to `proxy` convention — Next.js 16 build warns the `middleware` file convention is deprecated

### Test coverage gaps (prices.py 61%)
- [x] Add SSE endpoint tests for `api/prices.py` to bring coverage from 61% to 80%+
- [x] Add missing `api/dashboard.py` tests for uncovered lines (85% -> 90%+)

---

## P0 — Critical (Service Stability)

> Source: [the-wealth-action-plan_20260319.md](../reviews/the-wealth-action-plan_20260319.md)

### Automated DB Backup
PostgreSQL runs on a single server with volume mount only — disk failure = total data loss.

- [x] Daily `pg_dump` script + retention policy (cron in Docker Compose)
- [x] Restore procedure docs
- [ ] External storage integration (S3 / GCS / R2) — requires cloud credentials → see manual-tasks.md
- [ ] Backup failure alerting (email or Telegram) — requires external service → see manual-tasks.md

### Monitoring & APM
No monitoring means scheduler failures and API outages go completely silent.

- [ ] Sentry integration — frontend `@sentry/nextjs` + backend `sentry-sdk[fastapi]` — requires Sentry DSN → see manual-tasks.md
- [ ] Uptime monitoring / alert channels / metrics dashboard — requires external service → see manual-tasks.md

### Single Server Resilience
All services on one server — server down = full outage.

- [ ] Add `restart: unless-stopped` to all services in docker-compose.yml
- [ ] Document managed DB / serverless Redis evaluation (Supabase, Neon, Upstash)

---
