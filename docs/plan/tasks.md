# THE WEALTH — Tasks

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
- [x] Fix: 해외주식 설정 페이지 평균단가 USD 표시 + 잔고 해외주식 포함
- [x] Fix: Redis stale cache fallback for exchange rate (1h fresh → 7d stale → 1450)
- [x] Fix: USD/KRW 환율 대시보드/설정 페이지 표시
- [x] Fix: 해외주식 52주 범위 — OverseasPriceDetail w52 필드 추가, dashboard 전달
- [x] Fix: HoldingsTable 해외주식 52주 범위 USD 포맷 표시
- [x] Fix: AllocationDonut custom tooltip (종목명, 비율%, 평가금액)
- [x] Fix: 종목 상세 API name 필드 + 해외주식 HHDFS00000300 지원
- [x] Fix: CAGR 실제 날짜 범위 사용 (최소 30일 guard)
- [x] Fix: 섹터 배분 해외주식 USD→KRW 환산
- [x] Fix: MetricCard 툴팁 fixed 포지션 (Card overflow:hidden 잘림 해결)

</details>

---

## Current work

### 🔴 Critical — 버그 수정 (P0)

- [x] **로그아웃 쿠키 미삭제 → /dashboard 재리다이렉트**
  - 현상: 로그아웃 클릭 → API 204 성공 → 브라우저 쿠키 미삭제 → `proxy.ts` 미들웨어가 `access_token` 쿠키 감지 → /dashboard로 재리다이렉트
  - 원인: `delete_cookie(domain=COOKIE_DOMAIN)`이 도메인 불일치로 쿠키 삭제 실패
  - 파일: `backend/app/api/auth.py:80-84` (`_clear_auth_cookies`), `frontend/src/proxy.ts:23-25`
  - 수정안: (A) `_clear_auth_cookies`에서 `domain=None`으로 한 번 더 삭제 시도, 또는 (B) `proxy.ts`에서 토큰 쿠키 존재 여부뿐 아니라 유효성(만료 시간)도 검증

- [x] **Analytics 태블릿(768px) 요약 카드 금액 잘림**
  - 현상: `sm:grid-cols-4` 레이아웃에서 768px일 때 4열 활성화 → 카드당 108px → 금액 텍스트(scrollWidth 110px)가 clientWidth(76px) 초과하여 잘림
  - 영향 카드: 총 자산 `₩103,634,739`, 투자 원금 `₩97,530,886`, 총 손익 `+6,103,852`
  - 파일: `frontend/src/app/dashboard/analytics/page.tsx` — 요약 카드 grid 클래스
  - 수정안: `sm:grid-cols-4` → `md:grid-cols-4`로 변경 (768px에서 2열 유지, 1024px부터 4열)

- [x] **포트폴리오 카드 아이콘 버튼 접근 불가**
  - 현상: 포트폴리오 카드 내 12x12px 아이콘 버튼에 텍스트/aria-label/title 없음 → 스크린 리더 완전 무접근, 터치 타겟도 44px 미달
  - 파일: `frontend/src/app/dashboard/portfolios/page.tsx` 또는 포트폴리오 카드 컴포넌트
  - 수정안: `aria-label="포트폴리오 메뉴"` 추가 + `min-w-[44px] min-h-[44px]` 터치 영역 확보

### 🟡 Warning — UX 개선 (P1)

- [x] **대시보드 보유종목 테이블 태블릿 가로 overflow**
  - 현상: 768px에서 테이블 실제 너비 1183px → 415px 초과, `수익금`, `수익률`, `전일 대비`, `52주 범위` 열이 화면 밖
  - 파일: `frontend/src/components/HoldingsTable.tsx`
  - 수정안: (A) 태블릿에서 `52주 범위` 열 숨김 (`hidden lg:table-cell`), 또는 (B) `overflow-x-auto` + 가로 스크롤 힌트 UI

- [x] **Analytics 종목별 성과 테이블 태블릿 가로 overflow**
  - 현상: 768px에서 테이블 1055px → 287px 초과
  - 파일: `frontend/src/app/dashboard/analytics/page.tsx` — 종목별 성과 테이블
  - 수정안: 위 보유종목 테이블과 동일 접근

- [x] **모바일 터치 타겟 44px 미달 (전 페이지)**
  - 미달 요소 목록:
    - "메뉴 열기" 버튼: 38x38px → 44x44px
    - "메뉴 닫기" 버튼: 28x28px → 44x44px
    - SSE "재연결" 버튼: 38px 높이 → 44px
    - 포트폴리오 카드 메뉴 버튼: 28x28px → 44x44px
    - Settings "계좌 추가" 버튼: 88x28px → 높이 44px
    - Settings "테스트" 버튼: 65x22px → 높이 44px
  - 수정안: 모바일 뷰포트에서 `min-h-[44px] min-w-[44px]` 적용, 또는 투명 패딩으로 터치 영역 확장

