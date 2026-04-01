# THE WEALTH -- Tasks

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

</details>

---

## Current work

### P0 -- GZip 응답 압축 미들웨어 추가 [team-analysis: PERF-001 + TD-011]

- [x] **perf: FastAPI GZipMiddleware 추가**
  - `backend/app/main.py` — `from fastapi.middleware.gzip import GZipMiddleware` 추가
  - `app.add_middleware(GZipMiddleware, minimum_size=1000)` — 1KB 이상 응답에 gzip 적용
  - dashboard/summary, analytics 엔드포인트 JSON 응답 40-70% 압축 예상
  - 파일: `backend/app/main.py`

### P0 -- `_is_domestic()` 유틸리티 통합 [team-analysis: TD-001]

- [x] **refactor: `backend/app/core/ticker.py` 생성 — 중복 제거**
  - `backend/app/core/ticker.py` 신규 생성: `DOMESTIC_TICKER_RE`, `is_domestic(ticker: str) -> bool`
  - 기존 5개 파일에서 중복 제거: `analytics.py`, `dashboard.py`, `portfolios.py`, `orders.py`, `chart.py`
  - 각 파일에서 `from app.core.ticker import is_domestic` 임포트로 교체
  - 테스트: `tests/unit/test_ticker.py` 신규 생성 (국내/해외 판별 엣지 케이스)
  - 파일: `backend/app/core/ticker.py`, 5개 API 파일

### P0 -- analytics cache invalidation 누락 엔드포인트 수정 [team-analysis: PERF-005]

- [x] **fix: fx-gain-loss, krw-asset-history 캐시 무효화 추가**
  - `backend/app/api/analytics.py` — `invalidate_analytics_cache()` 함수에 두 키 추가
  - `fx-gain-loss`, `krw-asset-history:{period}` (1M/3M/6M/1Y/ALL 각 기간) invalidation 추가
  - 보유종목 추가/삭제/bulk 성공 후에도 호출되도록 `portfolios.py`에 연결
  - 파일: `backend/app/api/analytics.py`, `backend/app/api/portfolios.py`

### P1 -- transactions.ticker DB 인덱스 추가 [team-analysis: TD-009]

- [x] **perf: transactions 테이블 ticker 컬럼 인덱스 추가**
  - `backend/app/models/transaction.py` — `ticker` mapped_column에 `index=True` 추가
  - Alembic migration 생성: `alembic revision --autogenerate -m "add_index_transactions_ticker"`
  - 파일: `backend/app/models/transaction.py`, `backend/alembic/versions/`

### P1 -- price_snapshots 복합 인덱스 추가 [team-analysis: PERF-004 + TD-013]

- [ ] **perf: price_snapshots (ticker, snapshot_date) 복합 인덱스**
  - `backend/app/models/price_snapshot.py` — `__table_args__`에 `Index('ix_price_snapshot_ticker_date', 'ticker', 'snapshot_date')` 추가
  - Alembic migration 생성
  - analytics 쿼리 `WHERE ticker IN (...) AND snapshot_date >= cutoff` 성능 개선
  - 파일: `backend/app/models/price_snapshot.py`, `backend/alembic/versions/`

### P1 -- 포트폴리오 삭제 확인 다이얼로그 교체 [team-analysis: TD-010 + UX-003]

- [ ] **fix: portfolios/page.tsx — confirm() → shadcn AlertDialog**
  - `frontend/src/app/dashboard/portfolios/page.tsx` — `confirm()` 제거, AlertDialog 적용
  - 제목: '포트폴리오 삭제', 본문: '{name} 포트폴리오를 영구 삭제하시겠습니까?'
  - 보유종목 삭제도 동일 패턴으로 AlertDialog 적용 (`portfolios/[id]/page.tsx`)
  - 파일: `frontend/src/app/dashboard/portfolios/page.tsx`, `portfolios/[id]/page.tsx`

### P1 -- 비교 페이지 빈 상태 추가 [team-analysis: UX-004]

