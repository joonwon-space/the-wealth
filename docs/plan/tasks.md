# THE WEALTH -- Tasks

Current work items. Read by `/auto-task` and `/next-task`.
Each item should be completable in a single commit.

---

## Sprint 14 — KIS Rate Limiting (2026-04-08)

### RL-002. Settings: KIS rate limit config
- [x] Add `KIS_RATE_LIMIT_PER_SEC: float = 5.0`, `KIS_RATE_LIMIT_BURST: int = 20`, `KIS_MOCK_MODE: bool = False` to `backend/app/core/config.py` Settings class — controls token bucket behavior without code changes

### RL-001. Token bucket rate limiter module
- [x] Create `backend/app/services/kis_rate_limiter.py` — `KisRateLimiter` class (asyncio-safe token bucket: `_consume()`, `acquire()`, `available_tokens()`); module-level `_limiter` singleton; `acquire()` helper; `get_timeout_counter()` observability; P95 slow-acquire warning log

### RL-006. Unit tests for token bucket
- [x] Create `backend/tests/test_kis_rate_limiter.py` — TDD: tests written first (RED), then implementation (GREEN); covers: initial tokens, burst, refill, cap, wait proportionality, mock mode, async acquire, timeout raises, global acquire helper

### RL-007. Integration test — burst of 20 with httpx mock
- [x] Integration tests in `test_kis_rate_limiter.py` (class `TestRateLimiterIntegration`): burst-20 concurrent gather, 20 mock KIS calls through rate limiter, timeout counter increment, P95 hint log

### RL-003. Wrap kis_price.py call sites
- [x] Add `await _rate_limit_acquire()` before each `client.get()` call in `backend/app/services/kis_price.py` — `fetch_domestic_price`, `fetch_overseas_price`, `fetch_domestic_daily_ohlcv`, `fetch_overseas_price_detail` (primary + 52w fallback)

### RL-004. Wrap price_snapshot.py call sites
- [x] Add `await _rate_limit_acquire()` before the KIS `client.get()` call in `backend/app/services/price_snapshot.py` `fetch_domestic_price_detail`

### RL-005. Observability logging
- [x] Included in `kis_rate_limiter.py`: acquire-timeout counter (`_timeout_counter` + lock), P95 hint warning log when wait >= 500ms, cumulative timeout count in warning message

### RL-008. Promote P1 detail-cache fallback to todo.md
- [x] Add `OverseasPriceDetail JSON cache fallback` item to `docs/plan/todo.md` Milestone 13-5c — deferred from this sprint; includes cache key, TTL, serialization plan

---

## Sprint 13 — Code Quality: Large File Splits Round 2 (2026-04-08)

### 23-1a. journal/page.tsx Split (TD-002)
- [x] Extract `JournalFilters.tsx` component from `frontend/src/app/dashboard/journal/page.tsx` — move filter state + filter controls UI (date pickers, tag selector, search input) into new file `frontend/src/app/dashboard/journal/JournalFilters.tsx`; export `JournalFiltersProps` interface; update imports in page.tsx

### 23-1b. journal/page.tsx Split — hook + timeline (TD-002)
- [x] Extract `useJournalData.ts` custom hook from `frontend/src/app/dashboard/journal/page.tsx` — move useQuery calls (transactions, portfolio list), derived state (filteredTxns), and filter state into `frontend/src/app/dashboard/journal/useJournalData.ts`; extract `JournalTimeline.tsx` for the timeline list render; target page.tsx ≤280L

### 23-1c. HoldingsSection.tsx Split — inline edit hook (TD-003)
- [x] Extract `useHoldingsInlineEdit.ts` custom hook from `frontend/src/app/dashboard/portfolios/[id]/HoldingsSection.tsx` — move inline-edit state (editingId, editQty, editPrice, handlers: startEdit, cancelEdit, saveEdit) and the mutation logic into `frontend/src/app/dashboard/portfolios/[id]/useHoldingsInlineEdit.ts`; update HoldingsSection.tsx imports; target HoldingsSection.tsx ≤380L

### 23-1d. HoldingsSection.tsx Split — table row component (TD-003)
- [x] Extract `HoldingsTableRow.tsx` component from `frontend/src/app/dashboard/portfolios/[id]/HoldingsSection.tsx` — move the per-row JSX (cells: ticker, name, qty inline-edit, avg price inline-edit, current price, PnL badge, 52-week bar, actions) into `frontend/src/app/dashboard/portfolios/[id]/HoldingsTableRow.tsx`; update HoldingsSection.tsx imports; target HoldingsSection.tsx ≤300L

### 23-2a. scheduler.py Split — market jobs (TD-004)
- [x] Split `backend/app/services/scheduler.py` (526L) — extract all market-data jobs (collect_price_snapshots, collect_benchmark, collect_exchange_rate) into `backend/app/services/scheduler_market_jobs.py`; each function takes `session_factory` param; update imports in scheduler.py

### 23-2b. scheduler.py Split — portfolio + ops jobs (TD-004)
- [x] Extract portfolio jobs (sync_portfolio_holdings) and ops jobs (run_health_checks, check_disk_usage, check_price_gaps) from `backend/app/services/scheduler.py` into `backend/app/services/scheduler_portfolio_jobs.py` and `backend/app/services/scheduler_ops_jobs.py`; reduce scheduler.py to ≤150L orchestrator-only; add pytest unit test verifying all job ids still register

### 23-2c. kis_price.py Split — extract kis_fx.py (TD-007)
- [x] Extract USD/KRW FX logic (~160L) from `backend/app/services/kis_price.py` into `backend/app/services/kis_fx.py` — move `get_usd_krw_rate`, `collect_exchange_rate_snapshot`, and related helpers; update all import sites; add/move existing tests to cover kis_fx module; target kis_price.py ≤360L

---

## Sprint 12 — Security Quick Wins + UX Polish (2026-04-07)

### Rate Limit Gaps (SEC-001)
- [x] Add `@limiter.limit("60/minute")` to all 6 endpoints in `backend/app/api/portfolio_transactions.py` — list_transactions, list_transactions_paginated, create transaction, delete transaction, patch transaction, list_kis_transactions; consistent with project-wide rate-limiting policy

### Holdings GET Rate Limits (SEC-004)
- [x] Add `@limiter.limit("30/minute")` to `GET /{portfolio_id}/holdings` and `GET /{portfolio_id}/holdings/with-prices` in `backend/app/api/portfolio_holdings.py` — the with-prices endpoint calls KIS API and is particularly vulnerable

### Vite CVE Patch (TD-001)
- [x] Upgrade vite in `frontend/` to fix HIGH severity CVE GHSA-4w7w-66w2-5vf9 (path traversal in .map file handling, affects >=8.0.0 <=8.0.4): `cd frontend && npm update vite`; verify `npm audit` shows 0 vulnerabilities after upgrade

### Journal Empty State (UX-001)
- [x] Add empty state to `frontend/src/app/dashboard/journal/page.tsx` — when filteredTxns.length === 0 but transactions.length > 0, render a message '필터 조건에 맞는 거래가 없습니다' with a Reset 버튼 that clears all filters; reuse existing EmptyState or create inline

### Analytics Metrics Null Feedback (UX-002)
- [x] Add informational banner to `frontend/src/app/dashboard/analytics/MetricsSection.tsx` — when the API returns null for all metrics (Sharpe/MDD/CAGR), show '포트폴리오 히스토리가 부족합니다. 지표는 데이터 축적 후 표시됩니다.' to explain why values are missing

