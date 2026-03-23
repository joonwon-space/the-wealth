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

</details>

---

## Current work

### P0 -- Test coverage recovery (90% -> 93%+)

- [x] **test: health.py router 테스트 추가** (47% -> 85%+)
  - `/api/v1/health` 엔드포인트의 DB/Redis/KIS/backup 상태 응답 테스트
  - 파일: `backend/tests/test_health.py`

- [x] **test: internal.py router 테스트 추가** (58% -> 90%+)
  - `POST /internal/backup-status` 성공/실패 시나리오 테스트
  - 파일: `backend/tests/test_internal.py`

- [x] **test: backup_health.py service 테스트 추가** (69% -> 90%+)
  - 백업 디렉토리 존재/부재, 파일 mtime 조회 로직 테스트
  - 파일: `backend/tests/test_backup_health.py`

### P1 -- npm 의존성 보안/업데이트

- [x] **chore: flatted Prototype Pollution 취약점 해결** (`npm audit fix`)
  - eslint -> file-entry-cache -> flat-cache -> flatted 3.4.1 (high severity)
  - `npm audit fix` 또는 eslint 버전 업데이트로 해결

- [x] **chore: frontend 의존성 마이너 업데이트**
  - Next.js 16.1.7 -> 16.2.0, tailwindcss 4.2.1 -> 4.2.2, shadcn 4.0.8 -> 4.1.0
  - `npm update` 후 빌드 확인

---

### P1 -- 16-2: Frontend 테스트 인프라 (MSW + 컴포넌트 테스트)

- [x] **test: MSW 2.x 설치 + 핸들러 설정**
  - `npm install msw --save-dev` (frontend)
  - `src/test/handlers.ts` — dashboard/summary, analytics/metrics 핸들러
  - `src/test/server.ts` — setupServer + setupWorker
  - `src/test/setup.ts` — beforeAll/afterEach/afterAll 훅 추가
  - vitest.config.ts에 MSW server setup 연동

- [x] **test: HoldingsTable 유닛 테스트**
  - `src/components/HoldingsTable.test.tsx`
  - 정렬 동작 (다중 컬럼), PnL 색상 규칙 (양수=빨간색, 음수=파란색), 해외 USD 표시 테스트
  - MSW로 API 모킹

### P1 -- 12-4: 알림 센터

- [x] **feat: notifications 테이블 + API**
  - `backend/app/models/notification.py` — id, user_id, type, title, body, is_read, created_at
  - Alembic migration: `add_notifications_table`
  - `backend/app/api/notifications.py` — `GET /notifications` (unread 먼저), `PATCH /notifications/{id}/read`, `POST /notifications/read-all`
  - `backend/app/schemas/notification.py` — Pydantic schemas
  - `backend/app/main.py` — router 등록
  - 기존 alert SSE 트리거 시 notification 레코드 생성 연동 (`backend/app/services/price_stream.py`)
  - 테스트: `backend/tests/test_notifications.py`

- [x] **feat: 알림 센터 프론트엔드 (벨 + 배지 + 드롭다운)**
  - `frontend/src/components/NotificationBell.tsx` — 벨 아이콘, 미읽 배지, 드롭다운 패널
  - `frontend/src/hooks/useNotifications.ts` — TanStack Query로 GET/PATCH
  - `frontend/src/app/dashboard/layout.tsx` 헤더에 NotificationBell 추가
  - 읽음 처리, 전체 읽음 처리

### P2 -- 14-2: MetricsMiddleware

- [x] **feat: API 응답시간 미들웨어**
  - `backend/app/middleware/metrics.py` — `MetricsMiddleware`: process_time 계산, structlog 기록, `X-Process-Time` 헤더 추가
  - `backend/app/main.py` — 미들웨어 등록
  - 테스트: `backend/tests/test_metrics_middleware.py`

### P2 -- 11-5: 거래 메모 (Trade Memo)

- [x] **feat: transactions.memo 컬럼 + PATCH API**
  - `backend/app/models/transaction.py` — `memo: Mapped[Optional[str]]` 컬럼 추가 (String(500))
  - Alembic migration: `add_transaction_memo_column`
  - `backend/app/api/portfolios.py` — `PATCH /portfolios/{pid}/transactions/{tid}` 메모 업데이트
  - `backend/app/schemas/transaction.py` — memo 필드 추가
  - 테스트: memo CRUD 케이스 추가

