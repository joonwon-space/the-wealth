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

- [ ] **feat: transactions.memo 컬럼 + PATCH API**
  - `backend/app/models/transaction.py` — `memo: Mapped[Optional[str]]` 컬럼 추가 (String(500))
  - Alembic migration: `add_transaction_memo_column`
  - `backend/app/api/portfolios.py` — `PATCH /portfolios/{pid}/transactions/{tid}` 메모 업데이트
  - `backend/app/schemas/transaction.py` — memo 필드 추가
  - 테스트: memo CRUD 케이스 추가

- [ ] **feat: 거래 내역 메모 인라인 편집 UI**
  - `frontend/src/app/dashboard/portfolios/[id]/page.tsx` 거래 내역 테이블에 메모 컬럼 추가
  - 인라인 편집 (클릭 → input, blur → PATCH 호출)
  - TanStack Query mutation + optimistic update

