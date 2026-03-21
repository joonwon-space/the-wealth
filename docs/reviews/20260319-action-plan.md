# 🏦 The Wealth — Action Plan

> 📅 Date: 2026-03-19  
> 📊 Based on: Full analysis of architecture/, plan/, reviews/  
> 🎯 Purpose: Project diagnosis + additional task generation

---

## 📋 Project Status

| Area | Status | Detail |
|:-----|:------:|:-------|
| Backend Test Coverage | ✅ 94% | 517 tests, 0 ruff errors |
| API Endpoints | ✅ 46 | 12 routers, `/api/v1` versioned |
| Production Deploy | ✅ Live | joonwon.dev (self-hosted Docker) |
| CI/CD | ✅ 7 workflows | lint, test, build, deploy, CodeQL, E2E, Dependabot |
| Security | ✅ Solid | AES-256-GCM, JWT rotation, IDOR prevention, HttpOnly Cookie |
| Monitoring/APM | ❌ None | structlog only |
| DB Backup | ❌ None | Data loss risk on disk failure |
| Alert Dispatch | ⚠️ Incomplete | CRUD only, no actual push/email |

---

## 🔴 P0 — Critical (Service Stability)

### 1. Automated DB Backup

PostgreSQL runs on a single server with volume mount only — disk failure = **total data loss**.

- [ ] Daily `pg_dump` script (cron or Docker scheduler)
- [ ] External storage (S3 / GCS / R2)
- [ ] Retention policy (7 daily + 4 weekly + 3 monthly)
- [ ] Restore procedure docs + periodic restore test
- [ ] Backup failure alerting (email or Telegram)

### 2. Monitoring & APM

No monitoring means scheduler failures and API outages go **completely silent**.

- [ ] Sentry — frontend `@sentry/nextjs` + backend `sentry-sdk[fastapi]`
- [ ] Uptime monitoring (UptimeRobot or Betterstack)
- [ ] Alert channels (email / Slack / Telegram)
- [ ] Key metrics dashboard
  - KIS API success/failure rate by time
  - Avg response time per endpoint
  - Sync success/failure trends
  - Redis cache hit rate
  - SSE concurrent connections

### 3. Single Server Resilience

All services on one server — server down = full outage.

- [ ] Verify `restart: unless-stopped` in Docker Compose
- [ ] Test auto-recovery on reboot
- [ ] Evaluate managed DB migration (Supabase / Neon)
- [ ] Evaluate serverless Redis (Upstash)

---

## 🟠 P1 — High (UX & Operations Quality)

### 4. Alert System Implementation

Alert CRUD exists but **no logic to actually notify users** when price conditions are met.

- [ ] Price condition check in SSE streaming loop
- [ ] In-app notification center (toast + notification list)
- [ ] Email alerts (SendGrid / Resend)
- [ ] Telegram bot alerts
- [ ] Dedup — `last_triggered_at` column + cooldown
- [ ] Auto-deactivate triggered alerts

### 5. TanStack Query Adoption

Frontend relies on manual Axios state management — code duplication and cache inconsistency.

- [ ] Install + QueryClientProvider setup
- [ ] Migrate dashboard fetching (`refetchInterval: 30_000`)
- [ ] Migrate portfolio/holdings lists
- [ ] Integrate SSE via `queryClient.setQueryData()`
- [ ] Standardize loading/error/empty state UI
- [ ] Optimistic updates for add/delete

### 6. Frontend Test Coverage

Backend 94% vs frontend **minimal**.

- [ ] `usePriceStream` hook tests (connect/reconnect/off-hours)
- [ ] Key page component tests (dashboard, portfolio list)
- [ ] `lib/format.ts` utility tests
- [ ] `store/auth.ts` Zustand store tests
- [ ] E2E core scenarios
  - Register → Login → KIS setup → Sync → Dashboard
  - Add stock → Record trade → Verify P&L
  - Token expiry → Auto-refresh → Retry

### 7. Analytics Enhancement

Basic analytics only — needs differentiation.

- [ ] Benchmark overlay — KOSPI200 / S&P500
- [ ] Performance metrics — Sharpe ratio, MDD, CAGR
- [ ] Dividend tracking — calendar + yield chart
- [ ] Portfolio time-series chart (daily/weekly/monthly toggle)

---

## 🟡 P2 — Medium (Feature Expansion)

### 8. Security Hardening

- [ ] CSP header
- [ ] Security audit log (login attempts, settings changes)
- [ ] 2FA (TOTP, Google Authenticator)
- [ ] API key rotation automation
- [ ] CORS production domain validation

### 9. API Design Improvements

- [ ] `GET /portfolios/{id}` standalone endpoint
- [ ] Cursor-based pagination for transactions, sync_logs
- [ ] Bulk operations — `POST /portfolios/{id}/holdings/bulk`
- [ ] ETag / If-None-Match for dashboard caching
- [ ] Webhook support (Slack, Discord, Zapier)

### 10. Stock Detail Page

- [ ] Fundamentals — market cap, PER, PBR, dividend yield
- [ ] Moving average overlays (5/20/60/120 day)
- [ ] Volume analysis chart
- [ ] News/disclosure feed
- [ ] My holdings overlay (avg purchase price line)

### 11. Data Pipeline

