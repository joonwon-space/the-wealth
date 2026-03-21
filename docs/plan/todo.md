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
- [x] Test coverage 93% (577 tests)
- [x] Playwright E2E setup
- [x] openapi-typescript type generation
- [x] Short-term improvements (DB indexes, legacy columns, rate limits, ticker validation, pagination cap, soft delete, HttpOnly cookies, Graceful Shutdown)

### KIS Resilience (2026-03-21)
- [x] KIS API 장애 시 `RuntimeError` raise (빈 배열 반환 → reconciliation 오삭제 방지)
- [x] Dashboard `kis_status: "ok" | "degraded"` 필드 + 프론트 배너 표시

</details>

---

## P0 — DB 정리

### 0-2. users 테이블 레거시 KIS 컬럼 제거 ✅
`kis_accounts` 테이블로 이관 완료된 컬럼들이 `users`에 잔존.
- [x] Alembic migration: `kis_app_key_enc`, `kis_app_secret_enc`, `kis_account_no`, `kis_acnt_prdt_cd` drop (`c3d4e5f6a7b8_drop_legacy_user_kis_columns.py`)
- [x] `backend/app/models/user.py` 정리 완료 (레거시 컬럼 없음)

---

## Milestone 11: Frontend Enhancement (Remaining)

### 11-2. Analytics Page Enhancement
- [ ] Portfolio performance period filter (1w / 1m / 3m / 6m / 1y / all 탭)
- [ ] KOSPI200 / S&P500 benchmark overlay (KIS index API `FHKUP03500100`)
- [ ] Dividend income tracking (calendar + yield chart)
- [ ] Investment performance metrics: Sharpe ratio, MDD, CAGR (`backend/app/services/metrics.py`)
- [ ] Monthly/annual return heatmap (GitHub contribution chart style)

### 11-3. Dashboard Enhancement
- [ ] 52-week high/low position bar in holdings table
- [ ] Target asset progress widget — `portfolios.target_value` + 달성률 프로그레스 바 (`PATCH /portfolios/{id}`)
- [ ] Drag-and-drop widget layout (react-grid-layout)

### 11-4. Stock Detail Page Enhancement
- [ ] Fundamental data (market cap, PER, PBR, dividend yield) via KIS master API
- [ ] Moving averages overlay (5/20/60/120 day)
- [ ] Volume analysis chart
- [ ] News/disclosure feed (KIS news API or Naver Finance)
- [ ] My holdings overlay (average purchase price horizontal line on candlestick chart)

### 11-5. UX Convenience
- [ ] In-app notification center (price alerts → toast + notification list)
- [ ] Trade memo & investment journal — `transactions.memo` 컬럼 + 인라인 편집

### 11-7. Frontend Quality
- [x] Bundle size budget — `@next/bundle-analyzer` + CI warning on budget exceed
- [x] Granular error boundaries — per-widget isolation
- [x] SSE reconnection UI — connection status indicator + manual reconnect button
- [x] Non-color indicators — ▲/▼ icons for gain/loss (accessibility)
- [ ] Unified skeleton UI loading states

---

## Milestone 12: Backend Enhancement (Remaining)

### 12-3. Performance & Caching
- [ ] ETag / `If-None-Match` support for dashboard endpoint (변경 없으면 304)
- [ ] Stock search trie structure or Redis `ZRANGEBYLEX` indexing
- [ ] KIS batch price API exploration (단일 호출로 여러 종목 조회)

### 12-4. Alert System — Notification Logic
Alert CRUD exists but no logic to actually notify users when price conditions are met.

- [x] Price condition check in SSE streaming loop
- [x] Dedup — `last_triggered_at` column + cooldown
- [x] Auto-deactivate triggered alerts
- [ ] In-app notification center: `notifications` 테이블 + `GET/PATCH /notifications` API
- [ ] Frontend notification bell + unread badge + dropdown panel
- [ ] Email alerts (SendGrid / Resend)

### 12-5. API Extension
- [ ] Cursor-based pagination for transactions, sync_logs
- [ ] Bulk operations API (`POST /portfolios/{id}/holdings/bulk`)

---

## Milestone 13: Data Pipeline & Analysis

### 13-1. External Data Collection
- [ ] KOSPI200 / S&P500 daily index data collection (benchmark 전제 조건)
- [ ] Stock metadata table (sector, industry, market_cap)
- [ ] Dividend data collection (KIS or KRX)

### 13-2. Portfolio Analysis Engine
- [ ] TWR (time-weighted return) / MWR (money-weighted return) calculation
- [ ] Risk metrics: volatility, Sharpe ratio, MDD, beta
- [ ] Portfolio correlation analysis
- [ ] Rebalancing suggestions (target vs current allocation)

### 13-3. AI Insights
- [ ] Claude API integration — portfolio analysis natural language summary
- [ ] News summarization (RSS + Claude)