- [ ] **fix: compare 페이지 — 포트폴리오 1개 이하일 때 empty state**
  - `frontend/src/app/dashboard/compare/page.tsx` — `portfolios.length < 2` 조건 추가
  - 안내 카드: '포트폴리오 비교는 2개 이상의 포트폴리오가 필요합니다' + 생성 링크 버튼
  - 파일: `frontend/src/app/dashboard/compare/page.tsx`

### P1 -- API 엔드포인트 Rate Limiting 추가 [team-analysis: SEC-001]

- [ ] **security: portfolios/holdings/orders 엔드포인트 rate limit 추가**
  - `backend/app/api/portfolios.py` — 주요 write 엔드포인트에 `@limiter.limit('60/minute')` 추가
  - `backend/app/api/orders.py` — order 엔드포인트에 `@limiter.limit('30/minute')` 추가
  - 파일: `backend/app/api/portfolios.py`, `backend/app/api/orders.py`

### P1 -- CORS allow_methods/allow_headers 명시적 스코프 [team-analysis: SEC-004]

- [ ] **security: CORS wildcard → 명시적 허용 목록**
  - `backend/app/main.py` — `allow_methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS']`
  - `allow_headers=['Content-Type','Authorization','X-Request-ID']` 명시
  - 파일: `backend/app/main.py`

### P2 -- localStorage.getItem() 방어 처리 [team-analysis: SEC-008]

- [ ] **fix: StockSearchDialog localStorage read try-catch 추가**
  - `frontend/src/components/StockSearchDialog.tsx` — JSON.parse() try-catch 추가
  - 파싱 실패 시 빈 배열 반환, 각 항목 string 유효성 검사
  - 파일: `frontend/src/components/StockSearchDialog.tsx`

### P2 -- Sentry environment 설정 환경변수화 [team-analysis: SEC-009]

- [ ] **fix: Sentry init — environment hardcoding 제거**
  - `backend/app/core/config.py` — `ENVIRONMENT: str = 'development'` 설정 추가
  - `backend/app/main.py` — `environment=settings.ENVIRONMENT` 사용
  - `backend/.env.example` — `ENVIRONMENT=production` 예시 추가
  - 파일: `backend/app/main.py`, `backend/app/core/config.py`, `backend/.env.example`

### P2 -- 종목 상세 페이지 차트 스켈레톤 추가 [team-analysis: UX-005]

- [ ] **fix: stocks/[ticker]/page.tsx — 차트 로딩 중 ChartSkeleton 표시**
  - `frontend/src/app/dashboard/stocks/[ticker]/page.tsx` — 기존 ChartSkeleton 컴포넌트 활용
  - candlestick 데이터 fetching 동안 `<ChartSkeleton />` 렌더링
  - 파일: `frontend/src/app/dashboard/stocks/[ticker]/page.tsx`

### 이전 완료 작업

### P1 -- 해외주식 환차익/환차손 분리: 백엔드 API (17-2)

- [x] **feat: GET /analytics/fx-gain-loss 엔드포인트 추가**
  - `backend/app/api/analytics.py` — 해외주식 보유 종목별 환차익/환차손 계산 엔드포인트
  - 각 해외주식에 대해: 매입 시점 USD 가치 vs 현재 USD 가치(주가 수익), 매입 시점 환율 vs 현재 환율(환차익)
  - 매입 시점 환율은 `fx_rate_snapshots` 테이블에서 보유 종목 `created_at` 날짜에 가장 가까운 환율 사용
  - 응답: `[{ticker, name, quantity, avg_price_usd, current_price_usd, stock_pnl_usd, fx_rate_at_buy, fx_rate_current, fx_gain_krw, stock_gain_krw, total_pnl_krw}]`
  - 해외주식 판별: ticker가 숫자 6자리가 아닌 경우 (기존 `_is_domestic()` 함수 활용)
  - 현재가는 Redis 캐시 우선(`_get_cached_price`), 없으면 `avg_price` fallback
  - 현재 환율은 `get_cached_fx_rate()` 사용
  - 파일: `backend/app/api/analytics.py`