- [ ] KOSPI200 / S&P500 daily index collection
- [ ] Stock metadata table (sector, industry, market_cap)
- [ ] Dividend data collection
- [ ] Exchange rate data (Bank of Korea ECOS API)
- [ ] Daily portfolio value snapshots

### 12. Dashboard UX

- [ ] Day-change badge on summary cards
- [ ] 52-week high/low bar in holdings table
- [ ] Drag-and-drop widget layout (`react-grid-layout`)
- [ ] Unified skeleton UI loading states

### 13. Multi-Worker uvicorn

Single worker — CPU-bound tasks can block the event loop.

- [ ] `--workers 2` or gunicorn + uvicorn worker class
- [ ] APScheduler dedup — Redis distributed lock or scheduler separation
- [ ] SSE connection management in multi-worker

---

## 🟢 P3 — Low (Long-term Roadmap)

### 14. i18n & Accessibility

- [ ] `next-intl` (Korean/English)
- [ ] Non-color indicators — ▲/▼ icons for gain/loss
- [ ] Chart `aria-label` + alt text tables
- [ ] Full keyboard navigation

### 15. Mobile App & PWA

- [ ] React Native or Capacitor wrapper
- [ ] Push notifications (FCM)
- [ ] Biometric auth
- [ ] Widgets (iOS/Android)

### 16. Export Extensions

- [ ] Excel export (xlsx with formatting)
- [ ] Tax calculator (domestic/overseas capital gains)
- [ ] PDF report generation

### 17. Multi-Broker

- [ ] BrokerProvider interface abstraction
- [ ] Mirae Asset, Kiwoom, NH connectors

### 18. Social & Sharing

- [ ] Anonymous portfolio sharing (stock name masking)
- [ ] Screenshot sharing (`html2canvas` / `satori`)
- [ ] Investment journal (trade reasons, memos)

### 19. AI Insights

- [ ] Claude API — portfolio analysis summaries
- [ ] News summarization (RSS + Claude)
- [ ] Trading pattern analysis

### 20. Dev Tools & DX

- [ ] Storybook
- [ ] Turborepo or Nx
- [ ] Visual regression testing (Chromatic / Percy)
- [ ] Load testing (Locust / k6)
- [ ] `visual-qa`, `perf-analyzer`, `migration-reviewer` agents

---

## 🆕 Newly Identified — From Cross-Document Analysis

> Items not in existing plans, discovered through architecture/review analysis.

### A. Operational Stability

- [ ] **Redis failure fallback** — Redis down = JWT validation & price cache fully broken. Needs in-memory fallback or graceful degradation
- [ ] **Scheduler failure alerting** — `kis_sync` and `daily_close_snapshot` failures only logged to `sync_logs`. Need alerts on consecutive failures
- [ ] **Docker volume monitoring** — Track `pg_data`, `redis_data` disk usage with threshold alerts
- [ ] **TLS certificate renewal check** — HTTPS cert expiry monitoring

### B. Data Integrity

- [ ] **price_snapshots gap detection** — Health check for missing weekday snapshots
- [ ] **Holdings quantity reconciliation** — Detect mismatch between transaction sum and current holdings
- [ ] **Orphan record cleanup** — Periodic scan for residual data from deleted portfolios

### C. KIS API Dependency Reduction

- [ ] **Adaptive cache TTL** — After market close, extend price cache TTL from 300s → 24h
- [ ] **KIS API health check on startup** — Auto-switch to cache-only mode on failure
- [ ] **Price fetch failure rate tracking** — Alert when threshold exceeded (e.g., 30%)

### D. Frontend Quality

- [ ] **Lighthouse CI** — Track performance scores per PR
- [ ] **Bundle size budget** — `@next/bundle-analyzer` + CI warning on budget exceed
- [ ] **Granular error boundaries** — Per-widget isolation (chart error shouldn't crash entire dashboard)
- [ ] **SSE reconnection UI** — Connection status indicator + manual reconnect button

### E. Deployment Pipeline

- [ ] **PR preview deploys** — Vercel Preview or self-hosted staging
- [ ] **Semantic release automation** — semantic-release + auto CHANGELOG
- [ ] **Container registry push** — Tag production builds to GHCR/DockerHub for easy rollback
- [ ] **Blue-Green or rolling deploy** — Current `docker compose up -d` may cause downtime

---

## 📊 Priority Matrix

```
          High Impact
               │
    P0 Backup  │  P0 Monitoring
    P0 Resil.  │  P1 Alerts
               │  P1 Analytics
   ────────────┼──────────────
               │  P1 TanStack Query
    P2 Security│  P1 FE Tests
    P3 i18n    │  P2 API Design
    P3 AI      │  P2 Data Pipeline
               │
          Low Impact
  High Effort ◄──────► Low Effort
```

---

## ✅ Recently Completed

- ✅ Next.js 16 middleware → proxy migration
- ✅ Test coverage 71% → 94% (517 tests)
- ✅ SSE hardening (per-user limit, heartbeat, 2h timeout)
- ✅ HttpOnly Cookie auth (XSS defense)
- ✅ Standardized error response envelope
- ✅ Commitlint + Husky
- ✅ Overseas stock USD display fix
- ✅ Graceful shutdown
- ✅ 7 CI/CD workflows

---

*Generated from comprehensive analysis of 11 documents across architecture/, plan/, and reviews/.*
