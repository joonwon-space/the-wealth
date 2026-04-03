# THE WEALTH — TODO (Future Roadmap)

Long-term backlog. Not urgent but eventually needed.
Current actionable work is in `tasks.md`.

`/discover-tasks` command refreshes this document.

---

## Completed Milestones

<details>
<summary>Milestone 1~9, 10, 11 (partial), 12 (partial incl. SSE hardening), 13-1, 14 (partial), 15-4, 16 (partial incl. commitlint) -- all completed</summary>

### Milestone 1-9: Foundation
- [x] Backend init, DB, Auth, Next.js layout, KIS API, Dashboard, Account sync, UI, Python upgrade, Feature extensions

### Milestone 10: AI Browser Agent
- [x] Playwright MCP, visual QA, fix-ui, e2e-check commands

### Milestone 11 (completed items)
- [x] 11-1: Mobile UX (responsive, card view, PWA, bottom nav, swipe gesture)
- [x] 11-2: Sector allocation chart
- [x] 11-3: Watchlist, real-time price indicator
- [x] 11-4: Stock detail page (`/dashboard/stocks/[ticker]`)
- [x] 11-5: Keyboard shortcuts dialog, Error Boundary, bundle optimization

### Milestone 12 (completed items)
- [x] 12-1: Price history & day change (price_snapshots, daily snapshot scheduler)
- [x] 12-2: SSE real-time prices (30s interval, market hours only, per-user limit, heartbeat, 2h timeout)
- [x] 12-3: Performance optimization (query optimization, Redis cache)
- [x] 12-4: Alert system (CRUD)
- [x] 12-5: API versioning (/api/v1), standardized error responses, openapi-typescript

### Milestone 13-1: Portfolio History
- [x] Portfolio history API + chart

### Milestone 14 (completed items)
- [x] Dockerfile multi-stage build
- [x] Structured logging (structlog)
- [x] CI/CD (GitHub Actions: lint, test, build, E2E, Docker, Dependabot, CodeQL)
- [x] Security headers (HSTS, CSP, X-Frame-Options, etc.)
- [x] Husky + lint-staged

### Milestone 15-4: Data Export
- [x] CSV export (holdings + transactions)

### Milestone 16 (completed items)
- [x] Test coverage 93% (577 tests)
- [x] Playwright E2E setup
- [x] openapi-typescript type generation
- [x] Short-term improvements (DB indexes, legacy columns, rate limits, ticker validation, pagination cap, soft delete, HttpOnly cookies, Graceful Shutdown)

### KIS Resilience (2026-03-21)
- [x] KIS API 장애 시 `RuntimeError` raise (빈 배열 반환 → reconciliation 오삭제 방지)
- [x] Dashboard `kis_status: "ok" | "degraded"` 필드 + 프론트 배너 표시

</details>

---

## P0 — DB 정리

### 0-2. users 테이블 레거시 KIS 컬럼 제거 ✅
`kis_accounts` 테이블로 이관 완료된 컬럼들이 `users`에 잔존.
- [x] Alembic migration: `kis_app_key_enc`, `kis_app_secret_enc`, `kis_account_no`, `kis_acnt_prdt_cd` drop (`c3d4e5f6a7b8_drop_legacy_user_kis_columns.py`)
- [x] `backend/app/models/user.py` 정리 완료 (레거시 컬럼 없음)

---

## Milestone 11: Frontend Enhancement (Remaining)

### 11-2. Analytics Page Enhancement
- [x] Portfolio performance period filter (1w / 1m / 3m / 6m / 1y / all 탭)
- [ ] KOSPI200 / S&P500 benchmark overlay (국내: `FHKUP03500100`, 해외: `FHKST03030100` `.SPX`/`.DJI`/`.IXIC`)
- [ ] Dividend income tracking (calendar + yield chart) — KIS `HHKDB669102C0` 배당일정, `HHKDB13470100` 배당률 상위
- [ ] Investment performance metrics: Sharpe ratio, MDD, CAGR (`backend/app/services/metrics.py`)
- [ ] Monthly/annual return heatmap (GitHub contribution chart style)

### 11-3. Dashboard Enhancement
- [x] 52-week high/low position bar in holdings table — HoldingsTable.tsx + 종목 상세 구현 완료
- [x] Target asset progress widget -- `portfolios.target_value` + 달성률 프로그레스 바 (`PATCH /portfolios/{id}`)

### 11-4. Stock Detail Page Enhancement
- [x] Fundamental data (market cap, PER, PBR, dividend yield) via KIS master API — stocks.py에서 FHKST01010100 조회 구현 완료
- [ ] Moving averages overlay (5/20/60/120 day)
- [ ] Volume analysis chart
- [ ] News/disclosure feed (KIS `FHKST01011800` 국내 시황/공시, `HHPSTH60100C1` 해외뉴스 — 제목 수준, 본문은 네이버 금융 등 보조 소스 필요)
- [ ] My holdings overlay (average purchase price horizontal line on candlestick chart)

### 11-5. UX Convenience
- [x] In-app notification center (price alerts → toast + notification list)
- [x] Trade memo & investment journal — `transactions.memo` 컬럼 + 인라인 편집

