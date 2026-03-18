# THE WEALTH — Tasks

Current work items. Read by `/auto-task` and `/next-task`.
Each item should be completable in a single commit.

---

- [x] `filelock` 3.19.1 → 3.25.2 업그레이드 (GHSA-w853-jp5j-5j7f, GHSA-qmgc-5h2g-mvrw)
- [x] `python-jose` → `PyJWT` 마이그레이션 (`ecdsa` 취약점 GHSA-wj6h-64fc-37mp 해소)
- [x] `passlib` → `bcrypt` 직접 사용으로 마이그레이션 (Python 3.13 `crypt` 모듈 제거 대비)
- [x] `backend/.env.example`에 `CORS_ORIGINS` 항목 추가
- [x] KIS 자격증명 등록 시 API 연결 테스트 엔드포인트 (B/E: `/users/kis-accounts/{id}/test`)
- [x] KIS 자격증명 연결 테스트 UI ("연결 테스트" 버튼 + 성공/실패 피드백)

## Milestone 12-1: 가격 히스토리 & 전일 대비

- [x] `price_snapshots` SQLAlchemy 모델 생성 + Alembic 마이그레이션
- [x] KIS 전일 종가 조회 서비스 함수 (`FHKST01010100`)
- [x] APScheduler 장 마감 스냅샷 job 추가 (KST 16:05, 보유 종목 대상)
- [x] `GET /dashboard/summary` 응답에 종목별 `day_change_rate` 추가
- [x] 대시보드 프론트엔드에 전일 대비 배지 표시 (▲ +1.2% / ▼ -0.8%)

## Milestone 11-1: 모바일 UX

- [x] 사이드바 드로어 스와이프로 닫기 제스처 (swipe left to close)
- [x] 가격 히스토리 API `GET /prices/{ticker}/history`
- [x] analytics 페이지 `day_change_rate` 컬럼 반영
- [x] 대시보드 요약 카드에 포트폴리오 전일 대비 변동률 배지 (`total_day_change_rate`)

## Milestone 11-3: 보유 종목 테이블 52주 고/저

- [x] `PriceDetail`에 `w52_high` / `w52_low` 추가 (FHKST01010100 응답 활용)
- [x] dashboard API 응답 `HoldingWithPnL`에 `w52_high` / `w52_low` 추가
- [x] 보유 종목 테이블에 52주 범위 프로그레스 바 컬럼 추가

## Milestone 12-2: SSE 실시간 가격

- [x] `GET /prices/stream` SSE 엔드포인트 — 보유 종목 가격 30초 간격 push
- [x] 프론트엔드 SSE 클라이언트 — 대시보드 가격 실시간 업데이트 (시장 개장 시간 한정)

## Milestone 11-2: 분석 페이지 강화

- [x] 투자 성과 지표 계산 API (`GET /analytics/metrics`) — 샤프 비율, MDD, CAGR, 총 수익률
- [x] 분석 페이지에 성과 지표 카드 표시

## Milestone 12-3: 성능 최적화

- [x] 대시보드 API KIS 중복 호출 제거 — `fetch_domestic_price_detail` 단일 호출로 통합
- [x] 백엔드 유닛 테스트 추가 — analytics 지표 계산 (CAGR, MDD, Sharpe)
- [x] 백엔드 유닛 테스트 추가 — price snapshot 서비스 (save_snapshots, get_prev_close)
- [x] 월별 수익률 데이터 API (`GET /analytics/monthly-returns`) + 분석 페이지 히트맵

## Milestone 11-1: PWA & 모바일 네비게이션

- [x] PWA 지원 — `manifest.json` + `<link rel="manifest">` + 앱 아이콘 (192/512px)
- [x] 모바일 하단 네비게이션 바 — 대시보드·분석·포트폴리오·설정 탭 (md:hidden)

## Milestone 12-3b: 쿼리 최적화

- [x] `GET /dashboard/summary` holdings 조회에 selectinload 제거 — N+1 없음 확인 + 느린 쿼리 로깅 추가
- [x] `analytics.py` `get_metrics`에서 `fetch_prices_parallel` → `fetch_domestic_price_detail` 단일 호출로 교체 (dashboard와 동일하게)

## Milestone 11-4: 종목 상세 페이지

- [x] `GET /stocks/{ticker}/detail` B/E — KIS 종목 기본 정보 (시가총액, PER, PBR, 배당수익률) `FHKST01010100` output 활용
- [x] `/dashboard/stocks/[ticker]` 프론트엔드 라우트 — 캔들스틱 차트 + 기본 정보 카드 + 내 보유 현황 오버레이

## Milestone 14: 인프라

- [x] Dockerfile 멀티스테이지 빌드 최적화 (backend) — builder + runtime 단계 분리, 이미지 슬림화

## Milestone 12-4: 알림 시스템 (기초)

- [x] `alerts` 테이블 + SQLAlchemy 모델 + Alembic 마이그레이션 (user_id, ticker, condition, threshold, is_active)
- [x] `POST /alerts` + `GET /alerts` + `DELETE /alerts/{id}` API
- [x] 대시보드 summary 응답 후 alert 조건 확인 로직 — 가격 도달 시 알림 생성 (`triggered_alerts` 응답 필드)
- [x] 프론트엔드: 설정 페이지에 목표가 알림 등록 UI + 알림 배지

## Milestone 13-1: 외부 데이터 & 분석 확장

