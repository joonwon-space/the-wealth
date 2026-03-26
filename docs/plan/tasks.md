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
- [x] Fix: 알림 벨 버튼 가리는 문제 (데스크탑 md:pr-6 → md:pr-16)
- [x] Fix: 포트폴리오 총 평가금액에 해외주식 미포함 (`cash-balance` 국내+해외 합산)
- [x] Fix: 설정 실계좌 조회 총 평가·주식 평가에 해외주식 미반영 (output2 방어 처리 + fallback)
- [x] Fix: 설정 실계좌 조회 종목 테이블에 "총 금액" 컬럼 추가 및 내림차순 정렬
- [x] All Trading Feature items (Step 1~8)
- [x] All UI Upgrade Phase 1~5 items

</details>

---

## Current work

### 브랜드 컬러 시스템 적용

- [x] **style: 주요 컬러를 #1e90ff(블루) + #00ff00(그린) 듀얼 팔레트로 교체**
  - `frontend/src/app/globals.css`
    - Light 모드: `--primary: #1e90ff` (도저블루), `--secondary: #00ff00` (네온그린)
    - Dark 모드: 동일 컬러 유지 (이미 충분한 명도)
    - `--primary-foreground`: `#ffffff` (블루 위 흰 텍스트)
    - `--secondary-foreground`: `#000000` (그린 위 검정 텍스트 — 가독성)
    - 차트 팔레트 1번: `#1e90ff`, 2번: `#00ff00` 로 교체 (나머지 6색 유지)
  - `frontend/src/app/globals.css` — `.text-primary` 유틸 자동 반영
  - 사이드바 active indicator, BottomNav pill, 버튼 primary 자동 반영 (CSS 변수 참조 중)
  - 대시보드 총 자산 카드 숫자 accent: amber → `#1e90ff`로 교체
  - 포트폴리오 히스토리 차트 라인 컬러: indigo → `#1e90ff`
  - `frontend/src/components/AllocationDonut.tsx` — `CHART_COLORS_FALLBACK[0]` = `#1e90ff`, `[1]` = `#00ff00`
  - 빌드 확인: `npx tsc --noEmit && npm run build`

---

### 계정 정보 변경 기능

#### Step 1 — 백엔드 모델 & API

- [x] **feat: users.name 컬럼 추가 + GET/PATCH /users/me**
  - `backend/app/models/user.py` — `name: Mapped[Optional[str]]` 컬럼 추가 (String(100))
  - Alembic migration: `add_user_name_column`
  - `backend/app/schemas/user.py` — `UserMe`, `UserUpdate(name)` 스키마 추가
  - `backend/app/api/users.py` — `GET /users/me` (이메일·이름 반환), `PATCH /users/me` (이름 변경)
  - 테스트: `backend/tests/test_users.py` — GET/PATCH 케이스

- [x] **feat: 비밀번호 변경 API**
  - `backend/app/api/users.py` — `POST /users/me/change-password`
    - Body: `{ current_password, new_password }` (new_password 최소 8자)
    - 현재 비밀번호 bcrypt 검증 → 불일치 시 400
    - 새 비밀번호 해싱 후 DB 저장
    - 성공 시 기존 refresh token 무효화 (Redis `refresh:{user_id}` 삭제)
  - `backend/app/schemas/user.py` — `ChangePasswordRequest` 스키마
  - 테스트: 성공/현재PW불일치/짧은PW 케이스

- [x] **feat: 이메일 변경 API**
  - `backend/app/api/users.py` — `POST /users/me/change-email`
    - Body: `{ new_email, current_password }`
    - 현재 비밀번호 검증 → 불일치 시 400
    - 이미 사용 중인 이메일이면 409
    - DB 이메일 업데이트 + refresh token 무효화
  - `backend/app/schemas/user.py` — `ChangeEmailRequest` 스키마
  - 테스트: 성공/PW불일치/중복이메일 케이스

- [x] **feat: 회원 탈퇴 API**
  - `backend/app/api/users.py` — `DELETE /users/me`
    - Body: `{ current_password }` (비밀번호 재확인)
    - 현재 비밀번호 검증
    - Cascade: portfolios → holdings/transactions/orders/alerts/notifications 삭제
    - kis_accounts, watchlist 삭제
    - users 레코드 삭제
    - Redis 토큰 무효화
  - 테스트: 성공/PW불일치 케이스, cascade 삭제 확인

#### Step 2 — 프론트엔드 UI

