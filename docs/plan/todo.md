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
- [ ] ETag / `If-None-Match` support for dashboard endpoint (변경 없으면 304)
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
- [ ] Security audit log (login attempts, settings changes, data access)
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
- [ ] 해외주식 환차익/환차손 분리 표시 (주가 수익 vs 환율 수익)
- [ ] 원화 환산 총 자산 추이 차트 (환율 변동 반영)
- [ ] 환율 알림 (목표 환율 도달 시 알림)

### 17-3. 투자 일지 대시보드
- [x] 거래 메모 기반 투자 일기장 뷰 (타임라인 UI)
- [x] 거래별 태그 시스템 (#실적발표, #배당투자, #단기매매 등)
- [ ] 월별/종목별 투자 일지 필터링 및 검색
- [ ] 투자 결정 회고 — 매수 시점 가격 vs 현재가 비교 위젯

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

## Priority Guide (2026-04-01 갱신)

### 해결 완료 (이전 P0/P1)
- ~~테스트 일괄 실행 (294 ERROR)~~ — conftest.py async session 격리 수정, CI 전체 통과
- ~~중복 파일 정리~~ — 이상 파일 없음, 구조 정상
- ~~Trading Feature 테스트 커버리지~~ — 39개 테스트 추가 (orders 36 + settlement 3)
- ~~npm 취약점 (yaml)~~ — `npm audit` 0 vulnerabilities
- ~~미체결 주문 즉시 반영 버그~~ — pending 시 transaction/holding 생성 제거, 체결 확인 스케줄러 추가

### P1 — 핵심 기능 + 인프라 안정성 (5개)
| # | Item | Milestone | Reason |
|---|------|-----------|--------|
| 1 | Sharpe ratio, MDD, CAGR 지표 | 11-2 | 투자 성과 핵심 분석 도구 |
| 2 | KOSPI200/S&P500 벤치마크 오버레이 | 11-2 | 수익률 비교 기준선 (13-1 선행 필요) |
| 3 | 해외주식 환차익/환차손 분리 표시 | 17-2 | 사용자 요청 빈번, 해외투자 핵심 |
| 4 | 원화 환산 총 자산 추이 차트 | 17-2 | 환율 변동 반영된 실질 자산 파악 |
| 5 | Neon(PostgreSQL) + Upstash(Redis) 전환 | 18-2 | 단일 서버 리스크 해소 (4개 하위 항목) |

### P2 — 분석 고도화 + 사용자 경험 (24개)
| # | Item | Milestone | Reason |
|---|------|-----------|--------|
| 1 | KOSPI200/S&P500 일별 인덱스 데이터 수집 | 13-1 | 벤치마크·분석 엔진의 선행 조건 |
| 2 | 종목 메타데이터 테이블 (섹터, 업종, 시가총액) | 13-1 | 섹터 분석 정확도 향상 |
| 3 | 배당 데이터 수집 (KIS or KRX) | 13-1 | 배당 추적의 전제 조건 |
| 4 | TWR/MWR 수익률 계산 | 13-2 | 정확한 투자 성과 측정 |
| 5 | 리스크 지표: 변동성, Sharpe, MDD, 베타 | 13-2 | 포트폴리오 리스크 분석 |
| 6 | 배당 수익 추적 (캘린더 + 수익률 차트) | 11-2 | 배당 투자자 핵심 기능 |
| 7 | 월간/연간 수익률 히트맵 | 11-2 | 성과 시각화 (GitHub 스타일) |
| 8 | 내 보유가 오버레이 (캔들차트 평균매입가 수평선) | 11-4 | 현재가 vs 매입가 시각적 비교 |
| 9 | 이동평균선 오버레이 (5/20/60/120일) | 11-4 | 기술적 분석 기본 도구 |
| 10 | 거래량 분석 차트 | 11-4 | 종목 상세 분석 보완 |
| 11 | 뉴스/공시 피드 (KIS or 네이버 금융) | 11-4 | 종목 관련 정보 통합 |
| 12 | 포트폴리오 비교: 기간별 필터 + date range picker | 17-1 | 비교 대시보드 사용성 개선 |
| 13 | 포트폴리오별 섹터 비중 비교 (side-by-side donut) | 17-1 | 다중 포트폴리오 분석 |
| 14 | 환율 알림 (목표 환율 도달 시) | 17-2 | 환전 타이밍 알림 |
| 15 | 투자 일지 필터링 및 검색 (월별/종목별) | 17-3 | 거래 기록 탐색 편의성 |
| 16 | 투자 결정 회고 (매수 시점 vs 현재가 비교 위젯) | 17-3 | 투자 학습 지원 |
| 17 | 이메일 알림 (SendGrid/Resend) | 19-1 | 인앱 알림만으로는 실시간 대응 불가 |
| 18 | 알림 채널 설정 UI (인앱/이메일/둘 다) | 19-1 | 알림 개인화 |
| 19 | 일일 포트폴리오 요약 이메일 | 19-1 | 장 마감 후 자동 리포트 |
| 20 | PWA Web Push 알림 | 19-1 | 모바일 실시간 알림 |
| 21 | 2FA (TOTP, Google Authenticator) | 14-4 | 계정 보안 강화 |
| 22 | 보안 감사 로그 (로그인, 설정 변경, 데이터 접근) | 14-4 | 보안 추적성 |
| 23 | API key rotation 자동화 | 14-4 | KIS 키 관리 안전성 |
| 24 | TLS 인증서 만료 체크 자동화 | 18-3 | 서비스 중단 예방 |

### P3 — 부가 기능 + DX (12개)
| # | Item | Milestone | Reason |
|---|------|-----------|--------|
| 1 | 운영 대시보드 (`/dashboard/admin`) | 18-1 | 관리 편의성, 규모 커지면 필수 |
| 2 | 동기화 상태 모니터링 (sync_logs 시각화) | 18-1 | 운영 가시성 |
| 3 | KIS API 응답시간 추이 차트 | 18-1 | 성능 추적 |
| 4 | Redis 키 현황 모니터링 | 18-1 | 캐시/락 상태 파악 |
| 5 | ETag/If-None-Match (dashboard 304) | 12-3 | 대역폭 절약, 체감 속도 개선 |
| 6 | 종목 검색 trie/Redis ZRANGEBYLEX 인덱싱 | 12-3 | 검색 성능 최적화 |
| 7 | KIS batch price API 탐색 | 12-3 | API 호출 횟수 절감 |
| 8 | KIS API 가격 조회 실패율 추적 | 18-3 | 데이터 품질 모니터링 |
| 9 | 백업 성공률 대시보드 (최근 30일) | 18-3 | 백업 신뢰성 확인 |
| 10 | 뉴스 요약 (RSS + Claude) | 13-3 | AI 부가 기능 |
| 11 | 포트폴리오 성과 익명 공유 링크 + 공유 페이지 | 19-2 | 바이럴 마케팅 |
| 12 | Storybook 8 컴포넌트 카탈로그 | 16-3 | DX 개선 |

> 보류(parked) 항목은 `docs/plan/parked.md` 참조

### 항목 수 요약
| 우선순위 | 개수 | 설명 |
|----------|------|------|
| P1 | 5 | 핵심 기능 + 인프라 안정성 |
| P2 | 24 | 분석 고도화 + 사용자 경험 |
| P3 | 12 | 부가 기능 + DX |
| Parked | 8 | 보류 (`parked.md`) |
| **합계** | **49** | |