### Benchmark Period Sync (UX-005)
- [x] Fix `frontend/src/app/dashboard/analytics/HistorySection.tsx` — pass the active period filter's from/to dates to the benchmark overlay useQuery params so KOSPI200/S&P500 data aligns with the selected portfolio history window

### AccountSection staleTime (TD-006)
- [x] Add `staleTime: 60_000` to the userMe `useQuery` in `frontend/src/app/dashboard/settings/AccountSection.tsx` line 37 — matches staleTime policy already applied to other settings page queries

### todo.md Stale Completions (TD-005)
- [x] Mark completed Sprint 10/11 items as `[x]` in `docs/plan/todo.md` Milestone 20: kis_order.py split (20-1), DashboardPortfolioList (20-1), OrderDialog split (20-1), benchmark collection (20-2), SMA overlay (20-3) — all completed in git commits f8c9d60 and c37bc75

---

## Sprint 11 — Benchmark Read API + Moving Averages + Code Quality (2026-04-07)

### Benchmark Read Endpoint (BM-001)
- [x] Add `GET /analytics/benchmark` endpoint in `backend/app/api/analytics.py` — query `index_snapshots` table, accept `?index_code=KOSPI200&from=YYYY-MM-DD&to=YYYY-MM-DD`, return `[{date, close_price}]` list; add rate-limit 30/minute

### Benchmark Frontend Overlay (BM-002)
- [x] Add benchmark overlay toggle to `frontend/src/app/dashboard/analytics/page.tsx` — fetch `/analytics/benchmark?index_code=KOSPI200`, plot as a secondary line on the portfolio history Recharts chart; show toggle button (KOSPI200 / S&P500 / off)

### Shared Error Fallback Component (CQ-001)
- [x] Extract `WidgetErrorFallback` component from inline JSX in `frontend/src/app/dashboard/analytics/page.tsx` and `frontend/src/app/dashboard/page.tsx` into `frontend/src/components/WidgetErrorFallback.tsx`; update all usages

### Fix _upsert_snapshot Session Anti-Pattern (CQ-002)
- [x] Refactor `_upsert_snapshot` in `backend/app/services/kis_benchmark.py` — replace bare `AsyncSessionLocal()` context manager (session not injected) with a proper `async with AsyncSessionLocal() as session:` block that receives the session as a parameter where the caller passes it; ensure session commit/rollback is handled correctly

### Shrink analytics/page.tsx (CQ-003)
- [x] Split `frontend/src/app/dashboard/analytics/page.tsx` (457L) — extract `BenchmarkChart.tsx`, `PortfolioMetricsCards.tsx` helper components; target main file ≤ 280 lines

### Backend SMA Endpoint (MA-001)
- [x] Add `GET /analytics/stocks/{ticker}/sma` endpoint in `backend/app/api/analytics.py` — accept `?period=20&from=YYYY-MM-DD&to=YYYY-MM-DD`, compute SMA over `price_history` snapshots stored in DB, return `[{date, sma}]`; add rate-limit 30/minute; add unit tests in `backend/tests/test_analytics_sma.py`

### Frontend Moving Average Overlay (MA-002)
- [x] Add SMA overlay to stock detail chart in `frontend/src/app/dashboard/portfolios/[id]/` — fetch `/analytics/stocks/{ticker}/sma?period=20`, render as dashed line on the Recharts price chart; add period selector (20 / 60 / 120 days)

---

## Bug Fix: Sprint 10 Test Regressions — 21 Failing Tests (2026-04-07)

- [x] Correct mock patch paths in `test_kis_order.py`: patch `kis_token.get_kis_access_token` (source module) and `kis_order_place._cache` (rate-limit location) — test mock was targeting old paths that became re-export shims after file split
- [x] Correct datetime patch path in `test_orders.py`: patch `kis_order_place.datetime` (correct module after split)
- [x] Update scheduler job count assertion in `test_scheduler.py`: assert 7 jobs (not 8), verify `collect_benchmark` job id — main had wrong count for wrong architecture
- [x] Remove unused `sqlalchemy.text` import from `kis_benchmark.py` (ruff F401)
- [x] Verify 803 tests pass / 0 fail (up from 782/21 on main)

---

## Sprint 10 — Code Quality + Benchmark Foundation (2026-04-06)

### Quick Wins (S effort, high impact)

- [x] Add `staleTime: 60_000` to portfolio list useQuery in `frontend/src/app/dashboard/portfolios/page.tsx:191` — PERF-002/UX-005: unnecessary re-fetches on window focus
- [x] Add `@limiter.limit("10/minute")` to `get_orderable` (L270), `list_pending_orders` (L306), `settle_orders_endpoint` (L396), `get_portfolio_cash_balance` (L423) in `backend/app/api/orders.py` — SEC-001/TD-006: 4 order endpoints calling KIS API without rate limits
- [x] Add `aria-label` to inline quantity/price edit inputs in `frontend/src/app/dashboard/portfolios/[id]/HoldingsSection.tsx:441,459` — UX-002: screen reader accessibility

### Large File Splits (M effort, high impact)

- [x] Complete `backend/app/services/kis_order.py` (780L) split — move domestic logic into `kis_domestic_order.py`, overseas into `kis_overseas_order.py`, query/cancel into `kis_order_query.py`, reduce original to shim/remove — TD-001 + PROD-002: split files exist but original unreduced
- [x] Split `frontend/src/components/OrderDialog.tsx` (605L) into `DomesticOrderForm.tsx` + `OverseasOrderForm.tsx` + `useOrderSubmit.ts` — TD-002 + PROD-002
- [x] Complete `frontend/src/app/dashboard/page.tsx` (415L) split — DashboardMetrics.tsx already exists; extract remaining portfolio list section into `DashboardPortfolioList.tsx` with its own ErrorBoundary — TD-003: partial split done in Sprint 9

### Benchmark Foundation (L effort, high user value)

- [x] Create `index_snapshots` Alembic migration (`index_code`, `index_name`, `date`, `close_price`) for KOSPI200 + S&P500 — UX-001 + PROD-001: prerequisite for benchmark overlay
- [x] Add KOSPI200 daily snapshot scheduler task to `backend/app/services/scheduler.py` using KIS `FHKUP03500100` — UX-001 + PROD-001
- [x] Add S&P500 daily snapshot scheduler task to `backend/app/services/scheduler.py` using KIS `FHKST03030100` — UX-001 + PROD-001 (해외 지수)

---

## Bug Fix: test_order_settlement.py 2 failing tests (2026-04-04)