- [x] `GET /analytics/portfolio-history` — price_snapshots 기반 일별 포트폴리오 총 가치 시계열 API
- [x] 분석 페이지 포트폴리오 가치 추이 선 차트 (Recharts LineChart, 기간 선택)
- [x] 백엔드 유닛 테스트 추가 — alerts API (create, list, delete, check_triggered_alerts)

## Milestone 16-2: 테스트 커버리지 강화

- [x] 백엔드 전체 테스트 커버리지 측정 + 80% 미달 모듈 목록 파악
- [x] `app/services/kis_token.py` 유닛 테스트 — TTL 파싱, 토큰 캐시 히트/미스
- [x] `app/api/portfolios.py` 통합 테스트 강화 — 다중 포트폴리오 holdings 쿼리 검증

## Milestone 11-5: UX 편의 기능

- [x] 다크모드 토글을 설정 페이지에도 노출 (현재 사이드바만)
- [x] 분석 페이지 로딩 스켈레톤 개선 — MetricCard, heatmap, history chart 각각 개별 스켈레톤

## Milestone 12-5: API 품질 개선

- [x] `GET /portfolios/{id}/holdings` 응답에 현재가 포함 — `/with-prices` 엔드포인트 이미 존재
- [x] `PATCH /portfolios/holdings/{id}` 부분 업데이트 지원 — 이미 구현됨 (quantity/avg_price 독립적 수정)
- [x] 백엔드 전체 테스트 재실행 후 커버리지 리포트 갱신

## Milestone 16-2b: 테스트 커버리지 확대

- [x] `app/api/auth.py` 통합 테스트 강화 — refresh token rotation, 잘못된 비밀번호, 이미 등록된 이메일
- [x] `app/services/kis_price.py` 유닛 테스트 — cache hit, cache miss, fetch_prices_parallel 폴백 로직
- [x] `app/api/analytics.py` 통합 테스트 — get_metrics 빈 데이터, get_portfolio_history, get_monthly_returns

## Milestone 14-3 / 16-3: CI/CD & 코드 품질

- [x] `.github/dependabot.yml` 추가 — pip & npm 의존성 자동 보안 업데이트
- [x] GitHub Actions CodeQL 워크플로우 추가 — Python/JS 정적 보안 분석
- [x] 백엔드 CI에 커버리지 리포트 추가 — `--cov-report=xml` + Codecov 업로드
- [x] Husky + lint-staged 설정 — pre-commit에 ESLint 자동 실행
- [x] Commitlint 설정 — conventional commit 형식 강제 (`.commitlintrc.json`)

## Milestone 10: AI 브라우저 에이전트

- [x] `.mcp.json` 생성 — Playwright MCP 서버 설정 (팀 공유용)
- [x] `.claude/commands/visual-qa.md` 생성 — 스크린샷 → 이슈 탐지 → 수정 제안 워크플로우
- [x] `.claude/commands/fix-ui.md` 생성 — UI 문제 수정 커맨드 (스크린샷 → 분석 → 수정 → 재검증)
- [x] `.claude/commands/e2e-check.md` 생성 — 핵심 사용자 플로우 자동 검증 커맨드

## Milestone 16-1: Claude Code 에이전트 확장

- [x] `.claude/agents/visual-qa.md` 생성 — Playwright MCP 기반 자동 UI 검사 에이전트 (뷰포트별 스크린샷 → 이슈 탐지)
- [x] `.claude/agents/e2e-runner.md` 생성 — Playwright MCP 기반 실제 브라우저 E2E 테스트 에이전트
- [x] `.claude/agents/perf-analyzer.md` 생성 — 번들 사이즈 분석 + Lighthouse 점수 체크 에이전트
- [x] `.claude/agents/migration-reviewer.md` 생성 — Alembic 마이그레이션 안전성 검증 에이전트

## Milestone 16-2: Playwright E2E 테스트 셋업

- [x] frontend에 `@playwright/test` 설치 + `playwright.config.ts` 설정 (baseURL: localhost:3000)
- [x] E2E 테스트 파일 생성 — 로그인 플로우 (`e2e/auth.spec.ts`)
- [x] E2E 테스트 파일 생성 — 대시보드 + 포트폴리오 플로우 (`e2e/dashboard.spec.ts`)
- [x] GitHub Actions E2E 워크플로우 추가 (`.github/workflows/e2e.yml`) — PR 시 실행

## Milestone 16-3: openapi-typescript 타입 자동 생성

- [x] `openapi-typescript` 패키지 설치 + `frontend/src/types/api.ts` 자동 생성 스크립트 (`package.json` `generate:types` 스크립트)
- [x] 자동 생성된 타입으로 기존 `src/types/` 수동 타입 교체 (dashboard, portfolio, analytics 스키마)

## Milestone 11-2: 섹터 배분 차트

- [x] 수동 섹터 매핑 테이블 추가 (`backend/app/data/sector_map.py`) — 주요 종목 50개 섹터 분류 (IT, 금융, 헬스케어 등)
- [x] `GET /analytics/sector-allocation` API — 보유 종목의 섹터별 비중 반환
- [x] 분석 페이지에 섹터 배분 도넛 차트 추가 (Recharts PieChart)

## Milestone 11-3: 워치리스트

- [ ] `watchlist` SQLAlchemy 모델 + Alembic 마이그레이션 (user_id, ticker, name, market)
- [ ] `POST /watchlist` + `GET /watchlist` + `DELETE /watchlist/{id}` API
- [ ] 대시보드에 워치리스트 섹션 추가 — 관심 종목 현재가 표시 (SSE 스트림 활용)
