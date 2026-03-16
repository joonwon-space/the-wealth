# THE WEALTH — TODO (미래 로드맵)

이 문서는 **중장기 백로그**다. 당장 하지 않지만 언젠가 해야 할 일을 관리한다.
현재 바로 실행할 작업은 `tasks.md`에 있다.

`/discover-tasks` 커맨드가 이 문서를 갱신한다.

---

## 완료된 마일스톤

<details>
<summary>Milestone 1~9 (모두 완료)</summary>

### Milestone 1: 백엔드 초기화 & DB 스캐폴딩
- [x] PostgreSQL 연결, SQLAlchemy async, Alembic, 5개 테이블 모델

### Milestone 2: 인증 인프라
- [x] JWT access/refresh, bcrypt, register/login/refresh API, IDOR 방지

### Milestone 3: Next.js 앱 라우터 레이아웃
- [x] 사이드바, 테마, 로그인/회원가입, 대시보드, Axios 인터셉터, Zustand

### Milestone 4: KIS API 연동 & 종목 검색
- [x] KIS 토큰 캐싱, 종목 검색, holdings CRUD, 국내/해외 현재가

### Milestone 5: 대시보드 시각화 & 실시간 수익 계산
- [x] 대시보드 요약 API, 도넛 차트, 보유 종목 테이블, 한국 증시 컬러

### Milestone 6: 자동 계좌 연동
- [x] AES-256 암호화, KIS 계좌 잔고 조회, Reconciliation, APScheduler

### Milestone 7: 프론트엔드 UI 완성
- [x] 인증 플로우, 포트폴리오 CRUD UI, 종목 관리 UI, 대시보드 빈 상태, 설정 페이지

### Milestone 8: Python 3.10+ 업그레이드
- [x] Python 3.9.6 → 3.12.13 업그레이드 (venv 재생성)
- [x] python-multipart 0.0.22 업그레이드 (CVE 해결)
- [x] `from __future__ import annotations` 제거, 네이티브 문법 사용

### Milestone 9: 기능 확장
- [x] 거래 기록 API & UI (테이블 + 필터 + 월별 매수/매도 bar chart)
- [x] 다중 계좌 & 실계좌 연동 (kis_accounts 테이블, POST /sync/balance)
- [x] 해외주식 검색 (NYSE/NASDAQ/AMEX 12,044종목)
- [x] 초성 검색 + 최근 검색어 localStorage

### 공통 / 인프라
- [x] Docker, Dockerfile, 환경변수, 에러 핸들링, Rate limiting, debounce
- [x] GitHub Actions CI/CD (lint → test → build)
- [x] Cmd+K 종목 검색, 비밀번호 변경 + refresh token revoke
- [x] 거래 기록 날짜 선택, 테이블 접근성, KIS price cache 5분 TTL

</details>

---

## Milestone 10: AI 브라우저 에이전트 & 자동 UI 수정

> **핵심 목표**: AI가 직접 사이트에 접속하여 UI 문제를 발견하고, 코드를 수정하고, 검증까지 하는 에이전트 구축

### 10-1. 브라우저 자동화 인프라 구축
- [ ] Playwright MCP 서버 프로젝트에 추가 (`claude mcp add playwright --scope project npx @playwright/mcp@latest`)
- [ ] `.mcp.json` 파일에 Playwright MCP 설정 추가 (팀 공유용)
- [ ] `.claude/launch.json` 에 frontend/backend dev server 설정 확인 및 보완
- [ ] Claude Preview 도구와 Playwright MCP 도구 비교 테스트 — 어떤 상황에서 어떤 도구가 적합한지 문서화

### 10-2. Visual QA 커맨드 (`/visual-qa`)
- [ ] `.claude/commands/visual-qa.md` 생성 — AI가 사이트 접속 → 스크린샷 → 이슈 탐지 → 수정 제안
- [ ] 워크플로우 정의:
  1. `preview_start` 로 dev server 시작
  2. `preview_screenshot` + `preview_snapshot` 으로 현재 상태 캡처
  3. 모바일(375px) / 태블릿(768px) / 데스크탑(1280px) 3가지 뷰포트에서 검사
  4. `preview_inspect` 으로 특정 요소 CSS 프로퍼티 확인 (색상, 간격, 폰트)
  5. 이슈 목록 생성 → 사용자 승인 → 코드 수정 → 재검증
- [ ] 반응형 레이아웃 검사 자동화 (overflow, 잘림, 겹침 탐지)
- [ ] 다크모드/라이트모드 양쪽에서 검사 (`preview_resize` + `colorScheme`)