- [x] Add `test_session_factory` async fixture to `backend/tests/conftest.py` that creates an `async_sessionmaker` bound to the `TEST_DB_URL` NullPool engine (no data cleanup)
- [x] Replace `AsyncSessionLocal()` in `test_settle_fully_filled_order` with `test_session_factory()`
- [x] Replace `AsyncSessionLocal()` in `test_settle_partial_fill` with `test_session_factory()`
- [x] Verify both failing tests pass and coverage for `order_settlement.py` improves above 23% (75% achieved)

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
- [x] Next.js middleware deprecation fix
- [x] Test coverage gaps (prices.py 61%, dashboard.py 85%)
- [x] P0 Automated DB Backup: daily pg_dump script + retention policy
- [x] P0 Single Server Resilience: restart policy + managed DB/Redis docs
- [x] Milestone 12-4: Alert Notification Logic (last_triggered_at, SSE integration, PATCH endpoint)
- [x] Milestone 16-2: Frontend Test Coverage (format.ts, auth store, usePriceStream)
- [x] Milestone 13-5c: Adaptive Cache TTL
- [x] Milestone 13-5b: Data Integrity Health Checks
- [x] Milestone 11-5: TanStack Query Adoption (all items)
- [x] Milestone 13-5b: Holdings quantity reconciliation endpoint
- [x] Milestone 13-5a: Redis failure fallback
- [x] Milestone 11-7: Frontend Quality (PnLBadge icons, ErrorBoundary, SSE status, bundle analyzer)
- [x] Milestone 13-5a: Scheduler Alerting (consecutive failure tracking)
- [x] Milestone 13-5b: Orphan Record Cleanup endpoint
- [x] Milestone 13-5c: KIS API Health Check on startup
- [x] Fix: 해외주식 관련 버그 수정 (52주 범위, 종목명, 환율, CAGR, 섹터배분)
- [x] Fix: MetricCard 툴팁 fixed 포지션
- [x] Visual QA bug fixes: accessibility, tablet layout, SSE, CSP
- [x] DB 백업 완성: restore 문서, sync_logs 기록, health last_backup_at
- [x] Fix: 알림 벨 버튼 가리는 문제 (데스크탑 md:pr-6 -> md:pr-16)
- [x] Fix: 포트폴리오 총 평가금액에 해외주식 미포함 (`cash-balance` 국내+해외 합산)
- [x] Fix: 설정 실계좌 조회 총 평가/주식 평가에 해외주식 미반영 (output2 방어 처리 + fallback)
- [x] Fix: 설정 실계좌 조회 종목 테이블에 "총 금액" 컬럼 추가 및 내림차순 정렬
- [x] All Trading Feature items (Step 1~8)
- [x] All UI Upgrade Phase 1~5 items
- [x] 브랜드 컬러 시스템 적용 (#1e90ff 블루 + #00ff00 그린)
- [x] 계정 정보 변경 기능 (이름/이메일/비밀번호 변경, 회원 탈퇴)
- [x] Milestone 11-3: Target Asset Progress Widget
- [x] Milestone 11-2: Analytics API period param + 프론트 연동
- [x] Milestone 12-5: 트랜잭션/sync_logs 커서 기반 페이지네이션
- [x] P0 Test coverage recovery (health, internal, backup_health)
- [x] P1 npm 의존성 보안/업데이트 (flatted 취약점 + 마이너 업데이트)
- [x] P1 16-2: Frontend 테스트 인프라 (MSW + HoldingsTable)
- [x] P1 12-4: 알림 센터 (notifications 테이블 + 벨 + 배지)
- [x] P2 14-2: MetricsMiddleware
- [x] P2 11-5: 거래 메모 (Trade Memo)
- [x] Milestone 11-2: Analytics 1W period + 브레이크이븐 마커
- [x] Milestone 12-5: sync_logs 커서 기반 페이지네이션
- [x] feat: 로깅 시스템 개선 (RotatingFileHandler, Dozzle, Sentry DSN env 변수화)
- [x] fix: 국내 주식 주문 버그 4건 (Decimal 타입, 지정가 검증, SELL 수량 검증, 에러 메시지)
- [x] P1 -- 운영 안정성: 디스크 사용량 모니터링 (18-3)
- [x] P1 -- 환율 히스토리 저장 (17-2)
- [x] P2 -- 포트폴리오 비교 차트 (17-1)
- [x] P2 -- 거래 태그 시스템 (17-3)
- [x] P1 -- Excel 내보내기 (15-4 / 19-3)
- [x] P1 -- Bulk Holdings API (12-5)
- [x] P1 -- 투자 일지 페이지 (17-3)
- [x] P0 -- 테스트 인프라 수정 (일괄 실행 시 294건 ERROR)
- [x] P0 -- 중복 파일 정리
- [x] P1 -- npm 취약점 해결
- [x] P1 -- Trading Feature 테스트 커버리지 (27% -> 80%+) (all items)
- [x] P1 -- 매수/매도 UX 개선 (Before/After 경험) (all items)
- [x] P2 -- 저커버리지 라우터 테스트 보강 (all items)
- [x] Team analysis sprint 2026-04-02: GZip, is_domestic 통합, cache fix, DB 인덱스, AlertDialog, compare empty state, rate limiting, CORS, localStorage 방어, Sentry env, chart skeleton (all items)
- [x] Milestone 17 complete: 환율 분석 (17-2), 투자 일지 (17-3), 포트폴리오 비교 (17-1)

</details>

---

## Current work

### P0 -- Sentry KIS 자격증명 유출 방지 [team-analysis: SEC-001]

- [x] **security: Sentry before_send 훅으로 KIS 헤더 스크러빙**
  - `backend/app/main.py` — `sentry_sdk.init()`에 `before_send` 콜백 추가
  - `appkey`, `appsecret`, `authorization` 헤더 값을 `[Filtered]`로 대체
  - `kis_order.py`, `kis_token.py` — `httpx.HTTPStatusError` catch 후 헤더 없는 `RuntimeError` re-raise
  - 파일: `backend/app/main.py`, `backend/app/services/kis_order.py`, `backend/app/services/kis_token.py`

### P0 -- get_prev_close 무제한 쿼리 수정 [team-analysis: PERF-001]

- [x] **perf: price_snapshot.py — DISTINCT ON (ticker) 쿼리로 교체**
  - `backend/app/services/price_snapshot.py:171-189` — 전체 rows fetch + Python dedup 제거
  - `DISTINCT ON (ticker) ORDER BY snapshot_date DESC` PostgreSQL 쿼리로 교체
  - 20종목 2년 데이터 기준 14,600행 -> 20행 전송, 50ms -> 5ms 예상
  - 파일: `backend/app/services/price_snapshot.py`

### P0 -- bcrypt DoS 방어: 비밀번호 max_length 추가 [team-analysis: SEC-002]

- [x] **security: 비밀번호 필드 max_length=128 제한**
  - `backend/app/schemas/auth.py` — `RegisterRequest.password`, `LoginRequest.password` max_length=128
  - `backend/app/schemas/user.py` — `ChangePasswordRequest`, `DeleteAccountRequest` max_length=128
  - bcrypt 72바이트 truncation 고려, Pydantic validation 단계에서 차단
  - 파일: `backend/app/schemas/auth.py`, `backend/app/schemas/user.py`

### P0 -- cryptography 패키지 보안 업데이트 [team-analysis: TD-005]

- [x] **chore: cryptography 46.0.5 -> 46.0.6 패치 적용**
  - AES-256 KIS 자격증명 암호화 경로의 보안 패치 적용
  - 파일: `backend/requirements.txt`

### P1 -- fx-gain-loss 엔드포인트 캐시 추가 [team-analysis: PERF-002]

- [x] **perf: analytics.py — fx-gain-loss Redis 캐시 적용**
  - `backend/app/api/analytics.py` — `cache_key` guard + `setex` 호출 추가
  - 3 DB 쿼리 + O(N*M) bisect 연산 → 캐시 hit 시 2ms 이내
  - 파일: `backend/app/api/analytics.py`

### P1 -- metrics 엔드포인트 해외종목 라우팅 수정 [team-analysis: PERF-003]

- [x] **fix: analytics.py — 해외 ticker에 국내 가격 API 호출 방지**
  - `backend/app/api/analytics.py` — ticker 목록을 국내/해외 분류 후 각 API 라우팅
  - 해외 ticker → `fetch_overseas_price_detail` 사용
  - 파일: `backend/app/api/analytics.py`

### P1 -- SSE 활성 시 대시보드 폴링 비활성화 [team-analysis: PERF-004]

- [x] **perf: dashboard/page.tsx — SSE 연결 시 refetchInterval 비활성화**
  - `frontend/src/app/dashboard/page.tsx` — SSE 연결 상태에 따라 `refetchInterval` 토글
  - SSE 활성: `refetchInterval: false`, SSE 비활성: `refetchInterval: REFRESH_INTERVAL_MS`
  - 파일: `frontend/src/app/dashboard/page.tsx`

### P1 -- 포트폴리오 상세 mutation onError 핸들러 추가 [team-analysis: UX-001]

- [x] **fix: portfolios/[id]/page.tsx — 7개 mutation에 onError toast 추가**
  - `frontend/src/app/dashboard/portfolios/[id]/page.tsx` — addHolding, editHolding, deleteHolding, addTxn, deleteTxn, updateMemo, updateTarget mutation에 onError 추가
  - 각 mutation 실패 시 `toast.error()` 한국어 메시지 표시
  - 파일: `frontend/src/app/dashboard/portfolios/[id]/page.tsx`

### P1 -- Redis 커넥션 풀 공유 [team-analysis: PERF-005 / TD-001]

- [x] **perf: redis_cache.py — 모듈 레벨 ConnectionPool 싱글턴으로 교체**
  - `backend/app/core/redis_cache.py` — `aioredis.ConnectionPool.from_url()` 모듈 레벨 생성 + `get_redis_client()` 컨텍스트 매니저 노출
  - 모든 `aioredis.from_url()` 호출을 공유 풀 기반으로 교체
  - `backend/app/core/security.py`, `backend/app/api/dashboard.py`, `backend/app/services/stock_search.py` 에도 동일 패턴 적용
  - 파일: `backend/app/core/redis_cache.py`, `backend/app/core/security.py`, `backend/app/api/dashboard.py`, `backend/app/services/stock_search.py`

### P1 -- 포트폴리오 목록 rename/delete mutation onError 추가 [team-analysis: UX-004]

- [x] **fix: portfolios/page.tsx — renameMutation, deleteMutation, reorderMutation onError 추가**
  - `frontend/src/app/dashboard/portfolios/page.tsx` — renameMutation/deleteMutation에 `toast.error()` 추가
  - reorderMutation — `onError`에서 `queryClient.setQueryData` rollback + toast
  - 파일: `frontend/src/app/dashboard/portfolios/page.tsx`

### P1 -- CSP unsafe-eval 프로덕션 제거 [team-analysis: SEC-004]

- [x] **security: next.config.ts — 프로덕션 CSP에서 unsafe-eval 제거**
  - `frontend/next.config.ts` — `process.env.NODE_ENV === 'development'` 분기로 unsafe-eval 제한
  - 개발 환경만 Next.js HMR을 위한 unsafe-eval 허용
  - 파일: `frontend/next.config.ts`

### P1 -- TransactionMemoUpdate tags 필드 길이 제약 추가 [team-analysis: SEC-006]

- [x] **security: portfolio.py schema — tags list 항목 수 + 개별 길이 제한**
  - `backend/app/schemas/portfolio.py` — `tags: Optional[list[Annotated[str, Field(max_length=50)]]] = Field(None, max_length=20)`
  - 최대 20개, 개당 최대 50자 제한
  - 파일: `backend/app/schemas/portfolio.py`

### P2 -- analytics/dashboard summary 쿼리 키 통일 [team-analysis: PERF-006]

- [x] **perf: analytics/page.tsx — dashboard summary 쿼리 키 상수화**
  - `frontend/src/app/dashboard/analytics/page.tsx` — 쿼리 키를 `['dashboard', 'summary']`로 통일 (dashboard/page.tsx와 일치)
  - 대시보드 → 분석 페이지 이동 시 중복 요청 제거
  - 파일: `frontend/src/app/dashboard/analytics/page.tsx`

### P2 -- analytics 테이블 키보드 접근성 추가 [team-analysis: UX-006]

- [x] **a11y: analytics/page.tsx — 종목 선택 row에 tabIndex + onKeyDown 추가**
  - `frontend/src/app/dashboard/analytics/page.tsx` — 모바일 카드 div를 button으로 교체, 데스크탑 tr에 `tabIndex={0}` + Enter/Space onKeyDown 추가
  - 파일: `frontend/src/app/dashboard/analytics/page.tsx`

### P2 -- 포트폴리오 상세 인라인 삭제 확인창 AlertDialog 교체 [team-analysis: UX-007]

- [x] **ux: portfolios/[id]/page.tsx — 인라인 fixed 오버레이를 shadcn AlertDialog로 교체**
  - `frontend/src/app/dashboard/portfolios/[id]/page.tsx` — 보유종목/거래내역 삭제 확인 raw div 오버레이 제거
  - shadcn AlertDialog 패턴으로 통일 (role=alertdialog, focus trap 자동 처리)
  - 파일: `frontend/src/app/dashboard/portfolios/[id]/page.tsx`

---

## Sprint 4 work (team-analysis 2026-04-03)

### P0 -- SQLAlchemy pool_recycle 추가 [team-analysis: TD-004]

- [x] **fix: session.py — pool_recycle=1800 추가**
  - `backend/app/db/session.py` — `create_async_engine`에 `pool_recycle=1800, pool_pre_ping=True` 추가
  - Neon 전환(Milestone 22) 전에 필수, 야간 유휴 연결 에러 방지
  - 파일: `backend/app/db/session.py`

### P0 -- Refresh token Redis 키 포맷 변경 [team-analysis: SEC-001]

- [x] **security: security.py — refresh token 키를 refresh:{user_id}:{jti} 포맷으로 변경**
  - `backend/app/core/security.py` — `store_refresh_jti`, `verify_and_consume_refresh_jti`, `revoke_all_refresh_tokens_for_user` 키 포맷 변경
  - 기존 `refresh:{jti}` → `refresh:{user_id}:{jti}` (O(N) 전체 스캔 → O(1) 사용자별 조회)
  - Redis 값 JSON으로 확장: `{"user_id": ..., "created_at": ...}` (세션 관리 UI 준비)
  - 파일: `backend/app/core/security.py`

### P0 -- pip-audit CI 추가 [team-analysis: SEC-007]

- [x] **chore: GitHub Actions — backend CI에 pip-audit 추가**
  - `.github/workflows/` — backend CI job에 `pip install pip-audit && pip-audit -r requirements.txt --fail-on-vuln` 단계 추가
  - Python CVE 자동 감지 (cryptography 취약점 수동 발견 재발 방지)
  - 파일: `.github/workflows/backend-ci.yml` (또는 기존 CI 파일)

### P0 -- 보안 감사 로그 [team-analysis: SEC-003]

- [x] **feat: 보안 감사 로그 테이블 + 서비스 + 엔드포인트**
  - `backend/app/models/security_audit_log.py` — `security_audit_logs` 테이블 (user_id, action enum, ip_address, user_agent, meta JSONB, created_at)
  - Alembic 마이그레이션 생성
  - `backend/app/services/audit_service.py` — `log_event(db, user_id, action, request, meta)` 비동기 함수
  - 기록 대상: 로그인 성공/실패, 로그아웃, KIS 자격증명 등록/삭제, 비밀번호 변경
  - `GET /users/me/security-logs` 엔드포인트 (최근 50건)
  - 파일: `backend/app/models/security_audit_log.py`, `backend/app/services/audit_service.py`, `backend/app/api/users.py`, `backend/app/api/auth.py`

### P1 -- stocks.py _is_domestic() 제거 [team-analysis: TD-001]

- [x] **fix: stocks.py — 로컬 _is_domestic() 삭제 후 공유 함수 임포트**
  - `backend/app/api/stocks.py` — 로컬 `_is_domestic()` 삭제
  - 공유 `is_domestic` 함수 임포트 (app.services.kis_price 또는 공유 위치)
  - 파일: `backend/app/api/stocks.py`

### P1 -- forward_fill_rates fx_utils.py 추출 [team-analysis: TD-006]

- [x] **refactor: forward_fill_rates() → fx_utils.py**
  - `backend/app/services/fx_utils.py` — `forward_fill_rates(snapshots, dates) -> dict` 함수 생성
  - `backend/app/api/analytics.py`, `backend/app/services/scheduler.py` 에서 임포트로 교체
  - 파일: `backend/app/services/fx_utils.py`, `backend/app/api/analytics.py`, `backend/app/services/scheduler.py`

### P1 -- PortfolioHistoryChart any[] 타입 수정 [team-analysis: TD-007]

- [x] **fix: PortfolioHistoryChart.tsx — payload any[] 타입 제거**
  - `frontend/src/components/PortfolioHistoryChart.tsx` — `TooltipProps<number, string>` 사용
  - `as any[]` 캐스트 제거
  - 파일: `frontend/src/components/PortfolioHistoryChart.tsx`

### P1 -- analytics metrics 1Y 날짜 커트오프 [team-analysis: PERF-003]

- [x] **fix: analytics.py — price_snapshots 1Y 날짜 범위 제한**
  - `backend/app/api/analytics.py` — price_snapshots 쿼리에 `WHERE snapshot_date >= NOW() - INTERVAL '1 year'` 추가
  - 기간 파라미터 연동: 선택된 period에 맞는 날짜 범위 적용
  - 파일: `backend/app/api/analytics.py`

### P1 -- 투자 일지 BUY/SELL 배지 아이콘 추가 [team-analysis: UX-003]

- [x] **fix: journal/page.tsx — BUY/SELL 배지 텍스트+아이콘**
  - `frontend/src/app/dashboard/journal/page.tsx` — 컬러만 의존하는 배지를 텍스트+아이콘으로 교체
  - BUY: ▲ 아이콘 + 'BUY' 텍스트, SELL: ▼ 아이콘 + 'SELL' 텍스트 (WCAG 1.4.1)
  - 파일: `frontend/src/app/dashboard/journal/page.tsx`

### P1 -- 보유종목 추가 폼 인라인 유효성 검사 [team-analysis: UX-004]

- [x] **fix: portfolios/[id]/page.tsx — add holding 폼 클라이언트 검증**
  - 수량 0/음수, 가격 음수 클라이언트 검증 추가
  - 유효성 실패 시 API 호출 없이 인라인 에러 메시지 표시
  - 파일: `frontend/src/app/dashboard/portfolios/[id]/page.tsx`

### P1 -- 설정 KIS 테스트 버튼 로딩 상태 [team-analysis: UX-005]

- [x] **fix: settings/page.tsx — KIS 연결 테스트 버튼 isPending 로딩 상태**
  - `frontend/src/app/dashboard/settings/page.tsx` — mutation.isPending으로 버튼 disabled + Loader2 스피너
  - 중복 클릭 방지
  - 파일: `frontend/src/app/dashboard/settings/page.tsx`

### P1 -- analytics per-section isLoading/isError [team-analysis: UX-001]

- [x] **fix: analytics/page.tsx — 6개 쿼리 섹션별 로딩/에러 처리**
  - `frontend/src/app/dashboard/analytics/page.tsx` — metrics, monthlyReturns, portfolioHistory, sectorAllocation, fxGainLoss, krwAssetHistory 쿼리에 isLoading/isError 추출
  - 각 섹션: `isLoading` → `<ChartSkeleton />`, `isError` → `<SectionError onRetry={refetch} />`
  - 파일: `frontend/src/app/dashboard/analytics/page.tsx`

### P1 -- CSV/XLSX 내보내기 로딩 상태 [team-analysis: UX-002]

- [x] **fix: portfolios/[id]/page.tsx — 내보내기 버튼 로딩 상태**
  - isExporting 상태 추가, 내보내기 중 버튼 disabled + Loader2 스피너
  - 실패 시 toast.error()
  - 파일: `frontend/src/app/dashboard/portfolios/[id]/page.tsx`

---

## Sprint 6 work (team-analysis 2026-04-03, 6th sprint)

### P0 -- portfolios/[id]/page.tsx 분리 (1,226→~400 lines) [team-analysis: TD-001]

- [x] **refactor: portfolios/[id]/page.tsx — HoldingsSection + TransactionSection + PortfolioHeader 추출**
  - `frontend/src/app/dashboard/portfolios/[id]/HoldingsSection.tsx` — mutation hooks (addHolding, editHolding, deleteHolding) + 보유종목 테이블 + AlertDialog + 인라인 add/edit 폼 (~350 lines)
  - `frontend/src/app/dashboard/portfolios/[id]/TransactionSection.tsx` — useInfiniteQuery + 거래내역 테이블 + add/delete + memo 편집 (~300 lines)
  - `frontend/src/app/dashboard/portfolios/[id]/PortfolioHeader.tsx` — target widget + KIS sync 버튼 + export 버튼 (~150 lines)
  - 메인 page.tsx는 포트폴리오 데이터 fetch + 세 섹션 조합으로 ~400 lines 이하
  - 파일: `frontend/src/app/dashboard/portfolios/[id]/page.tsx` (분리 후 ~400 lines)

### P0 -- settings/page.tsx 분리 + 보안 탭 추가 (901→~150 lines) [team-analysis: TD-002, UX-001, UX-002, SEC-003]

- [x] **refactor: settings/page.tsx — 4개 섹션 컴포넌트 + Security/Sessions 탭 추가**
  - `frontend/src/app/dashboard/settings/AccountSection.tsx` — 프로필(이름), 비밀번호 변경, 이메일 변경, 계정 삭제 다이얼로그 (~200 lines)
  - `frontend/src/app/dashboard/settings/KisCredentialsSection.tsx` — KIS 계좌 CRUD + 연결 테스트 버튼(isPending) + 실계좌 잔고 조회 (~250 lines)
  - `frontend/src/app/dashboard/settings/SecurityLogsSection.tsx` — `GET /users/me/security-logs` 조회 + 이벤트 테이블(시간/액션/IP/UA) + 한국어 레이블 매핑 (~100 lines)
  - `frontend/src/app/dashboard/settings/ActiveSessionsSection.tsx` — `GET /auth/sessions` 조회 + 세션 목록 + 개별 'Revoke' 버튼 (~100 lines)
  - 메인 settings/page.tsx — 탭 컨테이너(계정/KIS 계좌/보안 로그/세션) ~150 lines
  - 파일: `frontend/src/app/dashboard/settings/page.tsx` (분리 후 ~150 lines)

### P0 -- GET/DELETE /auth/sessions 엔드포인트 추가 [team-analysis: SEC-001]

- [x] **feat: auth.py — 활성 세션 조회 및 개별 취소 API**
  - `backend/app/api/auth.py` — `GET /auth/sessions`: Redis SCAN `refresh:{user_id}:*` → JSON 파싱 → `[{jti, created_at}]` 반환
  - `DELETE /auth/sessions/{jti}`: `refresh:{user_id}:{jti}` 키 삭제 (단일 세션 취소)
  - 두 엔드포인트 모두 `Depends(get_current_user)` 적용
  - 파일: `backend/app/api/auth.py`

### P1 -- SSE httpx client 루프 외부 이동 (1-line fix) [team-analysis: TD-003, PERF-001]

- [x] **perf: prices.py — httpx.AsyncClient를 while 루프 외부로 이동**
  - `backend/app/api/prices.py:245` — `async with httpx.AsyncClient(timeout=10.0) as client:` 블록을 `while elapsed < _SSE_TIMEOUT:` 루프 밖으로 이동
  - 30초마다 TCP/TLS 재연결 → SSE 연결 수명(최대 2시간) 동안 1회 연결로 변경
  - 파일: `backend/app/api/prices.py`

### P1 -- Dashboard ETag + 304 Not Modified [team-analysis: PERF-002]

- [x] **perf: dashboard.py — ETag 기반 304 Not Modified 지원**
  - `backend/app/api/dashboard.py` — JSON 응답 직렬화 후 SHA-256(앞 16자) ETag 계산
  - `If-None-Match` 헤더 확인 → 일치 시 `Response(status_code=304)` 반환
  - 장 마감 후 30초 폴링 시 payload 90% 감소 예상
  - 파일: `backend/app/api/dashboard.py`

### P1 -- OrderDialog.test.tsx (0% → 80%+) [team-analysis: UX-003]

- [x] **test: OrderDialog — vitest + MSW 테스트 커버리지 80%+ 달성**
  - `frontend/src/components/OrderDialog.test.tsx` 신규 생성
  - 테스트 항목: (1) 수량 0/음수 → 제출 차단, (2) LIMIT 주문 시 가격 필수, (3) BUY/SELL 탭 전환 UI, (4) 국내/해외 주문 라우팅, (5) mutation 로딩 시 버튼 비활성, (6) 성공 → 다이얼로그 닫힘, (7) 실패 → toast.error()
  - 파일: `frontend/src/components/OrderDialog.test.tsx`

### P1 -- SSE JWT URL 노출 제거 (SSE 티켓 시스템) [team-analysis: SEC-002]

- [x] **security: SSE 단기 티켓으로 ?token= 쿼리 파라미터 제거**
  - `backend/app/api/auth.py` — `POST /auth/sse-ticket` (인증 필요): Redis에 `sse-ticket:{uuid4}` → `user_id`, TTL 30초 저장 후 티켓 UUID 반환
  - `backend/app/api/prices.py` — `?ticket=` 파라미터로 인증: Redis에서 티켓 조회 후 즉시 삭제(단일 사용), user_id 획득
  - `frontend/src/hooks/usePriceStream.ts` — EventSource 생성 전 POST /auth/sse-ticket 호출 후 ticket을 쿼리 파라미터로 사용
  - JWT가 서버 접근 로그에 노출되는 문제 해결
  - 파일: `backend/app/api/auth.py`, `backend/app/api/prices.py`, `frontend/src/hooks/usePriceStream.ts`

### P2 -- HoldingsTable aria-sort ARIA 수정 [team-analysis: TD-007]

- [x] **fix: HoldingsTable.tsx — role=button 제거, th 기본 columnheader 역할 사용**
  - `frontend/src/components/HoldingsTable.tsx:297` — `role='button'` 속성 제거
  - `th` 요소의 암묵적 role인 `columnheader`가 `aria-sort`를 올바르게 지원
  - `tabIndex={0}` 및 `onKeyDown` 키보드 핸들러는 유지
  - 파일: `frontend/src/components/HoldingsTable.tsx`

### P2 -- Icon-only 버튼 aria-label 추가 [team-analysis: UX-004]

- [x] **fix: journal/compare/watchlist — 아이콘 전용 버튼 aria-label 추가**
  - `frontend/src/app/dashboard/journal/page.tsx` — 월 이동 화살표 버튼: `aria-label='이전 달'`, `aria-label='다음 달'`; 삭제 버튼: `aria-label='거래 삭제'`
  - `frontend/src/app/dashboard/compare/page.tsx` — `aria-label='포트폴리오 추가'`, `aria-label='비교 목록에서 제거'`
  - `frontend/src/components/WatchlistSection.tsx` — `aria-label='관심종목 삭제'`
  - 파일: `frontend/src/app/dashboard/journal/page.tsx`, `compare/page.tsx`, `components/WatchlistSection.tsx`

### P2 -- npm 패치 업데이트 [team-analysis: TD-006]

- [x] **chore: frontend npm 패치/마이너 업데이트**
  - `@playwright/test` 1.58.2 → 1.59.1, `@sentry/nextjs` 10.45.0 → 10.47.0, `next` 16.2.0 → 16.2.2, `eslint-config-next` 16.2.0 → 16.2.2
  - `cd frontend && npm update @playwright/test @sentry/nextjs next eslint-config-next`
  - CI 통과 확인 후 완료
  - 파일: `frontend/package.json`, `frontend/package-lock.json`

---

## Sprint 7 work (team-analysis 2026-04-03, 7th sprint)

### P0 -- fx_gain_loss 캐시 키 불일치 수정 [team-analysis: SEC-003]

- [x] **fix: analytics.py — fx_gain_loss 캐시 키를 _analytics_key() 패턴으로 통일**
  - `backend/app/api/analytics.py:493` — `f"analytics:fx_gain_loss:{current_user.id}"` → `_analytics_key(current_user.id, "fx-gain-loss")`
  - sync 후 invalidate_analytics_cache()가 실제로 캐시를 삭제하지 못하는 버그 수정
  - 파일: `backend/app/api/analytics.py`

### P0 -- 수동 보유종목 변경 시 analytics 캐시 무효화 누락 [team-analysis: PERF-004]

- [x] **fix: portfolios.py — holding add/edit/delete 시 invalidate_analytics_cache 호출**
  - `backend/app/api/portfolios.py` — holding 생성/수정/삭제 mutation 후 `await invalidate_analytics_cache(current_user.id)` 추가
  - sync 없이 수동 변경 시 최대 1시간 stale 데이터 노출 방지
  - 파일: `backend/app/api/portfolios.py`

### P0 -- analytics/notifications/users 엔드포인트 rate limit 추가 [team-analysis: SEC-001]

- [x] **security: analytics.py, notifications.py, users.py — rate limiting 적용**
  - `backend/app/api/analytics.py` — 모든 GET 엔드포인트에 `@limiter.limit("30/minute")` 추가
  - `backend/app/api/users.py` — password-change, email-change, account-delete에 `@limiter.limit("5/minute")` 추가
  - `backend/app/api/notifications.py` — GET/PATCH에 `@limiter.limit("60/minute")` 추가
  - 파일: `backend/app/api/analytics.py`, `backend/app/api/users.py`, `backend/app/api/notifications.py`

### P0 -- SSE ticker 조회 DB 세션 최적화 [team-analysis: PERF-001]

- [x] **perf: prices.py — SSE 루프 내 ticker 조회를 모듈 레벨 캐시로 교체**
  - `backend/app/api/prices.py:235` — `AsyncSessionLocal()` ticker 조회를 루프 외부로 이동
  - 연결 시작 시 1회 ticker 목록 조회 후 60초 TTL로 메모리 캐시 (dict + timestamp)
  - sync 이벤트 후 캐시 무효화: `invalidate_sse_ticker_cache(user_id)` 함수 추가
  - 파일: `backend/app/api/prices.py`

### P1 -- SSE 해외종목 실시간 가격 지원 [team-analysis: TD-007]

- [x] **feat: prices.py — SSE 루프에 해외종목 가격 조회 추가**
  - `backend/app/api/prices.py:246` — `is_domestic(ticker)`로 tickers를 domestic/overseas로 분리
  - domestic → 기존 `fetch_and_cache_domestic_price()` 유지
  - overseas → `get_or_fetch_overseas_price()` 호출 (kis_price.py에 이미 존재)
  - 두 결과를 merge하여 `prices` dict 구성
  - 파일: `backend/app/api/prices.py`

### P1 -- OrderDialog 동적 임포트로 번들 최적화 [team-analysis: PERF-003]

- [x] **perf: HoldingsSection.tsx — OrderDialog dynamic import로 교체**
  - `frontend/src/app/dashboard/portfolios/[id]/HoldingsSection.tsx:22` — static import 제거
  - `const OrderDialog = dynamic(() => import('@/components/OrderDialog').then(m => ({ default: m.OrderDialog })), { ssr: false })`
  - 초기 번들에서 ~15-20KB 절감 예상
  - 파일: `frontend/src/app/dashboard/portfolios/[id]/HoldingsSection.tsx`

### P1 -- compare 페이지 empty state 추가 [team-analysis: UX-002]

- [x] **ux: compare/page.tsx — 포트폴리오 미선택 시 empty state 추가**
  - `frontend/src/app/dashboard/compare/page.tsx` — selectedPortfolios.length === 0 시 안내 UI 표시
  - 아이콘 + '비교할 포트폴리오를 추가하세요' + '포트폴리오 추가' 버튼 (기존 추가 버튼 트리거)
  - 파일: `frontend/src/app/dashboard/compare/page.tsx`

### P2 -- settings 탭 URL hash 반영 [team-analysis: UX-008]

- [x] **ux: settings/page.tsx — 탭 상태를 URL hash로 persist**
  - `frontend/src/app/dashboard/settings/page.tsx` — 탭 전환 시 `window.location.hash` 업데이트 (#account, #kis, #security-logs, #sessions)
  - 마운트 시 hash 읽어 초기 탭 복원
  - 파일: `frontend/src/app/dashboard/settings/page.tsx`

---

## Sprint 8 work (team-analysis 2026-04-04, 8th sprint)

### P0 -- stocks/chart/alerts/watchlist 엔드포인트 rate limit 추가 [team-analysis: SEC-001]

- [x] **security: stocks.py, chart.py, alerts.py, watchlist.py — rate limiting 적용**
  - `backend/app/api/stocks.py` — 2개 GET 엔드포인트에 `@limiter.limit("30/minute")` 추가 + `from app.core.limiter import limiter` 임포트
  - `backend/app/api/chart.py` — GET 엔드포인트에 `@limiter.limit("30/minute")` 추가
  - `backend/app/api/alerts.py` — CRUD 엔드포인트에 `@limiter.limit("30/minute")` 추가
  - `backend/app/api/watchlist.py` — GET/POST/DELETE에 `@limiter.limit("60/minute")` 추가
  - 파일: `backend/app/api/stocks.py`, `backend/app/api/chart.py`, `backend/app/api/alerts.py`, `backend/app/api/watchlist.py`

### P0 -- analytics.py 분리 (780L → analytics_metrics.py + analytics_history.py + analytics_fx.py) [team-analysis: TD-001, PERF-003]

- [x] **refactor: analytics.py — 3개 라우터 파일로 분리**
  - `backend/app/api/analytics_metrics.py` — `get_metrics`, `get_monthly_returns`, `get_sector_allocation` + `_calc_*` 헬퍼
  - `backend/app/api/analytics_history.py` — `get_portfolio_history`, `get_krw_asset_history`
  - `backend/app/api/analytics_fx.py` — `get_fx_gain_loss`, `get_fx_history`
  - `backend/app/services/analytics_utils.py` — `_period_cutoff`, `_analytics_key`, `invalidate_analytics_cache` 공통 함수
  - `backend/app/main.py` — 3개 라우터 등록으로 교체
  - 파일: `backend/app/api/analytics_metrics.py`, `analytics_history.py`, `analytics_fx.py`, `services/analytics_utils.py`

### P0 -- analytics/page.tsx 분리 (762L → 섹션 컴포넌트) [team-analysis: TD-003, PERF-003]

- [x] **refactor: analytics/page.tsx — 4개 섹션 컴포넌트로 분리**
  - `frontend/src/app/dashboard/analytics/MetricsSection.tsx` — 성과 지표 (total_return, cagr, mdd, sharpe) + period 탭 (~150 lines)
  - `frontend/src/app/dashboard/analytics/MonthlyReturnsSection.tsx` — 월별 수익 heatmap + bar chart (~150 lines)
  - `frontend/src/app/dashboard/analytics/SectorFxSection.tsx` — 섹터 배분 donut + 환차손익 (~200 lines)
  - `frontend/src/app/dashboard/analytics/HistorySection.tsx` — 포트폴리오 히스토리 + KRW 자산 추이 (~200 lines)
  - 메인 page.tsx는 섹션 조합 + 쿼리 키 공유 ~100 lines
  - 파일: `frontend/src/app/dashboard/analytics/` (신규 4개 컴포넌트)

### P1 -- npm 마이너 업데이트 [team-analysis: TD-005]

- [x] **chore: frontend npm 마이너 업데이트**
  - `@tanstack/react-query` 5.91.0 → 5.96.2, `@tanstack/react-query-devtools` 5.91.3 → 5.96.2
  - `axios` 1.13.6 → 1.14.0, `@next/bundle-analyzer` 16.2.1 → 16.2.2
  - `eslint-config-next` 16.2.0 → 16.2.2, `@types/node` 25.5.0 → 25.5.2
  - `cd frontend && npm update @tanstack/react-query @tanstack/react-query-devtools axios @next/bundle-analyzer eslint-config-next @types/node`
  - CI 통과 확인 후 완료
  - 파일: `frontend/package.json`, `frontend/package-lock.json`

### P1 -- Python 패치 업데이트 [team-analysis: TD-006]

- [x] **chore: backend Python 패치 업데이트**
  - `fastapi` 0.135.1 → 0.135.3, `redis` 7.3.0 → 7.4.0, `sentry-sdk` 2.55.0 → 2.57.0
  - `SQLAlchemy` 2.0.48 → 2.0.49, `ruff` 0.15.6 → 0.15.9
  - `cd backend && pip install --upgrade fastapi redis sentry-sdk sqlalchemy ruff && pip freeze > requirements.txt`
  - 테스트 통과 확인 후 완료
  - 파일: `backend/requirements.txt`

### P1 -- journal/page.tsx 빈 달 empty state 추가 [team-analysis: UX-001]

- [x] **ux: journal/page.tsx — 거래 없는 달 empty state 추가**
  - `frontend/src/app/dashboard/journal/page.tsx` — `trades.length === 0` 조건에 empty state UI 추가
  - BookOpen 아이콘 + '이 달에는 거래 내역이 없습니다' + '거래 추가하기' 포트폴리오 링크
  - 파일: `frontend/src/app/dashboard/journal/page.tsx`

### P1 -- compare/page.tsx 기간 필터 추가 [team-analysis: UX-002, PERF-002]

- [x] **feat: compare/page.tsx — 기간 필터 탭(1m/3m/6m/1y/all) 추가**
  - `frontend/src/app/dashboard/compare/page.tsx` — period 상태 추가 + 탭 UI
  - portfolio-history API 호출 시 period 파라미터 전달
  - 기본값 3m. 각 포트폴리오 쿼리 키에 period 포함
  - 파일: `frontend/src/app/dashboard/compare/page.tsx`

### P2 -- kis_order.py 분리 (780L → 3개 서비스 파일) [team-analysis: TD-002]

- [x] **refactor: kis_order.py — 국내/해외/조회 분리**
  - `backend/app/services/kis_domestic_order.py` — `place_domestic_order`, `get_orderable_quantity` (국내)
  - `backend/app/services/kis_overseas_order.py` — `place_overseas_order` (해외)
  - `backend/app/services/kis_order_query.py` — `get_pending_orders`, `cancel_order`, `settle_pending_orders` (조회/취소)
  - `backend/app/services/kis_order.py` — 하위 호환 re-export만 유지
  - 파일: `backend/app/services/kis_domestic_order.py`, `kis_overseas_order.py`, `kis_order_query.py`

---

## Sprint 9 work (team-analysis 2026-04-06, 9th sprint)

### P0 -- 로컬 venv pip 동기화 (CVE 패치) [team-analysis: TD-001]

- [x] **chore: backend venv — requirements.txt 동기화**
  - `cd backend && source venv/bin/activate && pip install -r requirements.txt`
  - Pygments 2.19.2 → 2.20.0 (CVE-2026-4539), requests 2.32.5 → 2.33.0 (CVE-2026-25645) 적용
  - requirements.txt 이미 최신 버전 명시됨 — venv만 동기화
  - 파일: `backend/venv` (재설치 후 pip-audit 재확인)

### P0 -- starlette 0.52.1 → 1.0.0 마이그레이션 [team-analysis: TD-002]

- [x] **chore: backend — starlette 1.0.0 업그레이드 및 호환성 검증**
  - `backend/requirements.txt` — `starlette==0.52.1` → `starlette==1.0.0`
  - FastAPI 내부 의존성 확인 (`fastapi>=0.135.3` 와 호환 여부)
  - `cd backend && source venv/bin/activate && pip install starlette==1.0.0 && pytest tests/ -x -q` 로 회귀 확인
  - 파일: `backend/requirements.txt`

### P1 -- pytest-asyncio 0.25.3 → 1.3.0 업그레이드 [team-analysis: TD-003]

- [x] **chore: backend — pytest-asyncio 1.3.0 업그레이드**
  - `backend/requirements.txt` — `pytest-asyncio==0.25.3` → `pytest-asyncio==1.3.0`
  - pytest.ini `asyncio_mode = auto` 설정 호환성 확인
  - 마이그레이션 노트 검토: `asyncio_mode`, fixture scope 변경 사항
  - `pytest tests/ -x -q` 전체 통과 확인
  - 파일: `backend/requirements.txt`, `backend/pytest.ini` (필요 시)

### P1 -- analytics.py shim 최소화 [team-analysis: TD-004]

- [x] **refactor: analytics.py — 762L shim을 30L 이하로 축소**
  - `backend/app/api/analytics.py` — 실제 엔드포인트 구현 코드 전부 삭제 (이미 split 모듈에 있음)
  - re-export / backward-compat 임포트만 유지: `invalidate_analytics_cache`, `router` 등
  - 파일: `backend/app/api/analytics.py`

### P1 -- dashboard/page.tsx 603L → DashboardMetrics + PortfolioList 분리 [team-analysis: TD-005]

- [x] **refactor: dashboard/page.tsx — 독립 섹션 컴포넌트 추출**
  - `frontend/src/app/dashboard/DashboardMetrics.tsx` — 총 자산/수익/일변동 지표 카드 (~150 lines)
  - `frontend/src/app/dashboard/PortfolioList.tsx` — 포트폴리오 목록 + WatchlistSection + 보유종목 테이블 (~200 lines)
  - 메인 page.tsx — 두 컴포넌트 조합 + SSE/쿼리 상태 관리 (~200 lines)
  - 각 섹션 독립 ErrorBoundary 적용
  - 파일: `frontend/src/app/dashboard/DashboardMetrics.tsx`, `frontend/src/app/dashboard/PortfolioList.tsx`, `frontend/src/app/dashboard/page.tsx`

### P1 -- analytics 섹션별 ErrorBoundary 추가 [team-analysis: UX-001]

- [x] **ux: analytics/page.tsx — MetricsSection, HistorySection, SectorFxSection에 ErrorBoundary 감싸기**
  - `frontend/src/app/dashboard/analytics/page.tsx` — 각 섹션 컴포넌트를 `<ErrorBoundary>` 로 감싸기
  - 개별 섹션 오류 시 전체 페이지 크래시 방지
  - 파일: `frontend/src/app/dashboard/analytics/page.tsx`

### P2 -- portfolios.py 751L 분리 [team-analysis: TD-006]

- [x] **refactor: portfolios.py — 3개 라우터 파일로 분리**
  - `backend/app/api/portfolio_holdings.py` — holding CRUD (add/edit/delete/bulk) + reconciliation 관련 (~250 lines)
  - `backend/app/api/portfolio_transactions.py` — transaction CRUD + cursor pagination (~200 lines)
  - `backend/app/api/portfolios.py` — portfolio CRUD + reorder + target + sync 트리거 (~300 lines)
  - `backend/app/main.py` — 3개 라우터 등록으로 교체
  - 파일: `backend/app/api/portfolio_holdings.py`, `backend/app/api/portfolio_transactions.py`, `backend/app/api/portfolios.py`

### P2 -- KisCredentialsSection KIS 계좌 추가 성공 toast [team-analysis: UX-002]

- [x] **ux: KisCredentialsSection.tsx — 계좌 추가/삭제 성공 toast 추가**
  - `frontend/src/app/dashboard/settings/KisCredentialsSection.tsx` — 계좌 추가 성공 시 `toast.success('KIS 계좌가 등록되었습니다')`, 삭제 성공 시 `toast.success('KIS 계좌가 삭제되었습니다')` 추가
  - 파일: `frontend/src/app/dashboard/settings/KisCredentialsSection.tsx`