### 11-7. Frontend Quality
- [x] Bundle size budget — `@next/bundle-analyzer` + CI warning on budget exceed
- [x] Granular error boundaries — per-widget isolation
- [x] SSE reconnection UI — connection status indicator + manual reconnect button
- [x] Non-color indicators — ▲/▼ icons for gain/loss (accessibility)
- [x] Unified skeleton UI loading states (CardSkeleton, ChartSkeleton, TableSkeleton)

---

## Milestone 12: Backend Enhancement (Remaining)

### 12-3. Performance & Caching
- [x] ETag / `If-None-Match` support for dashboard endpoint (변경 없으면 304)
- [ ] Stock search trie structure or Redis `ZRANGEBYLEX` indexing
- [ ] KIS batch price API exploration (단일 호출로 여러 종목 조회)

### 12-4. Alert System — Notification Logic
Alert CRUD exists but no logic to actually notify users when price conditions are met.

- [x] Price condition check in SSE streaming loop
- [x] Dedup — `last_triggered_at` column + cooldown
- [x] Auto-deactivate triggered alerts
- [x] In-app notification center: `notifications` 테이블 + `GET/PATCH /notifications` API
- [x] Frontend notification bell + unread badge + dropdown panel
- [ ] Email alerts (SendGrid / Resend) → 19-1로 통합

### 12-5. API Extension
- [x] Cursor-based pagination for transactions
- [x] Cursor-based pagination for sync_logs
- [x] Bulk operations API (`POST /portfolios/{id}/holdings/bulk`) — portfolios.py:398 구현 완료

---

## Milestone 13: Data Pipeline & Analysis

### 13-1. External Data Collection
- [ ] KOSPI200 / S&P500 daily index data collection — 국내 `FHKUP03500100`, 해외 `FHKST03030100` (benchmark 전제 조건)
- [ ] Stock metadata table (sector, industry, market_cap)
- [ ] Dividend data collection — KIS `HHKDB669102C0` 배당일정 + `HHKDB13470100` 배당률 상위

### 13-2. Portfolio Analysis Engine
- [ ] TWR (time-weighted return) / MWR (money-weighted return) calculation
- [ ] Risk metrics: volatility, Sharpe ratio, MDD, beta

### 13-3. AI Insights
- [ ] News summarization (RSS + Claude)

### 13-4. DB Stability
- [x] Automated daily pg_dump backup
- [x] Retention policy (7 daily + 4 weekly + 3 monthly)
- [x] Recovery procedure documentation
- [x] Backup failure alerting + health endpoint `last_backup_at`

---

## Milestone 13-5: Operational Stability & Data Integrity

### 13-5a. Operational Stability
- [x] Redis failure fallback
- [x] Scheduler failure alerting (consecutive failure tracking)
- [ ] Docker volume disk monitoring → 18-3으로 통합
- [ ] TLS certificate renewal check → 18-3으로 통합
- [ ] Price fetch failure rate tracking → 18-3으로 통합

### 13-5b. Data Integrity
- [x] `price_snapshots` gap detection
- [x] Holdings quantity reconciliation
- [x] Orphan record cleanup

### 13-5c. KIS API Dependency Reduction
- [x] Adaptive cache TTL (after-market 24h extension)
- [x] KIS API health check on startup + degraded mode
- [ ] Price fetch failure rate tracking → 18-3으로 통합

---

## Milestone 14: Infrastructure & Observability (Remaining)

### 14-2. Monitoring & Observability
- [x] Sentry 백엔드 통합 — `sentry-sdk[fastapi]` + `SENTRY_DSN` env (완료, 수신 확인됨)
- [x] Sentry 프론트엔드 통합 — `@sentry/nextjs` + Error Boundary `captureException` 연동 (완료)
- [x] API 응답시간 미들웨어 — `MetricsMiddleware`: `process_time` structlog 기록 + `X-Process-Time` 헤더

### 14-4. Security Enhancement
- [ ] API key rotation automation
- [x] Security audit log (login attempts, settings changes, data access) — 완료 (Sprint 4 backend + Sprint 6 UI)
- [ ] 2FA (TOTP, Google Authenticator compatible)

---

## Milestone 15: User Experience & Extension

### 15-2. Portfolio Tools
- [x] Breakeven visualization — HoldingsTable 미니 게이지 바 (52주 범위 내 현재가 + 평균 매입가 마커)
- [ ] Portfolio performance sharing → 19-2로 통합
- [ ] Screenshot sharing → 19-2로 통합

### 15-4. Data Export & Tax
- [ ] Excel export → 19-3으로 통합
- [ ] Tax calculator → 19-3으로 통합
- [ ] PDF report generation → 19-3으로 통합

---

## Milestone 16: Dev Tools & DX (Remaining)

### 16-2. Test Infrastructure
- [x] MSW (Mock Service Worker) 설정 — 프론트엔드 테스트 API 모킹 인프라
- [x] Dashboard page component tests (TanStack Query mock + MSW)
- [x] Portfolio list/detail page tests
- [x] HoldingsTable unit tests (sort, PnLBadge color rules, overseas USD display)
- [x] SSE connection tests (connect/reconnect, off-hours deactivation)

### 16-3. Code Quality Tools
- [ ] Storybook 8 — component catalog (`PnLBadge`, `DayChangeBadge`, `AllocationDonut`, `HoldingsTable`)
- [x] Commitlint — commit message format validation