### 10-3. 실시간 사이트 수정 커맨드 (`/fix-ui`)
- [ ] `.claude/commands/fix-ui.md` 생성 — 사용자가 "이 부분 고쳐줘" 라고 하면:
  1. 현재 페이지 스크린샷 촬영
  2. 문제 영역 `preview_inspect` 으로 CSS/DOM 분석
  3. 소스 코드 수정 (Edit 도구)
  4. 핫 리로드 대기 → 재촬영 → 비교
- [ ] 접근성(a11y) 검사 기능 포함 — ARIA 속성, 색상 대비, 키보드 네비게이션
- [ ] 컴포넌트별 비주얼 리그레션 탐지 로직

### 10-4. E2E 플로우 검증 커맨드 (`/e2e-check`)
- [ ] `.claude/commands/e2e-check.md` 생성 — 핵심 사용자 플로우 자동 검증:
  - 회원가입 → 로그인 → KIS 계정 등록 → 잔고 동기화 → 대시보드 확인
  - 포트폴리오 생성 → 종목 추가 → 거래 기록 → 분석 페이지
  - 종목 검색 (국내/해외/초성) → 종목 상세 → 캔들스틱 차트
- [ ] 각 단계에서 스크린샷 캡처 → 성공/실패 리포트 생성
- [ ] 실패 시 자동 디버깅: 콘솔 에러 확인 (`preview_console_logs`), 네트워크 에러 확인 (`preview_network`)

### 10-5. Vercel agent-browser 통합 (선택)
- [ ] `agent-browser` CLI 설치 및 Claude Code 스킬 추가
- [ ] 토큰 효율성 비교: Claude Preview vs Playwright MCP vs agent-browser
- [ ] 긴 검증 루프에서 컨텍스트 절약용으로 활용

---

## Milestone 11: 프론트엔드 고도화

### 11-1. 반응형 & 모바일 UX 개선
- [x] 거래 입력 폼 모바일 오버플로우 수정 (2-col grid, 전체 너비)
- [x] 보유 종목 테이블 모바일 카드 뷰 전환
- [x] 분석 페이지 성과 테이블 모바일 대응 (카드 뷰)
- [x] 대시보드 레이아웃 모바일 패딩 최적화 (p-4/md:p-6)
- [ ] 사이드바 드로어 제스처 지원 (swipe to close)
- [ ] PWA 지원 — `manifest.json`, Service Worker, 오프라인 캐시
- [ ] 모바일 하단 네비게이션 바 (사이드바 대체)

### 11-2. 분석 페이지 강화 (`/dashboard/analytics`)
- [ ] 포트폴리오 성과 시계열 차트 (일/주/월 단위) — 전체 자산 가치 추이
- [ ] 섹터/자산군별 배분 차트 (도넛 or 트리맵)
  - B/E: KIS 업종 코드 매핑 API 또는 수동 매핑 테이블
  - F/E: Recharts TreeMap or sunburst chart
- [ ] KOSPI200 / S&P500 벤치마크 대비 성과 오버레이
  - B/E: KIS 지수 시세 API 연동 (`FHKUP03500100`)
  - F/E: 라인차트에 벤치마크 오버레이 + 알파/베타 계산
- [ ] 배당 수익 추적
  - B/E: KIS 배당 정보 API 또는 외부 데이터 소스
  - F/E: 배당 캘린더 + 배당 수익률 차트
- [ ] 투자 성과 지표: 샤프 비율, MDD (최대 낙폭), CAGR 계산 및 표시
- [ ] 월별/연간 수익률 히트맵 (GitHub contribution chart 스타일)

### 11-3. 대시보드 개선
- [ ] "전일 대비" 변동률 배지 — 대시보드 요약 카드에 (▲ +2.3% / ▼ -1.5%)
- [x] 실시간 가격 업데이트 인디케이터 (마지막 업데이트 시간 + 수동 새로고침 버튼)
- [ ] 보유 종목 테이블에 52주 최고/최저 대비 현재 위치 바 (프로그레스 바)
- [ ] 드래그앤드롭 위젯 레이아웃 (react-grid-layout)
- [ ] 워치리스트 기능 — 보유하지 않은 관심 종목 모니터링

### 11-4. 종목 상세 페이지 (신규)
- [ ] `/dashboard/stocks/[ticker]` 라우트 생성
- [ ] 종목 기본 정보 (시가총액, PER, PBR, 배당수익률)
  - B/E: KIS 종목 마스터 상세 API 연동