### P1 -- 해외주식 환차익/환차손 분리: 프론트엔드 UI (17-2)

- [x] **feat: 분석 페이지에 해외주식 환차익/환차손 섹션 추가**
  - `frontend/src/app/dashboard/analytics/page.tsx` — 새 섹션 추가
  - `/analytics/fx-gain-loss` API 호출하여 해외주식별 환차익/환차손 표시
  - 테이블 형식: 종목명/티커, 주가 수익(USD), 환차익(KRW), 총 손익(KRW)
  - 보유 해외주식이 없으면 섹션 미표시
  - 파일: `frontend/src/app/dashboard/analytics/page.tsx`

### P1 -- 원화 환산 총 자산 추이: 백엔드 API (17-2)

- [x] **feat: GET /analytics/krw-asset-history 엔드포인트 추가**
  - `backend/app/api/analytics.py` — 환율 변동 반영 원화 총 자산 추이 엔드포인트
  - `price_snapshots` × `fx_rate_snapshots` JOIN으로 날짜별 원화 환산 총 자산 계산
  - 국내주식: KRW 그대로, 해외주식: 해당 날짜 `fx_rate_snapshots` 환율 적용 (없으면 최근 환율 interpolation)
  - `period` 쿼리 파라미터 지원: 1M / 3M / 6M / 1Y / ALL
  - 응답: `[{date: "YYYY-MM-DD", value: float, domestic_value: float, overseas_value_krw: float}]`
  - 파일: `backend/app/api/analytics.py`

### P1 -- 원화 환산 총 자산 추이: 프론트엔드 차트 (17-2)

- [x] **feat: 분석 페이지에 원화 환산 총 자산 추이 차트 추가**
  - `frontend/src/app/dashboard/analytics/page.tsx` — 기존 포트폴리오 가치 추이 섹션 아래에 추가
  - `/analytics/krw-asset-history` API 호출
  - Recharts LineChart: 국내(KRW) + 해외(환산 KRW) 스택 영역 차트 (AreaChart, stacked)
  - 기간 탭: 1M / 3M / 6M / 1Y / ALL (historyPeriod 상태 재사용)
  - 해외주식 보유가 없으면 단순 라인 차트로 표시
  - 파일: `frontend/src/app/dashboard/analytics/page.tsx`

### P2 -- 투자 일지 필터링 및 검색 (17-3)

- [x] **feat: 투자 일지 월별/종목별 필터링 + 키워드 검색**
  - `frontend/src/app/dashboard/journal/page.tsx` — 검색/필터 기능 추가
  - 월별 필터: 드롭다운 (거래 이력에서 유니크 월 목록 추출)
  - 종목별 필터: 드롭다운 (보유 종목 + 거래 종목 합집합)
  - 키워드 검색: 메모(memo) 내용 검색, debounce 300ms
  - 검색/필터 결과 0건 시 "검색 결과 없음" empty state 표시
  - 파일: `frontend/src/app/dashboard/journal/page.tsx`

### P2 -- 투자 결정 회고 위젯 (17-3)

- [x] **feat: 투자 결정 회고 위젯 — 매수 시점 가격 vs 현재가 비교**
  - `frontend/src/app/dashboard/journal/page.tsx` — 페이지 상단에 회고 요약 섹션 추가
  - 최근 30일 이내 BUY 거래 종목에 대해: 매수가 vs 현재가 비교 카드
  - 각 카드: 종목명, 매수가(avg), 현재가(from dashboard summary), 수익률(%)
  - 현재가는 `/dashboard/summary` 데이터에서 가져옴 (별도 API 호출 없이)
  - 최대 5개까지만 표시 (평가금액 큰 순)
  - 파일: `frontend/src/app/dashboard/journal/page.tsx`
