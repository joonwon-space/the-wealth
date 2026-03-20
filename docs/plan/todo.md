# THE WEALTH — TODO (Future Roadmap)

Long-term backlog. Not urgent but eventually needed.
Current actionable work is in `tasks.md`.

`/discover-tasks` command refreshes this document.

---

## Completed Milestones

<details>
<summary>Milestone 1~9, 10, 11 (partial), 12 (partial incl. SSE hardening), 13-1, 14 (partial), 15-4, 16 (partial incl. commitlint) -- all completed</summary>

### Milestone 1-9: Foundation
- [x] Backend init, DB, Auth, Next.js layout, KIS API, Dashboard, Account sync, UI, Python upgrade, Feature extensions

### Milestone 10: AI Browser Agent
- [x] Playwright MCP, visual QA, fix-ui, e2e-check commands

### Milestone 11 (completed items)
- [x] 11-1: Mobile UX (responsive, card view, PWA, bottom nav, swipe gesture)
- [x] 11-2: Sector allocation chart
- [x] 11-3: Watchlist, real-time price indicator
- [x] 11-4: Stock detail page (`/dashboard/stocks/[ticker]`)
- [x] 11-5: Keyboard shortcuts dialog, Error Boundary, bundle optimization

### Milestone 12 (completed items)
- [x] 12-1: Price history & day change (price_snapshots, daily snapshot scheduler)
- [x] 12-2: SSE real-time prices (30s interval, market hours only, per-user limit, heartbeat, 2h timeout)
- [x] 12-3: Performance optimization (query optimization, Redis cache)
- [x] 12-4: Alert system (CRUD)
- [x] 12-5: API versioning (/api/v1), standardized error responses, openapi-typescript

### Milestone 13-1: Portfolio History
- [x] Portfolio history API + chart

### Milestone 14 (completed items)
- [x] Dockerfile multi-stage build
- [x] Structured logging (structlog)
- [x] CI/CD (GitHub Actions: lint, test, build, E2E, Docker, Dependabot, CodeQL)
- [x] Security headers (HSTS, CSP, X-Frame-Options, etc.)
- [x] Husky + lint-staged

### Milestone 15-4: Data Export
- [x] CSV export (holdings + transactions)

### Milestone 16 (completed items)
- [x] Test coverage 93% (501 tests) — added `.coveragerc` with `core = sysmon` to fix Python 3.12 async coverage tracking; previously reported as 73% due to sys.settrace limitation with asyncio tasks
- [x] Playwright E2E setup
- [x] openapi-typescript type generation
- [x] Short-term improvements (DB indexes, legacy columns, rate limits, ticker validation, pagination cap, soft delete, HttpOnly cookies, Graceful Shutdown)

</details>

---

## Milestone 11: Frontend Enhancement (Remaining)

### 11-2. Analytics Page Enhancement
- [ ] Portfolio performance time-series chart (daily/weekly/monthly)
- [ ] KOSPI200 / S&P500 benchmark overlay (KIS index API `FHKUP03500100`)
- [ ] Dividend income tracking (calendar + yield chart)
- [ ] Investment performance metrics: Sharpe ratio, MDD, CAGR
- [ ] Monthly/annual return heatmap (GitHub contribution chart style)

### 11-3. Dashboard Enhancement
- [ ] Day-change badge on dashboard summary cards
- [ ] 52-week high/low position bar in holdings table
- [ ] Drag-and-drop widget layout (react-grid-layout)

### 11-4. Stock Detail Page Enhancement
- [ ] Fundamental data (market cap, PER, PBR, dividend yield) via KIS master API
- [ ] Moving averages overlay (5/20/60/120 day)
- [ ] Volume analysis chart
- [ ] News/disclosure feed (KIS news API or Naver Finance)
- [ ] My holdings overlay (average purchase price line)

### 11-5. UX Convenience
- [ ] i18n (next-intl, Korean/English)
- [ ] In-app notification center (price alerts, sync results, errors)
- [ ] Onboarding tour (react-joyride)
- [x] TanStack Query adoption (replace manual Axios state management)
  - [x] Install + QueryClientProvider setup
  - [x] Migrate dashboard fetching (`refetchInterval: 30_000`)
  - [x] Migrate portfolio/holdings lists
  - [x] Integrate SSE via `queryClient.setQueryData()`
  - [x] Standardize loading/error/empty state UI
  - [ ] Optimistic updates for add/delete (partial — mutations use setQueryData for immediate cache update)

