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

</details>

---

## Current work

### P1 -- Excel 내보내기 (15-4 / 19-3)

- [ ] **feat: 포트폴리오 Excel(xlsx) 내보내기 API + UI**
  - `backend/app/api/portfolio_export.py` — `GET /{portfolio_id}/export/xlsx` 엔드포인트 추가
  - openpyxl 사용: 보유 종목 시트 + 거래내역 시트 (서식 포함)
  - 열 너비 자동 조정, 헤더 볼드, 숫자 형식 적용
  - `frontend/src/app/dashboard/portfolios/[id]/page.tsx` — "Excel 내보내기" 버튼 추가 (CSV 버튼 옆)
  - 파일: `backend/app/api/portfolio_export.py`, 포트폴리오 상세 페이지

### P1 -- Bulk Holdings API (12-5)

- [ ] **feat: 보유 종목 일괄 등록 API**
  - `backend/app/api/portfolios.py` — `POST /portfolios/{id}/holdings/bulk` 엔드포인트 추가
  - 요청: `[{ticker, name, quantity, avg_price}]` 배열 (최대 100건)
  - 중복 ticker 처리: upsert (기존 보유 수량+평단가 가중평균 업데이트)
  - 응답: `{created: N, updated: N, errors: [...]}`
  - 파일: `backend/app/api/portfolios.py`, `backend/tests/test_portfolios.py`

### P1 -- 투자 일지 페이지 (17-3)

- [ ] **feat: 투자 일지 타임라인 페이지**
  - `frontend/src/app/dashboard/journal/page.tsx` 생성
  - 거래 내역(transactions)을 날짜 역순으로 타임라인 형식으로 표시
  - 메모가 있는 항목은 말풍선으로 강조 표시
  - 종목별 필터, BUY/SELL 타입 필터 제공
  - Sidebar/BottomNav에 "일지" 메뉴 항목 추가
  - 파일: `frontend/src/app/dashboard/journal/page.tsx`, `Sidebar.tsx`, `BottomNav.tsx`

### P0 -- 테스트 인프라 수정 (일괄 실행 시 294건 ERROR)

- [x] **fix: conftest.py async DB session 격리 문제 해결**
  - `backend/tests/conftest.py` -- async session fixture가 일괄 실행 시 세션 누수 발생
  - 원인: `pytest-asyncio` + `asyncpg` 세션 cleanup이 불완전
  - 해결: 테스트별 독립 DB session 생성 + 트랜잭션 rollback 패턴 적용
  - 검증: `pytest -q` 일괄 실행 시 0 errors 확인

### P0 -- 중복 파일 정리

- [x] **chore: 공백 포함 중복 파일 삭제**
  - `backend/.coverage 2`, `.coverage 3`, `.coverage 4` 삭제
  - `backend/alembic/versions/61cd677d984b_add_sync_type_to_sync_logs 2.py` 삭제
  - `backend/app/api/internal 2.py` 삭제
  - `backend/app/services/backup_health 2.py` 삭제
  - `backend/tests/test_backup_health 2.py`, `test_backup_health 3.py` 삭제
  - `backend/tests/test_health 2.py`, `test_health 3.py` 삭제
  - `backend/tests/test_health_data_integrity 2.py` 삭제
  - `backend/tests/test_internal 2.py`, `test_internal 3.py` 삭제
  - `docs/plan/todo 2.md`, `docs/runbooks/restore 2.md` 삭제
  - `.coveragerc`에 `internal 2.py` 등 중복 파일 제외 패턴 추가

### P1 -- npm 취약점 해결

- [x] **chore: yaml 2.0.0-2.8.2 Stack Overflow 취약점 수정**
  - `cd frontend && npm audit fix`
  - 4건 (2 moderate, 2 high): yaml 패키지 deep nested YAML collections
  - 빌드 확인 후 커밋

### P1 -- Trading Feature 테스트 커버리지 (27% -> 80%+)