- [x] **feat: 설정 페이지 "계정 정보" 섹션 추가**
  - `frontend/src/app/dashboard/settings/page.tsx` 상단에 계정 섹션 추가
  - 현재 이메일 표시 (읽기 전용)
  - 이름 인라인 편집 (클릭 → input → blur/enter 시 PATCH 저장)
  - TanStack Query로 `GET /users/me` 조회 + `PATCH /users/me` mutation

- [x] **feat: 비밀번호 변경 UI**
  - 설정 페이지 계정 섹션 내 "비밀번호 변경" 버튼
  - shadcn Dialog: 현재 비밀번호 + 새 비밀번호 + 확인 입력
  - 클라이언트 검증: 새 비밀번호 8자 이상, 확인 일치
  - 성공 시 toast + Dialog 닫기, 실패 시 인라인 에러 메시지

- [x] **feat: 이메일 변경 UI**
  - 설정 페이지 계정 섹션 내 "이메일 변경" 버튼
  - shadcn Dialog: 새 이메일 + 현재 비밀번호 입력
  - 성공 시 로컬 상태 갱신 + toast, 실패 시 인라인 에러

- [x] **feat: 회원 탈퇴 UI**
  - 설정 페이지 최하단 "위험 구역" 섹션 (빨간 테두리 카드)
  - "계정 삭제" 버튼 클릭 → 경고 Dialog (복구 불가 안내)
  - Dialog 내 현재 비밀번호 입력 + "영구 삭제" 확인 버튼
  - 성공 시 zustand logout() → `/login` 리다이렉트

---

### Milestone 11-3: Target Asset Progress Widget

- [x] **feat: portfolios.target_value 컬럼 추가 + PATCH API**
  - `backend/app/models/portfolio.py` — `target_value: Mapped[Optional[int]]` 컬럼 추가
  - Alembic migration: `add_portfolio_target_value`
  - `backend/app/api/portfolios.py` — `PATCH /portfolios/{id}` 엔드포인트 (name, target_value 수정)
  - `backend/app/schemas/portfolio.py` — `PortfolioUpdate` 스키마 추가
  - 테스트: `backend/tests/test_portfolios.py`에 PATCH 케이스 추가

- [x] **feat: 포트폴리오 목표 금액 달성률 위젯 (프론트엔드)**
  - `frontend/src/app/dashboard/portfolios/[id]/page.tsx` — 포트폴리오 상세 상단에 목표 달성률 프로그레스 바 추가
  - `target_value` 미설정 시 숨김; 설정 시 현재 평가금액 / 목표금액 진행률 바 + % 표시
  - 목표 금액 인라인 편집 (클릭 → input, blur → PATCH 호출)
  - TanStack Query mutation + optimistic update

### Milestone 11-2: Analytics API 개선

- [x] **feat: `/analytics/portfolio-history` period query param 추가**
  - `backend/app/api/analytics.py` — `period: str = "ALL"` query param (1M/3M/6M/1Y/ALL)
  - DB 쿼리 시 날짜 필터 적용 (불필요한 오래된 데이터 제외)
  - 캐시 키에 period 포함 (`analytics:{user_id}:portfolio-history:{period}`)
  - `backend/app/schemas/analytics.py` — 변경 없음
  - 테스트: `backend/tests/test_analytics.py`에 period 파라미터 케이스 추가

- [x] **feat: 분석 페이지 히스토리 차트 기간 필터 API 연동**
  - `frontend/src/app/dashboard/analytics/page.tsx` — period 변경 시 클라이언트 필터링 대신 API 재호출
  - `historyPeriod` state 변경 → `api.get("/analytics/portfolio-history", { params: { period } })` 호출
  - TanStack Query `useQuery`로 마이그레이션 (캐싱 + 자동 갱신)

### Milestone 12-5: 트랜잭션 커서 기반 페이지네이션

- [x] **feat: transactions 목록 커서 기반 페이지네이션**
  - `backend/app/api/portfolios.py` — `GET /portfolios/{id}/transactions` 에 `cursor` (last id), `limit` (default 20) query param
  - 응답: `{ items: [...], next_cursor: id | null, has_more: bool }`
  - 테스트 추가

- [x] **feat: 거래 내역 무한 스크롤 (프론트엔드)**
  - `frontend/src/app/dashboard/portfolios/[id]/page.tsx` 거래 내역 테이블에 "더 보기" 버튼 추가
  - TanStack Query `useInfiniteQuery` 사용
  - 초기 20건 로드 → "더 보기" 클릭 시 다음 20건 append

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