- [x] **feat: 거래 내역 메모 인라인 편집 UI**
  - `frontend/src/app/dashboard/portfolios/[id]/page.tsx` 거래 내역 테이블에 메모 컬럼 추가
  - 인라인 편집 (클릭 → input, blur → PATCH 호출)
  - TanStack Query mutation + optimistic update

---

## Trading Feature — 실제 주식 매매 기능

### Step 1 — DB 마이그레이션

- [x] **chore: trading 지원 Alembic 마이그레이션**
  - `kis_accounts` 테이블: `is_paper_trading` (Boolean, default: false), `account_type` (String(20)) 컬럼 추가
  - `transactions` 테이블: `order_no` (String(50)), `order_source` (String(10), default: "manual") 컬럼 추가
  - `orders` 테이블 신규 생성: `id`, `portfolio_id`, `kis_account_id`, `ticker`, `name`, `order_type`, `order_class`, `quantity`, `price`, `order_no`, `status`, `filled_quantity`, `filled_price`, `memo`, `created_at`, `updated_at`
  - `alembic revision --autogenerate -m "add_trading_support"`

### Step 2 — 백엔드 서비스 계층

- [x] **feat: KIS 주문 서비스 (`kis_order.py`)**
  - `backend/app/services/kis_order.py` 신규 생성
  - `place_domestic_order()`: 국내주식 매수/매도, 계좌 유형별 TR_ID 분기 (일반/ISA: `TTTC0802U`/`TTTC0801U`, 연금/IRP: `TTTC0852U`/`TTTC0851U`)
  - `place_overseas_order()`: 해외주식 매수/매도, 거래소별 TR_ID 분기 (`JTTT1002U`/`JTTT1006U`)
  - `get_orderable_quantity()`: 매수가능조회 (`TTTC8908R`), 해외 매수가능금액 (`TTTS3007R`)
  - `get_pending_orders()`: 미체결 주문 조회 (국내 `TTTC8036R`, 해외 `JTTT3018R`)
  - `cancel_order()`: 주문 취소 (국내 `TTTC0803U`, 해외 `JTTT1004U`)
  - Redis 기반 이중 주문 방지 락 (`order_lock:{portfolio_id}:{ticker}`, TTL: 10초)
  - 장 운영시간 체크 (국내 09:00~15:30), 장외 주문 시 안내 메시지
  - 레이트 리밋 5회/분, 모든 주문 시도를 `orders` 테이블에 기록

- [x] **feat: 예수금 조회 서비스 확장 (`kis_balance.py`)**
  - `backend/app/services/kis_balance.py` 신규 또는 `kis_account.py` 확장
  - `get_cash_balance()`: 국내 예수금 (`TTTC8434R`), 해외 체결기준잔고 (`TTTS3012R`)
  - 반환: `total_cash`, `available_cash`, `total_evaluation`, `total_profit_loss`, `profit_loss_rate`, `currency`, `foreign_cash`, `usd_krw_rate`

- [x] **feat: 주문 Pydantic 스키마 (`schemas/order.py`)**
  - `backend/app/schemas/order.py` 신규 생성
  - `OrderRequest`, `OrderResult`, `OrderableInfoResponse`, `CashBalanceResponse`, `PendingOrderResponse`

### Step 3 — 백엔드 API 계층

- [x] **feat: 주문 API 라우터 (`api/orders.py`)**
  - `backend/app/api/orders.py` 신규 생성
  - `POST /portfolios/{id}/orders`: 매수/매도 주문 실행 → KIS API 호출 → transactions/holdings/orders 테이블 자동 업데이트
  - `GET /portfolios/{id}/orders/orderable`: 주문 가능 수량/금액 조회 (`ticker`, `price`, `order_type` query params)
  - `GET /portfolios/{id}/orders/pending`: 미체결 주문 목록
  - `DELETE /portfolios/{id}/orders/{order_no}`: 주문 취소
  - `GET /portfolios/{id}/cash-balance`: 예수금 및 총 평가금액 (Redis 캐시 TTL 30초)
  - `backend/app/main.py`에 라우터 등록