### 13-4. DB Stability
- [x] Automated daily pg_dump backup
- [x] Retention policy (7 daily + 4 weekly + 3 monthly)
- [x] Recovery procedure documentation
- [x] Backup failure alerting + health endpoint `last_backup_at`

---

## Milestone 13-5: Operational Stability & Data Integrity

### 13-5a. Operational Stability
- [x] Redis failure fallback
- [x] Scheduler failure alerting (consecutive failure tracking)
- [ ] Docker volume disk monitoring — `pg_data`, `redis_data` 사용량 임계값(80%) 경고 + health endpoint `disk_usage` 필드
- [ ] TLS certificate renewal check — HTTPS cert expiry monitoring
- [ ] Price fetch failure rate tracking — threshold(30%) 초과 시 alert

### 13-5b. Data Integrity
- [x] `price_snapshots` gap detection
- [x] Holdings quantity reconciliation
- [x] Orphan record cleanup

### 13-5c. KIS API Dependency Reduction
- [x] Adaptive cache TTL (after-market 24h extension)
- [x] KIS API health check on startup + degraded mode
- [ ] Price fetch failure rate tracking (13-5a와 연계)

---

## Milestone 14: Infrastructure & Observability (Remaining)

### 14-2. Monitoring & Observability
- [x] Sentry 백엔드 통합 — `sentry-sdk[fastapi]` + `SENTRY_DSN` env (완료, 수신 확인됨)
- [x] Sentry 프론트엔드 통합 — `@sentry/nextjs` + Error Boundary `captureException` 연동 (완료)
- [ ] API 응답시간 미들웨어 — `MetricsMiddleware`: `process_time` structlog 기록 + `X-Process-Time` 헤더

### 14-4. Security Enhancement
- [ ] API key rotation automation
- [ ] Security audit log (login attempts, settings changes, data access)
- [ ] 2FA (TOTP, Google Authenticator compatible)

---

## Milestone 15: User Experience & Extension

### 15-2. Portfolio Tools
- [ ] Breakeven visualization — HoldingsTable 미니 게이지 바 (52주 범위 내 현재가 + 평균 매입가 마커)
- [ ] Portfolio performance sharing (anonymous link, stock name masking)
- [ ] Screenshot sharing (html2canvas or satori)

### 15-4. Data Export & Tax
- [ ] Excel export (xlsx with formatting, `openpyxl`)
- [ ] Tax calculator (국내 대주주 양도세, 해외 250만원 공제 후 22%)
- [ ] PDF report generation

---

## Milestone 16: Dev Tools & DX (Remaining)

### 16-2. Test Infrastructure
- [ ] MSW (Mock Service Worker) 설정 — 프론트엔드 테스트 API 모킹 인프라
- [ ] Dashboard page component tests (TanStack Query mock + MSW)
- [ ] Portfolio list/detail page tests
- [ ] HoldingsTable unit tests (sort, PnLBadge color rules, overseas USD display)
- [ ] SSE connection tests (connect/reconnect, off-hours deactivation)
- [ ] Visual regression testing (Chromatic or Percy)
- [ ] Load testing (Locust or k6)

### 16-3. Code Quality Tools
- [ ] Storybook 8 — component catalog (`PnLBadge`, `DayChangeBadge`, `AllocationDonut`, `HoldingsTable`)
- [x] Commitlint — commit message format validation

---

## Priority Guide

| Priority | Item | Reason |
|----------|------|--------|
| ~~**P0**~~ | ~~0-2 (users 레거시 컬럼 제거)~~ | ✅ 완료 |
| ~~**P0**~~ | ~~14-2 (Sentry APM)~~ | ✅ 완료 (백엔드+프론트 모두) |
| **P1** | 16-2 (Frontend 테스트 MSW + 컴포넌트 테스트) | 백엔드 93% 대비 프론트 거의 0% |
| **P1** | 12-4 (알림 센터) | SSE 조건 체크는 됨, 사용자 알림 없음 |
| **P1** | 11-2 (Analytics: 기간 필터 + 지표) | 핵심 차별화 기능 |
| **P1** | 13-5a (Disk monitoring) | 운영 안정성 |
| **P2** | 11-2 (Benchmark overlay) | 13-1 외부 데이터 수집 선행 필요 |
| **P2** | 11-3 (Target asset widget) | 사용자 가치 높음, 구현 간단 |
| **P2** | 11-5 (Trade memo) | DB 컬럼 1개 + UI |
| **P2** | 13-2 (분석 엔진: TWR/MWR, 리스크 지표) | price_snapshots 데이터 누적 전제 |
| **P2** | 15-4 (Excel export) | CSV 이미 있음, xlsx는 추가 가치 |
| **P3** | 13-3 (Claude API 인사이트) | 재미있지만 API 비용 발생 |
| **P3** | 16-3 (Storybook) | DX 개선 |
| **P3** | 15-4 (세금 계산기) | 세법 복잡도 높음 |