## UI Upgrade — 프리미엄 디자인 개편

### Phase 1 — 색상 시스템 & 기반 (임팩트 최대, 전체 앱 변화)

- [x] **style: 프리미엄 금융 앱 색상 팔레트로 개편 (`globals.css`)**
  - 현재 neutral gray → 짙은 slate 기반 다크 테마로 전환 (다크 모드를 기본으로)
  - Primary accent: `#6366F1` (인디고) — 주요 액션 버튼, 활성 상태
  - Highlight amber: `#F59E0B` — 총 자산, 수익 강조 숫자
  - Card 배경: `oklch(0.18 0.01 250)` (짙은 slate), glassmorphism용 반투명 변수 추가
  - 차트 색상 변수 (`--chart-1` ~ `--chart-8`): 멀티컬러 팔레트 (인디고·에메랄드·앰버·로즈·바이올렛·시안·오렌지·그린)
  - 기존 한국 증시 색상(`#E31F26` 상승, `#1A56DB` 하락)은 유지
  - 파일: `frontend/src/app/globals.css`

- [x] **style: 타이포그래피 위계 강화**
  - 총 자산 숫자: `text-4xl font-bold tabular-nums tracking-tight`
  - 섹션 헤더: `text-xs font-semibold uppercase tracking-widest text-muted-foreground`
  - 메트릭 레이블: `text-xs text-muted-foreground`
  - 숫자 데이터: `font-mono tabular-nums` 일관 적용
  - 파일: `frontend/src/app/globals.css` (커스텀 CSS 클래스 추가)

### Phase 2 — 대시보드 메트릭 카드 리디자인 (첫인상 개선)

- [x] **feat: 대시보드 요약 카드 프리미엄 리디자인**
  - 현재 평면 4 카드 → 총 자산 Large 카드(상단 전체 너비) + 하단 3 카드 그리드 레이아웃
  - 총 자산 카드: 앰버 액센트 숫자, 일간 변동 퍼센트 + 화살표 아이콘, 7일 미니 sparkline (Recharts `AreaChart`)
  - 투자 원금 / 예수금 / 총 손익 카드: 아이콘(Lucide) + 컬러 상단 바 (손익: 빨강/파랑 동적)
  - 카드 배경: 반투명 glassmorphism (`backdrop-blur-sm bg-card/60 border border-white/10`)
  - 파일: `frontend/src/app/dashboard/page.tsx`

- [x] **feat: 보유 종목 빠른 요약 — Top 3 종목 위젯 추가**
  - 대시보드 상단 메트릭 카드 아래에 "수익 상위 3종목" 가로 위젯 추가
  - 종목명 + 티커 + 수익률 + 미니 바 인디케이터
  - 파일: `frontend/src/app/dashboard/page.tsx`, `frontend/src/components/TopHoldingsWidget.tsx`

### Phase 3 — 사이드바 & 네비게이션 리디자인 (프로페셔널 느낌)

- [x] **feat: 사이드바 Vercel/Linear 스타일 리디자인**
  - 로고 영역: 앱 이름 "THE WEALTH" + 작은 마름모 로고 아이콘 (SVG)
  - 활성 메뉴 아이템: 왼쪽 2px 인디고 컬러 바 + 배경 `bg-accent` + 텍스트 `text-foreground font-medium`
  - 비활성 메뉴 아이템: `text-muted-foreground hover:text-foreground` 전환 애니메이션 (`transition-colors duration-150`)
  - 하단 사용자 프로필 고정: 아바타(이니셜 원형) + 이름 + 설정 아이콘
  - 사이드바 하단 경계: 미묘한 `border-t border-border/50` 구분선
  - 파일: `frontend/src/components/Sidebar.tsx`

- [x] **feat: 모바일 하단 네비게이션 개선**
  - 현재 단순 아이콘+텍스트 → 활성 탭 인디고 pill 배경 + 아이콘 색상 전환
  - 활성 탭 미세한 scale-up 애니메이션 (`transition-transform duration-150`)
  - 파일: `frontend/src/components/BottomNav.tsx`

### Phase 4 — 데이터 테이블 & 차트 시각화 (데이터 가독성)