- [x] **test: orders.py 라우터 테스트 확장** (27% -> 80%+)
  - `backend/tests/test_orders.py` -- 매수/매도, 예수금 조회, 미체결, 취소 등 통합 테스트
  - KIS API mock, Redis 락 mock
  - 에러 케이스: 보유수량 부족, KIS API 실패, 장외시간
  - 파일: `backend/tests/test_orders.py`

- [x] **test: kis_transaction.py 서비스 테스트 추가** (0% -> 80%+)
  - 국내(TTTC8001R) + 해외(TTTS3035R) 체결내역 조회 테스트
  - httpx mock으로 KIS API 응답 모킹
  - 파일: `backend/tests/test_kis_transaction.py`

- [x] **test: kis_order.py 서비스 테스트 추가**
  - place_domestic_order, place_overseas_order, cancel_order 단위 테스트
  - 계좌 유형별 TR_ID 분기 검증 (일반/ISA/연금/IRP)
  - 파일: `backend/tests/test_kis_order.py`

- [x] **test: kis_balance.py 서비스 테스트 추가**
  - 국내+해외 예수금 합산 로직 테스트
  - KIS API 실패 시 에러 전파 검증
  - 파일: `backend/tests/test_kis_balance.py`

### P1 -- 매수/매도 UX 개선 (Before/After 경험)

- [x] **feat: OrderDialog에 현재 보유 정보 표시**
  - `frontend/src/components/OrderDialog.tsx` — `existingHolding` prop 추가
  - 포트폴리오 페이지에서 holding 데이터를 OrderDialog에 전달
  - 다이얼로그 상단에 "현재 보유: N주 @ 평단가" 표시 (보유 없으면 미표시)
  - 파일: `OrderDialog.tsx`, `portfolios/[id]/page.tsx`

- [x] **feat: 매수 폼 — 추가 매수 후 예상 평단가 실시간 계산**
  - 수량/가격 입력 시 `(보유수량 × 평단가 + 매수수량 × 매수가) / (보유수량 + 매수수량)` 계산
  - 기존 평단가 대비 변화 방향(↑↓)과 차이 표시
  - 시장가 주문 시 현재가 기준으로 계산
  - 파일: `OrderDialog.tsx`

- [x] **feat: 매도 폼 — 현재 손익 + 실현손익 미리보기**
  - 보유 중인 경우 현재 손익(₩)과 수익률(%) 표시
  - 수량 입력 시 해당 수량 매도 기준 실현손익 실시간 계산
    - `(매도가 - 평단가) × 매도수량`
  - 전량 매도 버튼 추가 (보유 수량 자동 입력)
  - 파일: `OrderDialog.tsx`

- [x] **feat: 주문 완료 후 Before/After 변화 요약 표시**
  - 주문 성공 toast에 포트폴리오 변화 요약 추가
    - 매수: "평단가 50,000 → 48,500 (-3%)"
    - 매도: "실현손익 +125,000원 (+5.0%)"
  - 파일: `OrderDialog.tsx`, `useOrders.ts`

### P2 -- 저커버리지 라우터 테스트 보강

- [x] **test: health.py 라우터 테스트 보강** (39% -> 80%+)
  - data-integrity, holdings-reconciliation, orphan-records 엔드포인트 테스트
  - 파일: `backend/tests/test_health.py`

- [x] **test: alerts.py 라우터 테스트 보강** (67% -> 80%+)
  - 알림 CRUD + 활성화/비활성화 엔드포인트 테스트
  - 파일: `backend/tests/test_alerts.py`

- [x] **test: analytics.py 라우터 테스트 보강** (55% -> 80%+)
  - sector-allocation, monthly-returns, metrics 엔드포인트 테스트
  - 기간별 필터 (1W/1M/3M/6M/1Y/ALL) 케이스
  - 파일: `backend/tests/test_analytics_api.py`