---

## Milestone 17: 투자 분석 고도화 (신규)

### 17-1. 포트폴리오 비교 대시보드
- [x] 포트폴리오 간 수익률 비교 차트 (overlay line chart)
- [ ] 기간별 필터 (1w / 1m / 3m / 6m / 1y / all) + date range picker
- [ ] 포트폴리오별 섹터 비중 비교 (side-by-side donut)

### 17-2. 환율 관리 및 해외투자 분석
- [x] USD/KRW 환율 히스토리 저장 (daily snapshot)
- [x] 해외주식 환차익/환차손 분리 표시 (주가 수익 vs 환율 수익)
- [x] 원화 환산 총 자산 추이 차트 (환율 변동 반영)
- [ ] 환율 알림 (목표 환율 도달 시 알림)

### 17-3. 투자 일지 대시보드
- [x] 거래 메모 기반 투자 일기장 뷰 (타임라인 UI)
- [x] 거래별 태그 시스템 (#실적발표, #배당투자, #단기매매 등)
- [x] 월별/종목별 투자 일지 필터링 및 검색
- [x] 투자 결정 회고 — 매수 시점 가격 vs 현재가 비교 위젯

---

## Milestone 18: 운영 안정성 강화 (신규)

### 18-1. 운영 대시보드
- [ ] `/dashboard/admin` 내부 관리 페이지 (관리자 전용)
- [ ] 동기화 상태 모니터링 (sync_logs 시각화, 성공/실패 추이)
- [ ] KIS API 응답시간 추이 차트 (MetricsMiddleware 데이터 활용)
- [ ] Redis 키 현황 모니터링 (토큰/캐시/락 상태)

### 18-2. 매니지드 인프라 전환
- [ ] Neon (PostgreSQL) 프로젝트 생성 및 데이터 마이그레이션
- [ ] Upstash (Redis) 인스턴스 생성 및 연결
- [ ] 프로덕션 `.env` 업데이트 + 스테이징 검증
- [ ] Docker Compose 로컬 개발용으로만 유지

### 18-3. 인프라 모니터링 확장
- [x] Docker 볼륨 디스크 사용량 모니터링 (80% 임계값 경고)
- [ ] TLS 인증서 만료 체크 자동화
- [ ] KIS API 가격 조회 실패율 추적 (30% 초과 시 alert)
- [ ] 백업 성공률 대시보드 (최근 30일 히스토리)

---

## Milestone 19: 사용자 경험 확장 (신규)

### 19-1. 이메일/푸시 알림
- [ ] SendGrid 또는 Resend 연동 — 가격 알림 이메일 발송
- [ ] 알림 채널 설정 UI (인앱 / 이메일 / 둘 다)
- [ ] 일일 포트폴리오 요약 이메일 (장 마감 후 자동 발송)
- [ ] PWA Web Push 알림 (모바일 브라우저 지원)

### 19-2. 소셜/공유 기능
- [ ] 포트폴리오 성과 익명 공유 링크 (종목명 마스킹 옵션)
- [ ] 성과 스크린샷 공유 (html2canvas 기반 이미지 생성)
- [ ] 공유 페이지 — 인증 없이 열람 가능한 읽기 전용 대시보드

### 19-3. 데이터 내보내기 확장
- [x] Excel 내보내기 (openpyxl 기반, 서식 포함 xlsx) — portfolio_export.py 구현 완료

---

---

## Sprint-6 완료 항목 (2026-04-03)

### 보안
- [x] SSE JWT URL 노출 제거: POST /auth/sse-ticket (30초 TTL 단일사용 티켓, nginx 로그 노출 방지)
- [x] GET /auth/sessions — Redis refresh:{user_id}:* 스캔, IDOR 보호
- [x] DELETE /auth/sessions/{jti} — 개별 세션 강제 종료, IDOR 보호

### 성능
- [x] PERF-SSE: httpx.AsyncClient SSE 루프 외부로 이동 (TCP/TLS 연결 1회/2시간, 기존 1회/30초)
- [x] PERF-ETAG: 대시보드 ETag/304 캐싱 (SHA-256[:16], after-hours 폴링 페이로드 ~90% 감소)

### 리팩터링
- [x] portfolios/[id]/page.tsx 1226 → 65줄 (PortfolioHeader + HoldingsSection + TransactionSection 분리)
- [x] settings/page.tsx 901 → 75줄 (AccountSection + KisCredentialsSection + SecurityLogsSection + ActiveSessionsSection 탭 분리)
- [x] SecurityLogsSection — GET /users/me/security-logs, 한국어 액션 레이블, 실패 컬러링
- [x] ActiveSessionsSection — GET /auth/sessions, 개별 취소, 세션 생성일 표시
- [x] usePriceStream.ts — 티켓 인증으로 EventSource URL에서 JWT 제거

### 테스트
- [x] OrderDialog.test.tsx — 8개 vitest+MSW 테스트 (BUY/SELL, 수량 0 차단, LIMIT 가격 필수, 국내/해외 라우팅, 인플라이트 비활성화, 성공 닫기, 오류 처리)

### 의존성
- [x] next 16.2.0 → 16.2.2
- [x] @sentry/nextjs 10.45.0 → 10.47.0
- [x] @playwright/test 1.58.2 → 1.59.1
- [x] react-is 추가 (recharts 빌드 실패 해결)

---

## Sprint-3 완료 항목 (2026-04-03)

### 보안
- [x] SEC-001: Sentry KIS 자격증명 스크러빙 (before_send 훅, kis_order/kis_token from-None chain)
- [x] SEC-002: bcrypt DoS 방어 (password max_length=128, auth.py/user.py)
- [x] SEC-004: 프로덕션 CSP unsafe-eval 제거 (next.config.ts 빌드 환경 분기)
- [x] SEC-006: TransactionMemoUpdate tags 최대 20개, 개당 50자 제한
- [x] TD-005: cryptography 46.0.5 → 46.0.6 패치 업그레이드

### 성능
- [x] PERF-001: get_prev_close DISTINCT ON 쿼리 (14,600행 → 20행)
- [x] PERF-002: fx-gain-loss Redis 캐시 가드
- [x] PERF-003: analytics/metrics 해외 ticker → fetch_overseas_price_detail 라우팅
- [x] PERF-004: SSE 활성 시 dashboard polling 비활성화 (streamActiveRef)
- [x] PERF-005/TD-001: Redis ConnectionPool 싱글턴 (요청당 TCP 오버헤드 40-300ms 제거)
- [x] PERF-006: analytics/page.tsx 쿼리 키 `["dashboard", "summary"]`로 통일

### UX/접근성
- [x] UX-001: 포트폴리오 상세 7개 mutation onError toast
- [x] UX-004: 포트폴리오 목록 rename/delete onError + reorder rollback
- [x] UX-006: analytics 테이블 키보드 접근성 (tabIndex, Enter/Space)
- [x] UX-007: 인라인 삭제 오버레이 → shadcn AlertDialog 교체

---

## Milestone 20: 보안 강화 — 트레이딩 계정 보호 (team-analysis 2026-04-02)

거래 기능 활성화 이후 계정 보안 리스크가 재무 피해로 직결되므로 P1 우선순위.

### 20-1. 서버 사이드 Refresh Token 관리 ✓ COMPLETED (Sprint 4, 2026-04-03)

- [x] Redis에 refresh token 저장 — `refresh:{user_id}:{jti}` 키, TTL = refresh 만료일
- [x] 로그아웃 시 Redis 키 삭제 + 사용자별 전체 무효화 O(1) per-user SCAN
- [x] `/auth/refresh` 검증 시 Redis 존재 여부 확인 — 없으면 401 반환
- [x] 비밀번호 변경 시 전체 refresh token 무효화
- [x] Redis 값 JSON 확장: {user_id, created_at} — 세션 관리 UI 준비

### 20-2. 2FA (TOTP)

- [ ] `pyotp` 패키지 + TOTP 시크릿 생성/저장 API (`POST /users/me/2fa/setup`)
- [ ] QR 코드 URI 반환 → 프론트 설정 UI (Google Authenticator 등록)
- [ ] 2FA 활성화 확인 (`POST /users/me/2fa/verify`) + users 테이블 `totp_enabled`, `totp_secret_enc` 컬럼
- [ ] 로그인 플로우: 2FA 활성화 계정은 TOTP 코드 추가 입력 단계

### 20-3. 보안 감사 로그 ✓ COMPLETED (Sprint 4, 2026-04-03)

- [x] `security_audit_logs` 테이블: user_id, action enum, ip_address, user_agent, meta JSONB, created_at
- [x] 기록 대상: 로그인 성공/실패, 로그아웃, KIS 자격증명 등록/삭제, 비밀번호 변경, 회원 탈퇴
- [x] `GET /users/me/security-logs` 엔드포인트 (최근 50건)
- [x] 설정 페이지 '보안 로그' 탭 추가 (Sprint 6, 2026-04-03)

### 20-4. 활성 세션 관리 ✓ COMPLETED (Sprint 6, 2026-04-03)

- [x] `GET /auth/sessions` — 활성 세션 목록 조회 (Redis refresh:{user_id}:* 스캔)
- [x] `DELETE /auth/sessions/{session_id}` — 특정 세션 강제 종료
- [x] 설정 페이지 '활성 세션' 탭 추가

---

## Milestone 21: 분석 엔진 완성 — 벤치마크 + 리스크 지표 (team-analysis 2026-04-02)

현재 analytics 완성도 72%. 벤치마크 오버레이와 리스크 지표가 핵심 잔여 갭.

### 21-1. 시장 지수 데이터 수집 (13-1 선행 작업)

- [ ] `index_snapshots` 테이블: index_code (KOSPI200/SPX), snapshot_date, close, open, high, low
- [ ] 스케줄러: 평일 KST 16:15 KOSPI200 (`FHKUP03500100`) + S&P500 (`FHKST03030100 .SPX`) 일별 데이터 저장
- [ ] `GET /analytics/benchmark` 엔드포인트 — 기간별 벤치마크 수익률 반환

### 21-2. 벤치마크 오버레이 차트

- [ ] 포트폴리오 히스토리 차트에 KOSPI200/S&P500 기준선 오버레이 (Recharts 추가 Line)
- [ ] 벤치마크 선택 토글 (국내 포트폴리오 → KOSPI200, 해외 포함 → S&P500)
- [ ] 기간 필터와 동기화 (1M/3M/6M/1Y/ALL)

### 21-3. 리스크 지표 계산

- [ ] `backend/app/services/metrics.py` — Sharpe ratio, MDD, 연환산 베타, 변동성 계산
- [ ] `GET /analytics/metrics` 응답에 sharpe_ratio, mdd, volatility 추가
- [ ] 분석 페이지 지표 카드 UI 업데이트

### 21-4. DCA 분석 뷰 (신규 기능)

- [ ] 거래 이력에서 정기 매수 패턴 감지 (월별 BUY 트랜잭션 집계)
- [ ] 종목별 평균매입단가 시계열 차트 (매수 거래 시점별 avg_price 변화)
- [ ] 투자 일지 페이지 또는 분석 페이지 내 'DCA 분석' 섹션 추가

---

## Milestone 22: 인프라 안정화 — Neon + Upstash + 이메일 알림 (team-analysis 2026-04-02)

단일 서버 PostgreSQL은 트레이딩 기능이 있는 프로덕션 앱의 주요 리스크.

### 22-1. Neon (서버리스 PostgreSQL) 전환 (18-2)

- [ ] Neon 프로젝트 생성 및 스키마 마이그레이션 (`alembic upgrade head`)
- [ ] 데이터 이전: `pg_dump` → Neon import
- [ ] `DATABASE_URL` 환경변수 업데이트 + 연결 테스트
- [ ] Docker Compose는 로컬 개발용으로만 유지

### 22-2. Upstash (서버리스 Redis) 전환 (18-2)

- [ ] Upstash Redis 인스턴스 생성 (TLS 연결)
- [ ] `REDIS_URL` 환경변수 업데이트
- [ ] 기존 RedisCache 추상화 재사용 — 코드 변경 최소화
- [ ] 스테이징 환경 검증 (KIS 토큰 캐싱, analytics 캐시, SSE)

### 22-3. 이메일 알림 (Resend) (19-1)

- [ ] `resend` Python 패키지 + `RESEND_API_KEY` 환경변수
- [ ] 가격 알림 이메일 발송 — 알림 조건 충족 시 triggered_alert에서 호출
- [ ] 알림 채널 설정 UI — 인앱 / 이메일 / 둘 다 선택
- [ ] 일일 포트폴리오 요약 이메일 — 평일 KST 16:30 자동 발송 (장 마감 후)

---

## Priority Guide (2026-04-02 2차 갱신)

### team-analysis 2차 sprint (2026-04-02)

tasks.md에 즉시 실행 가능 항목 8개 추가 (P0/P1):
- P0: Sentry KIS 자격증명 스크러빙, get_prev_close DISTINCT ON, bcrypt DoS 방어, cryptography 업데이트
- P1: fx-gain-loss 캐시, metrics 해외종목 라우팅, SSE 활성 시 폴링 비활성화, mutation onError

1차 sprint 항목 전체 완료:
- ~~GZip 미들웨어, is_domestic 통합, analytics cache 누락 수정~~
- ~~DB 인덱스 2건, 삭제 확인 다이얼로그, compare 빈 상태, rate limiting, CORS 스코프~~
- ~~localStorage 방어 처리, Sentry env 설정, 차트 스켈레톤~~

신규 마일스톤:
- **Milestone 20** (P1): 보안 강화 -- 2FA, 서버사이드 refresh token, 감사 로그
- **Milestone 21** (P1): 분석 엔진 완성 -- 벤치마크, 리스크 지표, DCA 분석
- **Milestone 22** (P2): 인프라 안정화 -- Neon, Upstash, 이메일 알림

### P1 -- 핵심 기능 + 보안 + 인프라 안정성 (10개)
| # | Item | Milestone | Reason | Source |
|---|------|-----------|--------|--------|
| 1 | SSE 토큰 쿼리 파라미터 -> HttpOnly 쿠키 | 보안 | 서버 로그에 JWT 노출 방지 | SEC-003 |
| 2 | Redis 커넥션 풀링 (per-call -> shared pool) | 성능 | 요청당 40-300ms 오버헤드 제거 | PERF-005 |
| 3 | TOTP 2FA (Google Authenticator 호환) | 20-2 | 트레이딩 기능 활성화 후 계정 보안 필수 | PROD-010 |
| 4 | 서버사이드 Refresh Token 무효화 | 20-1 | 로그아웃 후 토큰 재사용 방지 | PROD-001 |
| 5 | 시장 지수 데이터 수집 + Sharpe/MDD 지표 | 21-1/21-3 | 투자 성과 핵심 분석 도구 | PROD-002 |
| 6 | KOSPI200/S&P500 벤치마크 오버레이 | 21-2 | 수익률 비교 기준선 | PROD-002 |
| 7 | Neon(PostgreSQL) + Upstash(Redis) 전환 | 22-1/22-2 | 단일 서버 리스크 해소 | PROD-003 |
| 8 | 이메일 알림 (Resend) -- 인프라와 분리 | 22-3 | 인앱 알림만으로는 실시간 대응 불가 | PROD-004 |
| 9 | 보안 감사 로그 | 20-3 | 재무 앱 필수 추적성 | -- |
| 10 | DCA 분석 뷰 | 21-4 | 한국 개인투자자 핵심 패턴 | PROD-007 |

### P2 -- 분석 고도화 + 사용자 경험 (37개)
| # | Item | Milestone | Reason | Source |
|---|------|-----------|--------|--------|
| 1 | 종목 메타데이터 테이블 (섹터, 업종, 시가총액) | 13-1 | 섹터 분석 정확도 향상 | -- |
| 2 | 배당 데이터 수집 (KIS or KRX) | 13-1 | 배당 추적의 전제 조건 | -- |
| 3 | TWR/MWR 수익률 계산 | 13-2 | 정확한 투자 성과 측정 | -- |
| 4 | 배당 수익 추적 (캘린더 + 수익률 차트) | 11-2 | 배당 투자자 핵심 기능 | -- |
| 5 | 월간/연간 수익률 히트맵 | 11-2 | 성과 시각화 (GitHub 스타일) | PROD-008 |
| 6 | 내 보유가 오버레이 (캔들차트 평균매입가 수평선) | 11-4 | 현재가 vs 매입가 시각적 비교 | -- |
| 7 | 이동평균선 오버레이 (5/20/60/120일) | 11-4 | 기술적 분석 기본 도구 | -- |
| 8 | 거래량 분석 차트 | 11-4 | 종목 상세 분석 보완 | -- |
| 9 | 뉴스/공시 피드 (KIS or 네이버 금융) | 11-4 | 종목 관련 정보 통합 | -- |
| 10 | 포트폴리오 비교: 기간별 필터 + date range picker | 17-1 | 비교 대시보드 사용성 개선 | -- |
| 11 | 포트폴리오별 섹터 비중 비교 (side-by-side donut) | 17-1 | 다중 포트폴리오 분석 | -- |
| 12 | 환율 알림 (목표 환율 도달 시) | 17-2 | 환전 타이밍 알림 | -- |
| 13 | 알림 채널 설정 UI (인앱/이메일/둘 다) | 22-3 | 알림 개인화 | -- |
| 14 | 일일 포트폴리오 요약 이메일 | 22-3 | 장 마감 후 자동 리포트 | -- |
| 15 | PWA Web Push 알림 | 19-1 | 모바일 실시간 알림 | -- |
| 16 | API key rotation 자동화 | 14-4 | KIS 키 관리 안전성 | -- |
| 17 | TLS 인증서 만료 체크 자동화 | 18-3 | 서비스 중단 예방 | -- |
| 18 | 활성 세션 관리 UI | 20-4 | 계정 보안 투명성 | -- |
| 19 | portfolios/[id]/page.tsx 컴포넌트 분리 (1123줄) | -- | 유지보수성 | TD-002/PROD-009 |
| 20 | settings/page.tsx 컴포넌트 분리 (901줄) | -- | 유지보수성 | TD-003/PROD-009 |
| 21 | OrderDialog lazy loading (dynamic import) | -- | 초기 번들 크기 절감 | PERF-008 |
| 22 | analytics.py holdings 쿼리 공통 서비스 추출 | -- | 코드 중복 제거 | TD-004 |
| 23 | SSE delta 감지 -- 변경 없으면 heartbeat만 전송 | -- | 네트워크 + 렌더링 효율 | PERF-006 |
| 24 | lucide-react v1.x 마이그레이션 | -- | 메이저 버전 업데이트 | TD-012 |
| 25 | kis_order.py 함수 추출 (place_order 128줄) | -- | 유지보수성 | TD-002 |
| 26 | OrderDialog.tsx 테스트 추가 (605줄, 무테스트) | -- | 트레이딩 UI 회귀 방지 | TD-004 |
| 27 | analytics/journal/compare 페이지 테스트 | -- | 비즈니스 로직 커버리지 확보 | TD-003 |
| 28 | OrderDialog/KIS cash balance --rise/--fall 변수 통일 | -- | 다크모드 색상 일관성 | UX-003 |
| 29 | CSV/XLSX 다운로드 에러 핸들링 + 로딩 상태 | -- | 네트워크 에러 시 무반응 해소 | UX-005 |
| 30 | analytics 페이지 에러 상태 + per-section 로딩 | -- | 7개 쿼리 에러/로딩 미처리 | UX-002/UX-010 |
| 31 | 입력 필드 max_length 제약 (name, ticker, tags) | -- | DoS 방어 | SEC-005/SEC-006 |
| 32 | SSE DB 세션 재사용 (30초마다 새 세션 불필요) | -- | DB 부하 97% 감소 | PERF-008 |
| 33 | SSE httpx 클라이언트 루프 외부로 이동 | -- | TLS 핸드셰이크 반복 제거 | PERF-009 |
| 34 | SSE 해외종목 실시간 가격 지원 | -- | 해외 보유종목 가격 고정 해소 | PERF-010 |
| 35 | analytics 순차 DB 쿼리 asyncio.gather 병렬화 | -- | 라운드트립 1회 절약 (5-15ms) | PERF-012 |
| 36 | response_model 누락 3개 엔드포인트 추가 | -- | openapi-typescript 타입 생성 | TD-007 |
| 37 | alert 비즈니스 로직 services 레이어 이동 | -- | api 레이어 횡단 의존성 해소 | TD-008 |

### P3 -- 부가 기능 + DX (18개)
| # | Item | Milestone | Reason | Source |
|---|------|-----------|--------|--------|
| 1 | 운영 대시보드 (`/dashboard/admin`) | 18-1 | 관리 편의성, 규모 커지면 필수 | -- |
| 2 | 동기화 상태 모니터링 (sync_logs 시각화) | 18-1 | 운영 가시성 | -- |
| 3 | KIS API 응답시간 추이 차트 | 18-1 | 성능 추적 | -- |
| 4 | Redis 키 현황 모니터링 | 18-1 | 캐시/락 상태 파악 | -- |
| 5 | ETag/If-None-Match (dashboard 304) | 12-3 | 대역폭 절약, 체감 속도 개선 | -- |
| 6 | 종목 검색 trie/Redis ZRANGEBYLEX 인덱싱 | 12-3 | 검색 성능 최적화 | -- |
| 7 | KIS batch price API 탐색 | 12-3 | API 호출 횟수 절감 | -- |
| 8 | KIS API 가격 조회 실패율 추적 | 18-3 | 데이터 품질 모니터링 | -- |
| 9 | 백업 성공률 대시보드 (최근 30일) | 18-3 | 백업 신뢰성 확인 | -- |
| 10 | 뉴스 요약 (RSS + Claude) | 13-3 | AI 부가 기능 | -- |
| 11 | 포트폴리오 성과 익명 공유 링크 + 공유 페이지 | 19-2 | 바이럴 마케팅 | -- |
| 12 | Storybook 8 컴포넌트 카탈로그 | 16-3 | DX 개선 | -- |
| 13 | SSR 초기 데이터 prefetch (dashboard Server Component) | -- | TTI 개선 | PERF-003 |
| 14 | SQLAlchemy pool_recycle=1800 설정 | -- | 야간 유휴 연결 에러 방지 | PERF-013 |
| 15 | Recharts ARIA label 추가 | -- | 스크린 리더 차트 정보 제공 | UX-008 |
| 16 | WatchlistSection 아이콘 aria-label 추가 | -- | 접근성 개선 | UX-009 |
| 17 | pip-audit CI 단계 추가 | -- | Python 의존성 취약점 자동 검출 | SEC-009 |
| 18 | backend HSTS 헤더 추가 (프로덕션 전용) | -- | API 도메인 HTTPS 강제 | SEC-008 |

> 보류(parked) 항목은 `docs/plan/parked.md` 참조

### team-analysis 3차 sprint (2026-04-03)

tasks.md에 즉시 실행 가능 항목 8개 추가 (P1/P2):
- P1: Redis 커넥션 풀 공유 (PERF-005), portfolios/page.tsx onError (UX-004), CSP unsafe-eval 제거 (SEC-004), tags 길이 제약 (SEC-006)
- P2: analytics 쿼리 키 통일 (PERF-006), analytics 테이블 키보드 접근성 (UX-006), 인라인 삭제 확인창 AlertDialog 교체 (UX-007)

신규 P2/P3 백로그 추가:
- analytics/metrics 날짜 커트오프 (PERF-007)
- 리스크 지표 최소 히스토리 가드 (PROD-005)
- UX 품질: 설정 KIS 테스트 버튼 로딩 상태, 일지 BUY/SELL 배지 텍스트, 보유종목 추가 인라인 에러
- stocks.py _is_domestic 잔존 제거 (TD-001)
- forward_fill_rates fx_utils.py 추출 (TD-011)
- PortfolioHistoryChart any[] 타입 제거 (TD-013)

신규 P2 항목 (P2 표에 추가):
| 38 | analytics metrics 날짜 커트오프 (1Y window) | -- | 14,600행 불필요 전송 제거 | PERF-007 |
| 39 | 리스크 지표 최소 히스토리 가드 (30일 미만 시 placeholder) | 21-3 | 오해의 소지 있는 Sharpe/MDD 출력 방지 | PROD-005 |
| 40 | 설정 KIS API 테스트 버튼 로딩 상태 추가 | -- | 3-10초 호출 중 버튼 무반응 해소 | UX-013 |
| 41 | 투자 일지 BUY/SELL 배지 색상 외 텍스트 추가 | -- | WCAG 1.4.1 색상 단독 의존 방지 | UX-012 |
| 42 | 보유종목 추가 폼 인라인 에러 메시지 (zero/negative) | -- | 서버 422 무시 해소 | UX-011 |
| 43 | stocks.py _is_domestic() 제거 (is_domestic 임포트로 교체) | -- | is_domestic 통합 잔존 버그 | TD-001 |
| 44 | forward_fill_rates() 함수 fx_utils.py 추출 (Milestone 21 재사용 준비) | -- | 분기 로직 재사용 가능하게 분리 | TD-011 |
| 45 | PortfolioHistoryChart payload any[] 타입 제거 | -- | 알려진 타입으로 교체 | TD-013 |

### 항목 수 요약 (2026-04-03 3차 갱신)
| 우선순위 | 개수 | 설명 |
|----------|------|------|
| P1 | 10 | 핵심 기능 + 보안 + 인프라 안정성 |
| P2 | 45 | 분석 고도화 + 사용자 경험 + 코드 품질 |
| P3 | 18 | 부가 기능 + DX + 접근성 |
| Parked | 8 | 보류 (`parked.md`) |
| **합계** | **81** | |

---

## Sprint-7 신규 항목 (2026-04-03, 7차 스프린트)

### 즉시 실행 (tasks.md Sprint 7 추가)

| 항목 | 우선순위 | 소스 |
|------|----------|------|
| fx_gain_loss 캐시 키 불일치 수정 (one-line fix) | P0 | SEC-003 |
| 수동 보유종목 변경 시 analytics 캐시 무효화 | P0 | PERF-004 |
| analytics/notifications/users rate limiting 추가 | P0 | SEC-001 |
| SSE ticker DB 세션 최적화 (모듈 캐시) | P0 | PERF-001 |
| SSE 해외종목 실시간 가격 지원 | P1 | TD-007 |
| OrderDialog dynamic import | P1 | PERF-003 |
| compare 페이지 empty state | P1 | UX-002 |
| settings 탭 URL hash persist | P2 | UX-008 |

### Milestone 23: 분석 완성 + 2FA (team-analysis 2026-04-03 제안)

analytics 완성도 65% — 벤치마크 비교와 2FA가 핵심 미완성 항목.

#### 23-1. TOTP 2FA (20-2 실행)
- [ ] `pyotp` 패키지 + `POST /users/me/2fa/setup` (QR URI 반환)
- [ ] `users` 테이블 `totp_secret_enc` 컬럼 추가 (AES-256 암호화) + Alembic 마이그레이션
- [ ] `POST /users/me/2fa/verify` — 코드 확인 + `totp_enabled=True` 저장
- [ ] 로그인 플로우: totp_enabled 계정에 2단계 코드 입력 추가
- [ ] 설정 페이지 2FA 섹션 (AccountSection.tsx에 추가)

#### 23-2. 시장 지수 데이터 수집 (21-1)
- [ ] `index_snapshots` 테이블: index_code(KOSPI200/SPX), snapshot_date, close, open, high, low
- [ ] 스케줄러: 평일 KST 16:15 KOSPI200 (`FHKUP03500100`) + S&P500 (`FHKST03030100 .SPX`) 데이터 저장
- [ ] `GET /analytics/benchmark` 엔드포인트 — 기간별 벤치마크 수익률

#### 23-3. 벤치마크 오버레이 차트 (21-2)
- [ ] PortfolioHistoryChart.tsx에 KOSPI200/S&P500 기준선 추가 (Recharts Line)
- [ ] 기간 필터와 동기화 (1M/3M/6M/1Y/ALL)
- [ ] 벤치마크 토글 버튼 (국내 포트폴리오 → KOSPI200, 해외 포함 → S&P500)

#### 23-4. 리스크 지표 서비스 추출 (21-3)
- [ ] `backend/app/services/metrics_service.py` — _calc_sharpe, _calc_mdd, _calc_cagr 이동
- [ ] 최소 히스토리 가드: 30일 미만 시 Sharpe/MDD null 반환 (오해 방지)
- [ ] 분석 페이지 리스크 지표 카드 UI (Sharpe, MDD, 연환산 수익률)

### 신규 P2 항목 (2026-04-03 추가)

| # | 항목 | 이유 | 소스 |
|---|------|------|------|
| 46 | Recharts 차트 ARIA 레이블 (role=img + sr-only 데이터 테이블) | WCAG 1.1.1 준수 | UX-001 |
| 47 | 해외 보유종목 'Last Sync' 타임스탬프 뱃지 (SSE 실시간 전까지 임시) | 혼란스러운 '--' 해소 | UX-003 |
| 48 | 종목 상세 페이지 '관심종목 추가/제거' 버튼 | 페이지 간 이동 없이 바로 추가 | UX-007 |
| 49 | HoldingsTable 정렬 상태 sessionStorage 저장 | 페이지 이동 후 정렬 초기화 방지 | UX-006 |
| 50 | analytics.py get_metrics 순차 DB 쿼리 asyncio.gather 병렬화 | 30-50ms 절감 | PERF-002 |
| 51 | analytics/page.tsx 762줄 → 섹션별 컴포넌트 분리 | 800줄 한계 접근 | TD-010 |
| 52 | kis_order.py place_domestic/overseas_order 헬퍼 추출 | 128줄 함수 단순화 | TD-002 |
| 53 | portfolios.py → holdings.py + transactions.py 분리 | 746줄 파일 분리 | TD-003 |
| 54 | 감사 로그 KIS 계좌 삭제 이벤트 기록 확인 및 추가 | 재무 앱 추적성 | SEC-004 |
| 55 | analytics 해외종목 가격 조회 전 캐시 체크 | 불필요한 KIS API 호출 80% 감소 | PERF-006 |

### 항목 수 요약 (2026-04-03 4차 갱신 — Sprint 7)
| 우선순위 | 개수 | 설명 |
|----------|------|------|
| P0 (tasks.md Sprint 7) | 4 | 캐시 버그 수정 + rate limiting + SSE DB 최적화 |
| P1 (tasks.md Sprint 7) | 4 | SSE 해외주식 + OrderDialog lazy + compare empty + 탭 URL |
| P1 (Milestone 23) | 12 | 2FA + 벤치마크 + 리스크 지표 |
| P2 신규 | 10 | 접근성 + 성능 + 코드 품질 |
| **Sprint 7 신규 합계** | **30** | |
