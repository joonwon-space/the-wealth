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
- [x] Team analysis sprint 2026-04-02: GZip, is_domestic 통합, cache fix, DB 인덱스, AlertDialog, compare empty state, rate limiting, CORS, localStorage 방어, Sentry env, chart skeleton (all items)
- [x] Milestone 17 complete: 환율 분석 (17-2), 투자 일지 (17-3), 포트폴리오 비교 (17-1)

</details>

---

## Current work

### P0 -- Sentry KIS 자격증명 유출 방지 [team-analysis: SEC-001]

- [ ] **security: Sentry before_send 훅으로 KIS 헤더 스크러빙**
  - `backend/app/main.py` — `sentry_sdk.init()`에 `before_send` 콜백 추가
  - `appkey`, `appsecret`, `authorization` 헤더 값을 `[Filtered]`로 대체
  - `kis_order.py`, `kis_token.py` — `httpx.HTTPStatusError` catch 후 헤더 없는 `RuntimeError` re-raise
  - 파일: `backend/app/main.py`, `backend/app/services/kis_order.py`, `backend/app/services/kis_token.py`

### P0 -- get_prev_close 무제한 쿼리 수정 [team-analysis: PERF-001]

- [ ] **perf: price_snapshot.py — DISTINCT ON (ticker) 쿼리로 교체**
  - `backend/app/services/price_snapshot.py:171-189` — 전체 rows fetch + Python dedup 제거
  - `DISTINCT ON (ticker) ORDER BY snapshot_date DESC` PostgreSQL 쿼리로 교체
  - 20종목 2년 데이터 기준 14,600행 -> 20행 전송, 50ms -> 5ms 예상
  - 파일: `backend/app/services/price_snapshot.py`

### P0 -- bcrypt DoS 방어: 비밀번호 max_length 추가 [team-analysis: SEC-002]

- [ ] **security: 비밀번호 필드 max_length=128 제한**
  - `backend/app/schemas/auth.py` — `RegisterRequest.password`, `LoginRequest.password` max_length=128
  - `backend/app/schemas/user.py` — `ChangePasswordRequest`, `DeleteAccountRequest` max_length=128
  - bcrypt 72바이트 truncation 고려, Pydantic validation 단계에서 차단
  - 파일: `backend/app/schemas/auth.py`, `backend/app/schemas/user.py`

### P0 -- cryptography 패키지 보안 업데이트 [team-analysis: TD-005]

- [ ] **chore: cryptography 46.0.5 -> latest 패치 적용**
  - `pip install --upgrade cryptography` 실행 후 `requirements.txt` 갱신
  - AES-256 KIS 자격증명 암호화 경로의 보안 패치 적용
  - pytest 전체 통과 확인
  - 파일: `backend/requirements.txt`

### P1 -- fx-gain-loss 엔드포인트 캐시 추가 [team-analysis: PERF-002]

- [ ] **perf: analytics.py — fx-gain-loss Redis 캐시 적용**
  - `backend/app/api/analytics.py:469-585` — `cache_key` guard + `setex` 호출 추가
  - 기존 `get_metrics` 캐시 패턴과 동일하게 적용
  - 3 DB 쿼리 + O(N*M) bisect 연산 → 캐시 hit 시 2ms 이내
  - 파일: `backend/app/api/analytics.py`

### P1 -- metrics 엔드포인트 해외종목 라우팅 수정 [team-analysis: PERF-003]

- [ ] **fix: analytics.py — 해외 ticker에 국내 가격 API 호출 방지**
  - `backend/app/api/analytics.py:156-158` — ticker 목록을 국내/해외 분류 후 각 API 라우팅
  - 해외 ticker → `fetch_overseas_price_detail` 사용
  - 실패 보장 KIS API 호출 제거, 경고 로그 감소
  - 파일: `backend/app/api/analytics.py`

### P1 -- SSE 활성 시 대시보드 폴링 비활성화 [team-analysis: PERF-004]

- [ ] **perf: dashboard/page.tsx — SSE 연결 시 refetchInterval 비활성화**
  - `frontend/src/app/dashboard/page.tsx:135-139` — SSE 연결 상태에 따라 `refetchInterval` 토글
  - SSE 활성: `refetchInterval: false`, SSE 비활성: `refetchInterval: REFRESH_INTERVAL_MS`
  - /dashboard/summary 호출 빈도 50% 감소 예상
  - 파일: `frontend/src/app/dashboard/page.tsx`

### P1 -- 포트폴리오 상세 mutation onError 핸들러 추가 [team-analysis: UX-001]