- [x] **feat: HoldingsTable 시각화 강화**
  - 종목명 컬럼: 굵은 폰트 + 티커를 `text-muted-foreground text-xs`로 하위 표시 (2줄 레이아웃)
  - 수익률 컬럼: 숫자 옆에 미니 bar 인디케이터 (0% 기준선 기준 좌우로 채워지는 바, 너비 최대 60px)
  - 현재가 컬럼: 전일 대비 상승/하락 시 행 배경 미세 틴팅 (`bg-red-950/10` 또는 `bg-blue-950/10`)
  - 수량 컬럼 제거 or 숨기기 옵션 추가 (화면 공간 효율화)
  - 파일: `frontend/src/components/HoldingsTable.tsx`

- [x] **feat: 자산 배분 도넛 차트 색상 & 스타일 개선**
  - 기존 파란 계열 단조로운 팔레트 → Phase 1에서 정의한 8색 멀티컬러 팔레트 적용
  - 도넛 중앙 텍스트: 총 평가금액 대신 "TOP 종목명 + 비중%" 표시로 인터랙티브 변경 (hover 시)
  - 범례: 아이콘 원형 12px + 종목명 + 비중% + 금액 3열 구조로 재배치
  - 파일: `frontend/src/components/AllocationDonut.tsx`

- [x] **feat: 포트폴리오 히스토리 차트 스타일 개선**
  - 라인 색상: 인디고 그라디언트 (`#6366F1` → `#818CF8`), 영역 fill 반투명
  - 수익률 양수/음수에 따라 라인 색상 동적 변경 (양수: 인디고/빨강, 음수: 파랑)
  - 커스텀 툴팁: 날짜 + 총 평가금액 + 수익률 + 투자 원금 (shadcn Card 스타일)
  - 파일: `frontend/src/components/PortfolioHistoryChart.tsx`

### Phase 5 — 마이크로 인터랙션 & 폴리싱 (고급스러운 완성도)

- [x] **feat: 숫자 카운트업 애니메이션 (`useCountUp` hook)**
  - 대시보드 로드 시 총 자산, 손익 숫자가 0에서 실제 값으로 카운트업
  - `frontend/src/hooks/useCountUp.ts` 신규 생성 (requestAnimationFrame 기반, 1.2s 이징)
  - 대시보드 요약 카드에 적용
  - 파일: `frontend/src/hooks/useCountUp.ts`, `frontend/src/app/dashboard/page.tsx`

- [x] **feat: 로딩 Skeleton UI 통일 (Unified Skeleton)**
  - 현재 `TableSkeleton`만 존재 → 카드 스켈레톤, 차트 스켈레톤 추가
  - `frontend/src/components/CardSkeleton.tsx` — 메트릭 카드 모양 스켈레톤 (pulse 애니메이션)
  - `frontend/src/components/ChartSkeleton.tsx` — 차트 영역 스켈레톤
  - 대시보드 페이지의 모든 로딩 상태에 적용
  - 파일: `frontend/src/components/CardSkeleton.tsx`, `frontend/src/components/ChartSkeleton.tsx`

- [x] **feat: 페이지 전환 fade-in 애니메이션**
  - 대시보드 페이지 진입 시 콘텐츠 순차 fade-in (`opacity-0 → opacity-100`, stagger 효과)
  - Tailwind `animate-in fade-in` 클래스 활용 (tailwindcss-animate 패키지)
  - 카드별 `animation-delay` 순차 적용 (0ms, 100ms, 200ms, 300ms)
  - 파일: `frontend/src/app/dashboard/page.tsx`, `frontend/tailwind.config.ts`

---

### Milestone 11-2: Analytics 기간 필터 확장 + 브레이크이븐 시각화

- [x] **feat: portfolio-history 1W 기간 추가 + analytics 페이지 연동**
  - `backend/app/api/analytics.py` — `HistoryPeriod` Literal에 `"1W"` 추가, `_period_cutoff` 에 `1W` → `today - timedelta(days=7)` 처리
  - `backend/app/api/analytics.py` — `invalidate_analytics_cache` 에 `"1W"` 포함
  - `backend/tests/test_analytics.py` — `1W` period 케이스 추가
  - `frontend/src/app/dashboard/analytics/page.tsx` — `historyPeriod` 타입에 `"1W"` 추가, PortfolioHistoryChart `onPeriodChange` 에 `"1W"` 전달
  - `frontend/src/components/PortfolioHistoryChart.tsx` — PERIODS 배열에 `"1W"` 추가 (버튼 UI)