- [ ] 캔들스틱 차트 + 이동평균선 (5/20/60/120일)
- [ ] 거래량 분석 차트
- [ ] 뉴스/공시 연동 (KIS 뉴스 API 또는 네이버 금융 크롤링)
- [ ] 내 보유 현황 오버레이 (평균 매입가 라인)

### 11-5. UX 편의 기능
- [ ] KIS 자격증명 등록 시 API 연결 테스트 (저장 전 유효성 검증)
  - B/E: `/users/kis-accounts/test` 엔드포인트 — 실제 KIS API 호출로 검증
  - F/E: "연결 테스트" 버튼 + 성공/실패 피드백
- [ ] 다국어 지원 (i18n) — next-intl 사용, 한국어/영어
- [x] 키보드 단축키 도움말 모달 (Cmd+? 로 열기)
- [ ] 알림 센터 — 인앱 알림 드롭다운 (목표가 도달, 동기화 결과, 에러)
- [ ] 온보딩 투어 — 첫 로그인 시 주요 기능 안내 (react-joyride)

---

## Milestone 12: 백엔드 고도화

### 12-1. 가격 히스토리 & 전일 대비
- [ ] `price_snapshots` 테이블 설계 (ticker, date, open, high, low, close, volume)
  - Alembic 마이그레이션 생성
  - 인덱스: (ticker, date) unique
- [ ] 장 마감 후 일별 종가 스냅샷 스케줄러 (APScheduler cron, KST 16:00)
  - 보유 종목만 대상으로 수집
  - KIS 일별 시세 API 활용
- [ ] "전일 대비" 변동률 계산 로직 — `GET /dashboard/summary` 응답에 추가
- [ ] 가격 히스토리 API: `GET /prices/{ticker}/history?from=&to=`

### 12-2. 실시간 가격 (WebSocket/SSE)
- [ ] FastAPI WebSocket 엔드포인트 설계
  - 클라이언트 연결 시 보유 종목 ticker 목록 전송
  - 서버: 주기적으로 KIS API 조회 → 변경분만 push
- [ ] SSE(Server-Sent Events) 대안 평가 — 구현 단순성 vs WebSocket 양방향
- [ ] 프론트엔드 WebSocket 클라이언트
  - Zustand 미들웨어로 실시간 가격 상태 관리
  - 연결 끊김 자동 재연결 (exponential backoff)
  - 시장 개장 시간에만 활성화

### 12-3. 성능 최적화
- [ ] 종목 검색 trie 구조 구현 or Redis ZRANGEBYLEX 인덱싱
  - 현재 O(n) 스캔 → O(log n) 검색으로 개선
- [ ] KIS 현재가 배치 API 탐색 (여러 종목 한번에 조회)
  - rate limit 대응: 요청 큐 + 레이트 리미터
- [ ] 대시보드 응답 캐싱 전략 개선
  - 사용자별 캐시 키 (user_id + portfolio_ids hash)
  - ETag/If-None-Match 헤더 지원
- [ ] 데이터베이스 쿼리 최적화
  - N+1 쿼리 탐지 및 수정 (SQLAlchemy selectinload/joinedload)
  - 느린 쿼리 로깅 (SQLAlchemy event 리스너)

### 12-4. 알림 시스템
- [ ] `alerts` 테이블 설계 (user_id, ticker, condition, threshold, is_active)
- [ ] 목표가 도달 감지 로직 (가격 조회 시 alert 조건 확인)
- [ ] 알림 전송 채널:
  - 웹 푸시 (Web Push API + VAPID 키)
  - 이메일 (SendGrid or AWS SES)
  - 텔레그램 봇 (선택)
- [ ] 일일 포트폴리오 리포트 이메일
  - 전일 대비 변동, 주요 종목 뉴스, 총 자산 추이

### 12-5. API 확장
- [ ] GraphQL 레이어 추가 (Strawberry) — 프론트엔드 데이터 요청 최적화
- [ ] API 버전관리 (`/api/v1/`, `/api/v2/`)
- [ ] OpenAPI 스키마 자동 생성 → 프론트엔드 타입 자동 생성 (openapi-typescript)
- [ ] Webhook 지원 — 외부 서비스 연동 (Slack, Discord, Zapier)

---

## Milestone 13: 데이터 파이프라인 & 분석

### 13-1. 외부 데이터 수집
- [ ] KOSPI200 / S&P500 일별 지수 데이터 수집 및 저장
  - KIS 지수 시세 API 또는 Yahoo Finance API (yfinance)
  - 일 1회 스케줄러로 수집