### 11-7. Frontend Quality
- [x] Bundle size budget — `@next/bundle-analyzer` + CI warning on budget exceed
- [x] Granular error boundaries — per-widget isolation (chart error shouldn't crash entire dashboard)
- [x] SSE reconnection UI — connection status indicator + manual reconnect button
- [x] Non-color indicators — ▲/▼ icons for gain/loss (accessibility)
- [ ] Unified skeleton UI loading states

### 11-6. Next.js 16 Migration
- [x] Migrate `middleware.ts` to `proxy` convention (deprecated in Next.js 16)

---

## Milestone 12: Backend Enhancement (Remaining)

### 12-2. SSE Connection Hardening (Completed)
- [x] Per-user max SSE connection limit (e.g., 3)
- [x] Server heartbeat (15s) + idle connection cleanup
- [x] Max connection duration (e.g., 2 hours)

### 12-3. Performance Optimization
- [ ] Stock search trie structure or Redis ZRANGEBYLEX indexing
- [ ] KIS batch price API exploration
- [ ] ETag/If-None-Match header support for dashboard caching
- [ ] Multi-worker uvicorn (`--workers 2` or gunicorn + uvicorn worker class)
- [ ] APScheduler dedup in multi-worker (Redis distributed lock or scheduler separation)
- [ ] SSE connection management in multi-worker

### 12-4. Alert System — Notification Logic
Alert CRUD exists but no logic to actually notify users when price conditions are met.

- [x] Price condition check in SSE streaming loop
- [ ] In-app notification center (toast + notification list)
- [ ] Email alerts (SendGrid / Resend)
- [ ] Telegram bot alerts
- [x] Dedup — `last_triggered_at` column + cooldown
- [x] Auto-deactivate triggered alerts

### 12-5. API Extension
- [ ] GraphQL layer (Strawberry)
- [ ] Webhook support (Slack, Discord, Zapier)
- [ ] Cursor-based pagination for transactions, sync_logs
- [ ] Bulk operations API (POST /portfolios/{id}/holdings/bulk)

---

## Milestone 13: Data Pipeline & Analysis

### 13-1. External Data Collection
- [ ] KOSPI200 / S&P500 daily index data collection
- [ ] Stock metadata table (sector, industry, market_cap)
- [ ] Dividend data collection (KIS or KRX)
- [ ] Exchange rate data collection (USD/KRW) via Bank of Korea ECOS API

### 13-2. Portfolio Analysis Engine
- [ ] Daily portfolio value snapshot (total + per-stock)
- [ ] TWR (time-weighted return) / MWR (money-weighted return) calculation
- [ ] Risk metrics: volatility, Sharpe ratio, MDD, beta
- [ ] Portfolio correlation analysis
- [ ] Rebalancing suggestions (target vs current allocation)

### 13-3. AI Insights (Future)
- [ ] Claude API integration for portfolio analysis summaries
- [ ] News summarization (RSS + Claude)
- [ ] Trading pattern analysis

### 13-4. DB Stability
- [x] Automated daily pg_dump backup script (`scripts/backup-postgres.sh` + docker-compose cron)
- [x] Retention policy (7 daily + 4 weekly + 3 monthly)
- [x] Recovery procedure documentation (`docs/runbooks/restore.md`)
- [x] Backup failure alerting — `backup-postgres.sh` 실패 시 `sync_logs` 기록 + health endpoint 노출
- [x] Backup 상태 헬스체크 — `/api/v1/health`에 `last_backup_at` 포함 (볼륨 최신 dump mtime 기반)

---

## Milestone 13-5: Operational Stability & Data Integrity

> Newly identified from cross-document analysis ([action plan 2026-03-19](../reviews/the-wealth-action-plan_20260319.md))

### 13-5a. Operational Stability
- [x] Redis failure fallback — in-memory fallback or graceful degradation when Redis is down
- [x] Scheduler failure alerting — alert on consecutive `kis_sync` / `daily_close_snapshot` failures (currently only logged to `sync_logs`)
- [ ] Docker volume monitoring — track `pg_data`, `redis_data` disk usage with threshold alerts
- [ ] TLS certificate renewal check — HTTPS cert expiry monitoring

### 13-5b. Data Integrity
- [x] `price_snapshots` gap detection — health check for missing weekday snapshots
- [x] Holdings quantity reconciliation — detect mismatch between transaction sum and current holdings
- [x] Orphan record cleanup — periodic scan for residual data from deleted portfolios

### 13-5c. KIS API Dependency Reduction
- [x] Adaptive cache TTL — after market close, extend price cache TTL from 300s to 24h
- [x] KIS API health check on startup — auto-switch to cache-only mode on failure
- [ ] Price fetch failure rate tracking — alert when threshold exceeded (e.g., 30%)

---

## Milestone 14: Infrastructure & Observability (Remaining)

> **배포 전략**: 외부 클라우드 서비스 없이 로컬 `docker compose` 운영 기준.
> Vercel, Railway, Fly.io, Supabase, Upstash 등 외부 플랫폼은 로드맵에서 제외.

### 14-2. Monitoring & Observability
- [ ] APM (Sentry) — frontend `@sentry/nextjs` + backend `sentry-sdk[fastapi]` (무료 플랜)
- [ ] Metrics dashboard (API response time, error rate, KIS API calls, Redis hit rate)

### 14-4. Security Enhancement
- [ ] API key rotation automation
- [ ] Security audit log (login attempts, settings changes, data access)
- [ ] 2FA (TOTP, Google Authenticator compatible)

---

## Milestone 15: User Experience & Extension

### 15-1. Multi-broker Support
- [ ] BrokerProvider interface abstraction
- [ ] Connectors for other brokers (Mirae Asset, Kiwoom, NH)

### 15-2. Social & Sharing
- [ ] Portfolio performance sharing (anonymous link, stock name masking)
- [ ] Screenshot sharing (html2canvas or satori)
- [ ] Investment journal (trade reasons, memos)

### 15-3. Mobile App
- [ ] React Native or Capacitor native wrapper
- [ ] Push notifications (FCM)
- [ ] Biometric authentication (Face ID / fingerprint)
- [ ] Widgets (iOS/Android) -- total assets, daily return

### 15-4. Data Export & Tax
- [ ] Excel export (xlsx with formatting)
- [ ] Tax calculator (domestic/overseas capital gains)
- [ ] PDF report generation

---

## Milestone 16: Dev Tools & DX (Remaining)

### 16-1. Claude Code Agent Extension
- [ ] `visual-qa` agent
- [ ] `perf-analyzer` agent (Lighthouse CI + bundle size)
- [ ] `migration-reviewer` agent (Alembic safety check)

### 16-2. Test Infrastructure
- [ ] SSE connection tests (connect/reconnect, off-hours deactivation)
- [ ] Frontend test coverage expansion
  - [x] `usePriceStream` hook tests (connect/reconnect/off-hours)
  - [ ] Key page component tests (dashboard, portfolio list)
  - [x] `lib/format.ts` utility tests
  - [x] `store/auth.ts` Zustand store tests
- [ ] Visual regression testing (Chromatic or Percy)
- [ ] Load testing (Locust or k6)

### 16-3. Code Quality Tools
- [ ] Storybook -- component catalog
- [ ] Turborepo or Nx -- monorepo build caching
- [x] Commitlint -- commit message format validation

---

## Priority Guide

| Priority | Milestone | Reason |
|----------|-----------|--------|
| **P0** | 14-2 (Monitoring & APM) | Silent failures in production |
| ~~**P0**~~ | ~~13-4 (DB Backup)~~ | Completed: daily backup + retention + restore docs + health endpoint |
| ~~**P0**~~ | ~~14-1 (Server resilience)~~ | Completed: restart policies + runbooks |
| ~~**P0**~~ | ~~Test coverage 80%+~~ | Completed: 90% (537 tests), health/internal modules need catch-up |
| **P1** | 16-2 (Frontend test coverage) | Backend 90% vs frontend minimal |
| **P1** | 11-2 (Analytics enhancement) | Differentiation feature |
| **P1** | 12-4 (Alert notification -- in-app/email) | SSE condition check done, no user-visible notification |
| ~~**P1**~~ | ~~11-5 (TanStack Query)~~ | Completed: QueryClientProvider, dashboard/portfolio migration |
| **P2** | 13 (Data pipeline) | Analytics prerequisite |
| **P2** | 14-4 (Security) | Production readiness |
| **P2** | 13-5 (Operational stability remaining) | Docker volume monitoring, TLS cert check |
| **P3** | 15 (Extensions) | Long-term roadmap |
| **P3** | 16 (Dev tools) | DX improvement |