- [x] **feat: HoldingsTable 브레이크이븐 마커 (평균 매입가 52주 범위 내 표시)**
  - `frontend/src/components/HoldingsTable.tsx` — `w52_range` 컬럼 cell 내 avg_price 마커 추가
  - 52주 범위 바 위에 avg_price 위치를 흰색 세로선(`|`)으로 표시
  - avg_price 가 low~high 범위 밖이면 마커 숨김
  - 마커에 `title` 속성으로 `평균매입가: {formatPrice(avg_price)}` 툴팁 추가
  - 테스트: `frontend/src/components/HoldingsTable.test.tsx` — 마커 렌더링 케이스 추가

### Milestone 12-5: sync_logs 커서 기반 페이지네이션

- [ ] **feat: sync_logs 커서 기반 페이지네이션**
  - `backend/app/api/sync.py` — `GET /sync/logs` 에 `cursor` (last id), `limit` (default 50) query param 추가
  - `cursor` 없으면 최신 50건 반환, `cursor` 있으면 해당 id 미만의 레코드 반환
  - 응답: `{ items: [...], next_cursor: int | null, has_more: bool }`
  - 기존 `offset` param 제거 (하위 호환 불필요 — 프론트엔드 미사용)
  - `backend/tests/test_sync.py` — cursor 페이지네이션 케이스 추가

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

- [x] **feat: 주문 TanStack Query 훅 (`hooks/useOrders.ts`)**
  - `frontend/src/hooks/useOrders.ts` 신규 생성
  - `useCashBalance(portfolioId)`: 예수금 + 총평가 조회, 30초 폴링
  - `useOrderableQuantity(portfolioId, ticker, price, orderType)`
  - `usePlaceOrder(portfolioId)`: 주문 실행 mutation, 성공 시 캐시 무효화
  - `usePendingOrders(portfolioId)`: 미체결 주문 조회, 30초 폴링
  - `useCancelOrder(portfolioId)`: 주문 취소 mutation
  - Order 관련 TypeScript 타입 추가

### Step 6 — 프론트엔드 UI

- [x] **feat: 주문 다이얼로그 컴포넌트 (`OrderDialog.tsx`)**
  - `frontend/src/components/OrderDialog.tsx` 신규 생성
  - shadcn/ui `Dialog` + `Tabs` 기반 (매수/매도 탭)
  - 지정가/시장가 선택, 수량 퀵 버튼 (10%/25%/50%/100%)
  - 주문금액·예수금·수수료 실시간 표시
  - 메모 필드 (transactions.memo 연계)
  - 주문 버튼 클릭 → 확인 다이얼로그 → 최종 실행
  - 매수=빨간색, 매도=파란색 (한국 컬러 컨벤션)

- [x] **feat: 미체결 주문 패널 (`PendingOrdersPanel.tsx`)**
  - `frontend/src/components/PendingOrdersPanel.tsx` 신규 생성
  - 30초 폴링으로 자동 갱신
  - 체결 완료 시 sonner toast 알림
  - 주문 취소 버튼

- [x] **feat: 포트폴리오 상세 페이지 개편**
  - `frontend/src/app/dashboard/portfolios/[id]/page.tsx` 수정
  - 상단 요약 영역: 총 평가금액 + 예수금(현금) + 총 수익률 표시
  - [신규 종목 매수] [전체 동기화] [미체결 주문 (N)] 버튼 추가
  - KIS 연결 안 된 포트폴리오는 예수금 영역 숨기고 기존 UI 유지
  - `HoldingsTable`에 [매수][매도] 버튼 추가 (KIS 연결 포트폴리오에서만 표시)
  - 신규 종목 매수: StockSearch → OrderDialog 자동 열림 플로우

- [x] **feat: 대시보드 및 포트폴리오 목록에 예수금 표시**
  - `frontend/src/app/dashboard/page.tsx`: 총 자산(평가+예수금) 표시
  - `frontend/src/app/dashboard/portfolios/page.tsx`: 포트폴리오 카드에 예수금 필드 추가

### Step 7 — 설정 페이지 확장

- [x] **feat: KIS 계좌 설정에 계좌 유형·모의투자 옵션 추가**
  - `frontend/src/app/dashboard/settings/page.tsx` 수정
  - 계좌 유형 선택 드롭다운 (일반/ISA/연금저축/IRP/해외주식)
  - 모의투자/실전투자 토글 (`is_paper_trading`)
  - 1회 주문 금액 상한 설정 입력 필드

### Step 8 — E2E 테스트

- [x] **test: 주문 플로우 E2E (Playwright)**
  - 정상 매수/매도 플로우
  - 에러 케이스: 예수금 부족, 장외 시간
  - 미체결 주문 취소 플로우