- [ ] 종목별 섹터/업종 매핑 테이블
  - KIS 업종 코드 활용 or FnGuide 데이터
  - `stock_metadata` 테이블: ticker, sector, industry, market_cap 등
- [ ] 배당 데이터 수집
  - KIS 배당 정보 API 또는 krx.co.kr 데이터
  - 배당 이력 테이블: ticker, ex_date, record_date, pay_date, amount
- [ ] 환율 데이터 수집 (USD/KRW)
  - 해외 주식 원화 환산용
  - 한국은행 ECOS API or 서울외국환중개 데이터

### 13-2. 포트폴리오 분석 엔진
- [ ] 일일 포트폴리오 가치 스냅샷 (전체 자산 + 종목별)
- [ ] 수익률 계산 엔진:
  - 시간 가중 수익률 (TWR) — 입출금 영향 제거
  - 금액 가중 수익률 (MWR/IRR)
- [ ] 리스크 지표 계산:
  - 변동성 (표준편차)
  - 샤프 비율 (위험 대비 수익)
  - 최대 낙폭 (MDD)
  - 베타 (시장 대비 민감도)
- [ ] 포트폴리오 상관관계 분석 (종목 간 상관계수)
- [ ] 자산 배분 리밸런싱 제안 (목표 비중 vs 현재 비중)

### 13-3. AI 기반 인사이트 (향후)
- [ ] Claude API 연동 — 포트폴리오 분석 요약 자동 생성
  - "이번 주 삼성전자가 -5% 하락했습니다. 반도체 업종 전반 약세..."
- [ ] 종목 뉴스 요약 (RSS + Claude 요약)
- [ ] 투자 패턴 분석 (매매 빈도, 평균 보유 기간, 손절/익절 비율)

---

## Milestone 14: 인프라 & 배포

### 14-1. 프로덕션 배포
- [ ] Vercel 배포 (프론트엔드)
  - `vercel.json` 설정
  - 환경변수: `NEXT_PUBLIC_API_URL` → 백엔드 프로덕션 URL
  - Preview 배포 → PR별 자동 프리뷰
- [ ] Railway or Fly.io 배포 (백엔드)
  - Dockerfile 최적화 (multi-stage build, slim 이미지)
  - 헬스체크 엔드포인트 활용
  - Auto-scaling 설정
- [ ] 프로덕션 PostgreSQL (Supabase or Neon)
  - 자동 백업, point-in-time 복구
  - Connection pooling (PgBouncer)
- [ ] 프로덕션 Redis (Upstash)
  - Serverless Redis, 글로벌 복제
  - 현재 캐시 키 전략 그대로 유지
- [ ] 프로덕션 환경변수 관리 (dotenv → Vault or AWS SSM)

### 14-2. 모니터링 & 관측성
- [ ] APM 도입 (Sentry)
  - 프론트엔드: `@sentry/nextjs` — 에러 트래킹, 성능 모니터링
  - 백엔드: `sentry-sdk[fastapi]` — 에러 트래킹, 트레이싱
- [ ] 로깅 인프라
  - 구조화 로깅 (structlog or loguru)
  - 로그 수집 (Datadog, Loki, or CloudWatch)
- [ ] 업타임 모니터링 (UptimeRobot or Betterstack)
- [ ] 알림 대시보드 (Grafana or Datadog Dashboard)
  - API 응답 시간, 에러율, KIS API 호출 횟수
  - Redis 캐시 히트율, DB 쿼리 시간

### 14-3. CI/CD 파이프라인 강화
- [ ] GitHub Actions: 프리뷰 배포 (PR 생성 시 Vercel preview)
- [ ] GitHub Actions: E2E 테스트 — Playwright (PR merge 전 필수)
- [ ] GitHub Actions: 보안 스캐닝 (Dependabot, CodeQL, Snyk)
- [ ] GitHub Actions: Docker 이미지 빌드 + Container Registry push
- [ ] 릴리스 자동화 — semantic-release (자동 버전 태깅, CHANGELOG 생성)

### 14-4. 보안 강화
- [ ] CORS 프로덕션 도메인 설정 (localhost:3000 → 실제 도메인)
- [ ] HTTPS 강제 적용 (HSTS 헤더)
- [ ] CSP (Content Security Policy) 헤더 설정
- [ ] API 키 로테이션 자동화
- [ ] 보안 감사 로그 — 로그인 시도, 설정 변경, 데이터 접근 이력
- [ ] 2FA (이중 인증) — TOTP (Google Authenticator 호환)