- [x] **feat: 대시보드 API에 예수금 필드 추가**
  - `backend/app/api/dashboard.py` 수정
  - `GET /dashboard/summary` 응답에 `total_cash`, `total_assets` 필드 추가

### Step 4 — 백엔드 테스트

- [x] **test: 주문 API 테스트 (`tests/test_orders.py`)**
  - KIS API mock으로 매수/매도 주문 플로우 테스트
  - 이중 주문 방지 (Redis 락) 테스트
  - 계좌 유형별 TR_ID 분기 테스트 (일반/ISA/연금/IRP/해외)
  - 에러 케이스: 예수금 부족, 장외 시간, 종목 정지
  - 주문 취소 플로우 테스트
  - `kis_transaction.py` 0% 커버리지 해소도 함께

### Step 5 — 프론트엔드 훅 & 타입

- [ ] **feat: 주문 TanStack Query 훅 (`hooks/useOrders.ts`)**
  - `frontend/src/hooks/useOrders.ts` 신규 생성
  - `useCashBalance(portfolioId)`: 예수금 + 총평가 조회, 30초 폴링
  - `useOrderableQuantity(portfolioId, ticker, price, orderType)`
  - `usePlaceOrder(portfolioId)`: 주문 실행 mutation, 성공 시 캐시 무효화
  - `usePendingOrders(portfolioId)`: 미체결 주문 조회, 30초 폴링
  - `useCancelOrder(portfolioId)`: 주문 취소 mutation
  - Order 관련 TypeScript 타입 추가

### Step 6 — 프론트엔드 UI

- [ ] **feat: 주문 다이얼로그 컴포넌트 (`OrderDialog.tsx`)**
  - `frontend/src/components/OrderDialog.tsx` 신규 생성
  - shadcn/ui `Dialog` + `Tabs` 기반 (매수/매도 탭)
  - 지정가/시장가 선택, 수량 퀵 버튼 (10%/25%/50%/100%)
  - 주문금액·예수금·수수료 실시간 표시
  - 메모 필드 (transactions.memo 연계)
  - 주문 버튼 클릭 → 확인 다이얼로그 → 최종 실행
  - 매수=빨간색, 매도=파란색 (한국 컬러 컨벤션)

- [ ] **feat: 미체결 주문 패널 (`PendingOrdersPanel.tsx`)**
  - `frontend/src/components/PendingOrdersPanel.tsx` 신규 생성
  - 30초 폴링으로 자동 갱신
  - 체결 완료 시 sonner toast 알림
  - 주문 취소 버튼

- [ ] **feat: 포트폴리오 상세 페이지 개편**
  - `frontend/src/app/dashboard/portfolios/[id]/page.tsx` 수정
  - 상단 요약 영역: 총 평가금액 + 예수금(현금) + 총 수익률 표시
  - [신규 종목 매수] [전체 동기화] [미체결 주문 (N)] 버튼 추가
  - KIS 연결 안 된 포트폴리오는 예수금 영역 숨기고 기존 UI 유지
  - `HoldingsTable`에 [매수][매도] 버튼 추가 (KIS 연결 포트폴리오에서만 표시)
  - 신규 종목 매수: StockSearch → OrderDialog 자동 열림 플로우

- [ ] **feat: 대시보드 및 포트폴리오 목록에 예수금 표시**
  - `frontend/src/app/dashboard/page.tsx`: 총 자산(평가+예수금) 표시
  - `frontend/src/app/dashboard/portfolios/page.tsx`: 포트폴리오 카드에 예수금 필드 추가

### Step 7 — 설정 페이지 확장

- [ ] **feat: KIS 계좌 설정에 계좌 유형·모의투자 옵션 추가**
  - `frontend/src/app/dashboard/settings/page.tsx` 수정
  - 계좌 유형 선택 드롭다운 (일반/ISA/연금저축/IRP/해외주식)
  - 모의투자/실전투자 토글 (`is_paper_trading`)
  - 1회 주문 금액 상한 설정 입력 필드

### Step 8 — E2E 테스트

- [ ] **test: 주문 플로우 E2E (Playwright)**
  - 정상 매수/매도 플로우
  - 에러 케이스: 예수금 부족, 장외 시간
  - 미체결 주문 취소 플로우