- [ ] **fix: portfolios/[id]/page.tsx — 7개 mutation에 onError toast 추가**
  - `frontend/src/app/dashboard/portfolios/[id]/page.tsx` — addHolding, editHolding, deleteHolding, addTxn, deleteTxn, updateMemo, updateTarget mutation에 onError 추가
  - 각 mutation 실패 시 `toast.error()` 한국어 메시지 표시
  - settings/page.tsx `updateNameMutation` 패턴 참조
  - 파일: `frontend/src/app/dashboard/portfolios/[id]/page.tsx`

### P1 -- Redis 커넥션 풀 공유 [team-analysis: PERF-005 / TD-001]

- [ ] **perf: redis_cache.py — 모듈 레벨 ConnectionPool 싱글턴으로 교체**
  - `backend/app/core/redis_cache.py` — `aioredis.ConnectionPool.from_url()` 모듈 레벨 생성
  - 모든 `aioredis.from_url()` 컨텍스트 매니저를 공유 풀 기반 `aioredis.Redis(connection_pool=_pool)` 로 교체
  - `backend/app/core/security.py`, `backend/app/api/dashboard.py`, `backend/app/services/stock_search.py` 에도 동일 패턴 적용
  - 요청당 40-300ms TCP 오버헤드 제거
  - 파일: `backend/app/core/redis_cache.py`, `backend/app/core/security.py`, `backend/app/api/dashboard.py`, `backend/app/services/stock_search.py`

### P1 -- 포트폴리오 목록 rename/delete mutation onError 추가 [team-analysis: UX-004]

- [ ] **fix: portfolios/page.tsx — renameMutation, deleteMutation, reorderMutation onError 추가**
  - `frontend/src/app/dashboard/portfolios/page.tsx` — renameMutation/deleteMutation에 `toast.error()` 추가
  - reorderMutation — `onMutate` snapshot 저장, `onError`에서 `queryClient.setQueryData` rollback
  - 파일: `frontend/src/app/dashboard/portfolios/page.tsx`

### P1 -- CSP unsafe-eval 프로덕션 제거 [team-analysis: SEC-004]

- [ ] **security: next.config.ts — 프로덕션 CSP에서 unsafe-eval 제거**
  - `frontend/next.config.ts:25` — `process.env.NODE_ENV === 'development'` 분기로 unsafe-eval 제한
  - 개발 환경만 Next.js HMR을 위한 unsafe-eval 허용
  - 파일: `frontend/next.config.ts`

### P1 -- TransactionMemoUpdate tags 필드 길이 제약 추가 [team-analysis: SEC-006]

- [ ] **security: portfolio.py schema — tags list 항목 수 + 개별 길이 제한**
  - `backend/app/schemas/portfolio.py:132-134` — `tags: Optional[list[Annotated[str, Field(max_length=50)]]] = Field(None, max_length=20)`
  - 최대 20개, 개당 최대 50자 제한
  - 파일: `backend/app/schemas/portfolio.py`

### P2 -- analytics/dashboard summary 쿼리 키 통일 [team-analysis: PERF-006]

- [ ] **perf: analytics/page.tsx — dashboard summary 쿼리 키 상수화**
  - `frontend/src/app/dashboard/analytics/page.tsx:129-133` — 쿼리 키를 `['dashboard', 'summary']`로 통일 (dashboard/page.tsx와 일치)
  - 대시보드 → 분석 페이지 이동 시 중복 요청 제거
  - 파일: `frontend/src/app/dashboard/analytics/page.tsx`

### P2 -- analytics 테이블 키보드 접근성 추가 [team-analysis: UX-006]

- [ ] **a11y: analytics/page.tsx — 종목 선택 row에 tabIndex + onKeyDown 추가**
  - `frontend/src/app/dashboard/analytics/page.tsx` — 모바일 카드 div를 button으로 교체, 데스크탑 tr에 `tabIndex={0}` + Enter/Space onKeyDown 추가
  - 파일: `frontend/src/app/dashboard/analytics/page.tsx`

### P2 -- 포트폴리오 상세 인라인 삭제 확인창 AlertDialog 교체 [team-analysis: UX-007]

- [ ] **ux: portfolios/[id]/page.tsx — 인라인 fixed 오버레이를 shadcn AlertDialog로 교체**
  - `frontend/src/app/dashboard/portfolios/[id]/page.tsx:822,843` — 보유종목/거래내역 삭제 확인 raw div 오버레이 제거
  - `portfolios/page.tsx` 의 shadcn AlertDialog 패턴으로 통일 (role=alertdialog, focus trap 자동 처리)
  - 파일: `frontend/src/app/dashboard/portfolios/[id]/page.tsx`