- [ ] **Settings 알림 폼 input label/aria-label 없음**
  - 현상: 목표가 알림 폼의 티커/종목명/목표가 input 3개 모두 `placeholder`만 있고 `<label>`이나 `aria-label` 없음
  - 파일: `frontend/src/app/dashboard/settings/page.tsx` — 알림 폼 섹션
  - 수정안: 각 input에 `aria-label="티커"`, `aria-label="종목명"`, `aria-label="목표가"` 추가

- [ ] **네비게이션 링크 `aria-current="page"` 부재**
  - 현상: 활성 페이지의 사이드바/하단 네비 링크에 시각적 하이라이트는 있으나 `aria-current="page"` 없음 → 스크린 리더 사용자가 현재 위치 파악 불가
  - 파일: `frontend/src/components/Sidebar.tsx`, `frontend/src/components/BottomNav.tsx` (또는 해당 레이아웃 컴포넌트)
  - 수정안: 현재 경로와 일치하는 링크에 `aria-current="page"` 속성 추가

- [ ] **SSE 연결 "연결 끊김 — 재연결" 항상 표시**
  - 현상: 배포 환경에서 SSE 연결이 맺어지지 않아 대시보드 헤더에 항상 "연결 끊김" 표시
  - 파일: `frontend/src/hooks/usePriceStream.ts` (또는 SSE 연결 훅), 백엔드 SSE 엔드포인트
  - 수정안: 배포 환경 SSE 엔드포인트 연결 확인 (CORS, 프록시 설정 등)

### 🟢 Minor — 개선 권장 (P2)

- [ ] **Settings 계좌 목록 소형 아이콘 버튼 접근성**
  - 현상: 12x12px, 14x14px 아이콘 버튼에 텍스트/aria-label 없음
  - 수정안: `aria-label` 추가

- [ ] **대시보드 새로고침 버튼 `aria-label` 부재**
  - 현상: `title="새로고침"`은 있으나 `aria-label` 없음 (title은 스크린 리더 지원 불일치)
  - 수정안: `aria-label="새로고침"` 추가

- [ ] **Cloudflare Analytics CSP 차단**
  - 현상: `static.cloudflareinsights.com` beacon.min.js가 CSP `script-src`에 의해 차단 → 콘솔 에러
  - 수정안: CSP 헤더에 `https://static.cloudflareinsights.com` 추가, 또는 Cloudflare Analytics 비활성화

- [ ] **CAGR/샤프 비율 "—" 사유 안내 텍스트 없음**
  - 현상: 데이터 부족 시 단순 "—" 표시 → 사용자가 왜 비어있는지 모름
  - 수정안: "—" 아래 또는 hover 시 "데이터 30일 이상 필요" 등 안내 표시

- [ ] **해외주식 상세 페이지 장외 시간 가격 빈칸**
  - 현상: 미국 장 마감 후 시가/고가/저가/전일종가 모두 "—"
  - 수정안: 캐시된 전일 종가 표시 또는 "미국 장 마감 (다음 개장: HH:MM KST)" 안내

### 데이터/API 이슈 (P1)

- [ ] **해외주식 52주 범위 "—" 표시**
  - 현상: KIS HHDFS00000300 API 응답에 `w52hgpr`/`w52lwpr` 필드가 없거나 빈 값
  - 수정안: 별도 API(`HHDFS76410000` 등)로 조회하는 fallback 추가

- [ ] **섹터 배분 "기타 100%"**
  - 현상: `sector_map`에 국내 ETF 종목(381170, 481190, 0087F0 등) 매핑 없음
  - 수정안: ETF 기초지수 기반 섹터 분류 추가 (미국테크=IT, 미국S&P500=혼합, 미국배당=배당)

- [ ] **해외주식 캔들차트 미지원**
  - 현상: 종목 상세 페이지에서 해외주식은 차트 영역 비어 있음 (국내만 chart API 호출)
  - 수정안: 해외주식 일봉 API 연동 또는 "차트 미지원" 안내 메시지

### 배포 후 확인 필요

- [ ] 섹터 배분 USD→KRW 환산 반영 확인 (IT 비중 0% → 정상값)
- [ ] 해외주식 52주 범위 데이터 확인 (— → 실제 범위 표시)
- [ ] CAGR이 30일 이상 데이터 쌓이면 정상 계산되는지 확인