---

## Milestone 15: 사용자 경험 & 확장

### 15-1. 다중 증권사 지원
- [ ] 증권사 추상화 레이어 설계 (BrokerProvider 인터페이스)
  - `get_token()`, `fetch_holdings()`, `fetch_price()`, `search_stocks()`
- [ ] KIS 이외 증권사 커넥터 (미래에셋, 키움, NH투자)
  - Open API 지원 여부 확인 및 우선순위 결정
- [ ] 증권사별 설정 UI

### 15-2. 소셜 & 공유 기능
- [ ] 포트폴리오 성과 공유 (익명 링크, 종목명 마스킹 옵션)
- [ ] 스크린샷 공유 기능 — 포트폴리오 카드 이미지 생성 (html2canvas or satori)
- [ ] 투자 일지 기능 — 매매 이유, 메모 기록

### 15-3. 모바일 앱
- [ ] React Native 또는 Capacitor로 네이티브 앱 래핑
- [ ] 푸시 알림 (FCM)
- [ ] 생체 인증 (Face ID / 지문)
- [ ] 위젯 (iOS Widget / Android Widget) — 총 자산, 일일 수익률

### 15-4. 데이터 내보내기 & 세금
- [ ] 포트폴리오 데이터 CSV/Excel 내보내기
- [ ] 세금 신고용 양도소득 계산기
  - 국내 주식: 대주주 양도소득세
  - 해외 주식: 250만원 초과 양도차익 22% 과세
- [ ] 거래 내역 PDF 리포트 생성

---

## Milestone 16: 개발 도구 & DX 강화

### 16-1. Claude Code 에이전트 확장
- [ ] `visual-qa` 에이전트 생성 (`.claude/agents/visual-qa.md`)
  - Claude Preview 도구를 활용한 자동 UI 검사 에이전트
  - 뷰포트별 스크린샷 → 이슈 목록 → 자동 수정
- [ ] `e2e-runner` 에이전트 강화 — Playwright MCP 기반 실제 브라우저 테스트
- [ ] `perf-analyzer` 에이전트 생성 — Lighthouse CI + 번들 사이즈 분석
- [ ] `migration-reviewer` 에이전트 — Alembic 마이그레이션 안전성 검증

### 16-2. 테스트 인프라 강화
- [ ] Playwright E2E 테스트 셋업 (frontend)
  - 핵심 플로우: 로그인 → 대시보드 → 포트폴리오 → 거래
  - CI에서 실행 (GitHub Actions)
- [ ] 백엔드 테스트 커버리지 80% 달성 확인 및 리포트 자동화
- [ ] 비주얼 리그레션 테스트 (Chromatic or Percy)
  - 컴포넌트 스토리북 → 스냅샷 비교
- [ ] 부하 테스트 (Locust or k6)
  - API 엔드포인트별 응답 시간 벤치마크
  - KIS API rate limit 시뮬레이션

### 16-3. 코드 품질 도구
- [ ] Storybook 도입 — 컴포넌트 카탈로그 및 독립 개발
- [ ] openapi-typescript-codegen — 백엔드 OpenAPI 스키마에서 F/E 타입 자동 생성
- [ ] Turborepo or Nx — 모노레포 빌드 캐싱 및 태스크 오케스트레이션
- [ ] Husky + lint-staged — 커밋 전 자동 린트/포맷
- [ ] Commitlint — 커밋 메시지 형식 자동 검증

---

## 우선순위 가이드

| 우선순위 | 마일스톤 | 이유 |
|---------|---------|------|
| **P0** | 10 (AI 브라우저 에이전트) | 개발 생산성 극대화, 즉시 활용 가능 |
| **P0** | 14-1 (프로덕션 배포) | 실제 서비스 론칭 전제조건 |
| **P1** | 11-1 (모바일 UX) | 사용성 직결, 배포 전 해결 필요 |
| **P1** | 12-1 (가격 히스토리) | 핵심 기능 누락 (전일 대비 표시) |
| **P1** | 14-2 (모니터링) | 프로덕션 운영 필수 |
| **P2** | 11-2 (분석 페이지) | 차별화 기능 |
| **P2** | 12-2 (실시간 가격) | UX 향상 but 복잡도 높음 |
| **P2** | 13 (데이터 파이프라인) | 분석 기능의 전제조건 |
| **P2** | 16-1 (에이전트 확장) | DX 개선 |
| **P3** | 12-4 (알림) | nice-to-have |
| **P3** | 15 (확장) | 장기 로드맵 |
