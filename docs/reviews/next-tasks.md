# THE WEALTH — Next Tasks (Ideation & Implementation Plan)

생성일: 2026-03-21
목적: Claude Code가 읽고 순차적으로 구현할 태스크 목록
규칙: 각 항목은 **단일 커밋**으로 완료 가능한 단위

---

## 🔴 P0 — 즉시 해결 (버그 & 안정성)

### 0-1. 실패 테스트 수정: `test_overseas_support.py`

- **문제**: `kis_account.py`가 빈 배열 대신 `RuntimeError`를 raise하도록 변경되었으나 테스트 기대값 미반영 (2건 실패)
- **작업**: `backend/tests/test_overseas_support.py`에서 해외주식 잔고 조회 실패 시 `RuntimeError` 예외를 expect하도록 수정
- **파일**: `backend/tests/test_overseas_support.py`
- **검증**: `cd backend && pytest tests/test_overseas_support.py -v` 전체 통과

### 0-2. users 테이블 레거시 KIS 컬럼 정리

- **문제**: `users` 테이블에 `kis_app_key_enc`, `kis_app_secret_enc`, `kis_account_no`, `kis_acnt_prdt_cd` 레거시 컬럼 존재 — `kis_accounts` 테이블로 이관 완료된 상태
- **작업**: Alembic migration으로 레거시 컬럼 drop (데이터 존재 여부 확인 후)
- **파일**: `backend/app/models/user.py`, 새 Alembic migration
- **주의**: 운영 DB에 레거시 데이터가 남아있을 수 있으므로 migration에서 null 체크 후 drop

---

## 🟠 P0 — 모니터링 & 가시성

### 1-1. Sentry 백엔드 통합

- **목적**: 프로덕션 에러 자동 수집 (현재 structlog만 운용, 에러 알림 없음)
- **작업**:
  - `sentry-sdk[fastapi]` 설치
  - `backend/app/main.py`에 `sentry_sdk.init()` 추가 (DSN은 환경변수)
  - 글로벌 예외 핸들러에 Sentry 전송 연동
  - `backend/.env.example`에 `SENTRY_DSN` 추가
- **파일**: `backend/requirements.txt`, `backend/app/main.py`, `backend/app/core/config.py`
- **참고**: DSN은 사용자가 직접 설정 (`manual-tasks.md` 참조)

### 1-2. Sentry 프론트엔드 통합

- **목적**: 프론트엔드 런타임 에러 + 성능 모니터링
- **작업**:
  - `@sentry/nextjs` 설치
  - `sentry.client.config.ts`, `sentry.server.config.ts` 생성
  - `next.config.ts`에 Sentry webpack 플러그인 추가
  - `NEXT_PUBLIC_SENTRY_DSN` 환경변수 설정
  - Error Boundary에 Sentry `captureException` 연동
- **파일**: `frontend/package.json`, `frontend/sentry.*.config.ts`, `frontend/next.config.ts`, `frontend/src/components/ErrorBoundary.tsx`

### 1-3. API 응답 시간 메트릭 미들웨어

- **목적**: 엔드포인트별 응답시간 추적 (현재 structlog에 request_id만 있고, 응답시간 메트릭 없음)
- **작업**:
  - `backend/app/core/middleware.py`에 `MetricsMiddleware` 추가
  - 요청마다 `process_time` 측정 → structlog에 기록
  - `X-Process-Time` 응답 헤더 추가
  - `/api/v1/health`에 최근 5분 평균 응답시간 포함 (선택)
- **파일**: `backend/app/core/middleware.py`, `backend/app/main.py`

---

## 🟡 P1 — 프론트엔드 테스트 커버리지

### 2-1. 대시보드 페이지 컴포넌트 테스트

- **목적**: 백엔드 92% 대비 프론트엔드 테스트 거의 없음
- **작업**:
  - `app/dashboard/page.tsx` 렌더링 테스트 (데이터 로딩, 에러 상태, 빈 상태)
  - TanStack Query mock + MSW(Mock Service Worker) 설정
  - 포트폴리오 요약 카드, 보유종목 테이블, 도넛 차트 렌더링 확인
- **파일**: `frontend/src/app/dashboard/page.test.tsx`, `frontend/src/test/setup.ts`
- **검증**: `cd frontend && npm test -- --run`

### 2-2. 포트폴리오 목록/상세 페이지 테스트

- **작업**:
  - 포트폴리오 목록 렌더링 테스트
  - 포트폴리오 상세 (보유종목 + 거래내역) 렌더링 테스트
  - CRUD 액션 (생성, 삭제) 인터랙션 테스트
- **파일**: `frontend/src/app/dashboard/portfolios/page.test.tsx`, `frontend/src/app/dashboard/portfolios/[id]/page.test.tsx`

### 2-3. HoldingsTable 컴포넌트 단위 테스트

- **작업**:
  - 정렬 기능 테스트 (멀티 컬럼)
  - PnLBadge 색상 규칙 (양수=빨강, 음수=파랑, 0=회색)
  - 빈 데이터 처리
  - 해외주식 USD 표시 확인
- **파일**: `frontend/src/components/HoldingsTable.test.tsx`

### 2-4. MSW(Mock Service Worker) 테스트 인프라 구성

- **목적**: 프론트엔드 테스트에서 API 호출을 일관성 있게 모킹
- **작업**:
  - `msw` 패키지 설치
  - `frontend/src/test/handlers.ts`에 주요 API 핸들러 정의
  - `frontend/src/test/server.ts`에 MSW 서버 설정
  - Vitest `setupFiles`에 MSW 연동
- **파일**: `frontend/package.json`, `frontend/src/test/handlers.ts`, `frontend/src/test/server.ts`, `frontend/vitest.config.ts`
- **참고**: 이 태스크를 2-1, 2-2, 2-3보다 먼저 구현

---

## 🟡 P1 — 알림 시스템 완성

### 3-1. 인앱 알림 센터 (백엔드)

- **문제**: SSE에서 가격 조건 체크는 되지만 사용자에게 보이는 알림이 없음
- **작업**:
  - `notifications` 테이블 추가 (user_id, type, title, message, is_read, created_at)
  - Alembic migration
  - `POST /alerts` 조건 트리거 시 → notifications 테이블에 레코드 생성
  - `GET /notifications` — 미읽음 우선, 페이지네이션
  - `PATCH /notifications/{id}/read` — 읽음 처리
  - `POST /notifications/read-all` — 전체 읽음
- **파일**: `backend/app/models/notification.py`, `backend/app/schemas/notification.py`, `backend/app/api/notifications.py`, Alembic migration

### 3-2. 인앱 알림 센터 (프론트엔드)

- **작업**:
  - Sidebar/BottomNav에 알림 벨 아이콘 + 미읽음 배지 추가
  - 알림 드롭다운 패널 (최근 알림 목록, 읽음 처리)
  - SSE 가격 스트림에서 triggered_alerts 수신 시 → sonner toast + notification fetch
  - TanStack Query로 알림 목록 캐싱
- **파일**: `frontend/src/components/NotificationCenter.tsx`, `frontend/src/components/Sidebar.tsx`, `frontend/src/components/BottomNav.tsx`

---

## 🟡 P1 — 분석 기능 강화

### 4-1. 벤치마크 비교 (KOSPI200 / S&P500)

- **목적**: 포트폴리오 수익률과 시장 지수 비교 (todo.md 11-2에 명시)
- **작업**:
  - `price_snapshots` 테이블에 인덱스 종목도 저장 (ticker: `^KOSPI200`, `^SPX`)
  - 일일 스냅샷 스케줄러에 인덱스 데이터 수집 추가 (KIS `FHKUP03500100` TR)
  - `GET /analytics/portfolio-history`에 `benchmark` 쿼리 파라미터 추가
  - PortfolioHistoryChart에 벤치마크 오버레이 라인 추가
- **파일**: `backend/app/services/price_snapshot.py`, `backend/app/api/analytics.py`, `frontend/src/components/PortfolioHistoryChart.tsx`

### 4-2. 투자 성과 지표 확장 (Sharpe, MDD, CAGR)

- **목적**: 기본 수익률 외 고급 성과 지표 제공
- **작업**:
  - `backend/app/services/metrics.py` 생성
  - `calculate_sharpe_ratio(returns, risk_free_rate)` — 무위험수익률 대비 초과수익/변동성
  - `calculate_mdd(portfolio_values)` — 최대 낙폭 (고점 대비 최저점)
  - `calculate_cagr(start_value, end_value, years)` — 연평균 복합 성장률
  - `GET /analytics/metrics` 응답에 sharpe, mdd, cagr 필드 추가
  - Analytics 페이지에 MetricCard 추가
- **파일**: `backend/app/services/metrics.py`, `backend/app/api/analytics.py`, `frontend/src/app/dashboard/analytics/page.tsx`
- **참고**: price_snapshots 데이터가 충분해야 의미 있는 값 산출 가능 — 데이터 부족 시 "데이터 수집 중" 표시

### 4-3. 포트폴리오 수익률 기간 필터

- **목적**: 1주/1개월/3개월/6개월/1년/전체 기간별 수익률 필터링
- **작업**:
  - `GET /analytics/portfolio-history`에 `period` 쿼리 파라미터 추가 (`1w`, `1m`, `3m`, `6m`, `1y`, `all`)
  - PortfolioHistoryChart에 기간 선택 탭 UI 추가
  - 기간별로 price_snapshots 필터링 후 반환
- **파일**: `backend/app/api/analytics.py`, `frontend/src/components/PortfolioHistoryChart.tsx`

---

## 🟢 P2 — 새로운 기능 (Ideation)

### 5-1. 거래 메모 & 투자 일지

- **목적**: 거래 시 이유/메모를 기록하여 투자 의사결정 복기 지원
- **작업**:
  - `transactions` 테이블에 `memo` 컬럼 추가 (nullable, TEXT)
  - `POST /portfolios/{id}/transactions` 요청에 `memo` 필드 추가
  - 거래내역 목록에 메모 표시 (접이식/툴팁)
  - 포트폴리오 상세 페이지에서 메모 인라인 편집
- **파일**: `backend/app/models/transaction.py`, `backend/app/schemas/portfolio.py`, Alembic migration, `frontend/src/app/dashboard/portfolios/[id]/page.tsx`

### 5-2. 배당금 추적 기본 구조

- **목적**: 배당 수익 기록 및 배당 캘린더 (todo.md 11-2에 명시)
- **작업**:
  - `dividends` 테이블 생성 (id, portfolio_id, ticker, name, amount, currency, ex_date, pay_date, created_at)
  - CRUD 엔드포인트: `GET/POST/DELETE /portfolios/{id}/dividends`
  - 분석 페이지에 월별/연별 배당 수익 차트 (Recharts BarChart)
  - 대시보드 요약에 `total_dividend_income` 필드 추가
- **파일**: `backend/app/models/dividend.py`, `backend/app/api/dividends.py`, Alembic migration, `frontend/src/components/DividendChart.tsx`

### 5-3. 포트폴리오 비교 뷰

- **목적**: 복수 포트폴리오 간 수익률/섹터 배분 비교
- **작업**:
  - `GET /analytics/compare?portfolio_ids=1,2,3` 엔드포인트 추가
  - 포트폴리오별 총 수익률, 섹터 배분, 기간 수익률 비교 데이터 반환
  - 비교 페이지 또는 모달 UI (테이블 + 오버레이 차트)
- **파일**: `backend/app/api/analytics.py`, `frontend/src/app/dashboard/analytics/compare/page.tsx`

### 5-4. 목표 자산 설정 & 진행률 위젯

- **목적**: 목표 자산액 설정 후 현재 달성률 추적
- **작업**:
  - `portfolios` 테이블에 `target_value` 컬럼 추가 (nullable, Numeric)
  - `PATCH /portfolios/{id}`에서 target_value 설정 가능
  - 대시보드에 목표 달성률 프로그레스 바 위젯
  - `GET /dashboard/summary` 응답에 `target_value`, `target_progress_pct` 추가
- **파일**: `backend/app/models/portfolio.py`, Alembic migration, `frontend/src/components/TargetProgressWidget.tsx`

### 5-5. 손익분기점 시각화

- **목적**: 보유종목별 평균 매입가 대비 현재가 위치를 직관적으로 표시
- **작업**:
  - HoldingsTable에 미니 게이지 바 추가: 52주 최저/최고 범위 내 현재가 위치 + 평균 매입가 마커
  - 종목 상세 페이지의 캔들스틱 차트에 평균 매입가 수평선 오버레이
- **파일**: `frontend/src/components/HoldingsTable.tsx`, `frontend/src/components/CandlestickChart.tsx`
- **참고**: todo.md 11-3 "52-week high/low position bar" 및 11-4 "My holdings overlay" 항목과 연계

### 5-6. 환율 변동 영향 분석

- **목적**: 해외주식 보유 시 환율 변동이 수익률에 미치는 영향 분리 표시
- **작업**:
  - `GET /analytics/metrics`에 `currency_impact` 필드 추가 (환율 변동 기여분)
  - 해외주식 수익률을 "주가 변동 기여 + 환율 변동 기여"로 분리 계산
  - Analytics 페이지에 환율 영향 카드 추가
- **파일**: `backend/app/api/analytics.py`, `frontend/src/app/dashboard/analytics/page.tsx`
- **전제**: 환율 히스토리 데이터 수집 필요 (Bank of Korea ECOS API 또는 KIS 환율 API)

### 5-7. 리밸런싱 제안 도구

- **목적**: 목표 배분 대비 현재 배분 차이 시각화 + 리밸런싱 필요 수량 계산
- **작업**:
  - 포트폴리오별 목표 섹터/종목 배분 설정 UI
  - `target_allocations` 테이블 (portfolio_id, category, target_pct)
  - 현재 배분 vs 목표 배분 비교 차트 (Recharts 중첩 BarChart)
  - 리밸런싱 필요 매수/매도 수량 자동 계산
- **파일**: `backend/app/models/target_allocation.py`, `backend/app/api/rebalancing.py`, `frontend/src/app/dashboard/portfolios/[id]/rebalance/page.tsx`

---

## 🟢 P2 — 인프라 & DX 개선

### 6-1. ETag 기반 대시보드 캐싱

- **목적**: 대시보드 데이터 미변경 시 304 반환으로 네트워크/서버 부하 감소
- **작업**:
  - 대시보드 응답 데이터의 해시값으로 ETag 생성
  - `If-None-Match` 헤더 비교 → 동일하면 304 반환
  - Axios 인터셉터에 ETag 캐싱 로직 추가
- **파일**: `backend/app/api/dashboard.py`, `frontend/src/lib/api.ts`

### 6-2. Multi-worker uvicorn 구성

- **목적**: 단일 워커 → 2+ 워커로 동시 처리량 증가
- **작업**:
  - `gunicorn` + `uvicorn.workers.UvicornWorker` 설정
  - APScheduler 중복 실행 방지: Redis 분산 락 (`redis-lock`) 적용
  - SSE 연결 카운터를 Redis로 이동 (워커 간 공유)
  - Dockerfile `ENTRYPOINT` 수정
- **파일**: `backend/gunicorn.conf.py`, `backend/requirements.txt`, `backend/app/services/scheduler.py`, `backend/Dockerfile`
- **주의**: APScheduler dedup + SSE 관리가 핵심 — 단순 워커 증가만으로는 부작용 발생

### 6-3. Docker 볼륨 디스크 사용량 모니터링

- **목적**: pg_data, redis_data 볼륨 디스크 부족 사전 감지
- **작업**:
  - `scripts/check-disk-usage.sh` 스크립트 생성 (df 기반 볼륨 사용량 체크)
  - 임계값(80%) 초과 시 `sync_logs`에 경고 기록
  - health endpoint에 `disk_usage` 필드 추가
  - cron 또는 APScheduler job으로 1일 1회 실행
- **파일**: `scripts/check-disk-usage.sh`, `backend/app/api/health.py`

### 6-4. Storybook 컴포넌트 카탈로그 초기 설정

- **목적**: UI 컴포넌트 독립 개발/테스트 환경 (todo.md 16-3에 명시)
- **작업**:
  - Storybook 8 설치 + Next.js 16 연동
  - 핵심 컴포넌트 스토리 작성: `PnLBadge`, `DayChangeBadge`, `AllocationDonut`, `HoldingsTable`
  - Tailwind v4 + shadcn/ui 테마 연동
- **파일**: `frontend/.storybook/`, `frontend/src/components/*.stories.tsx`

---

## 🔵 P3 — 장기 개선 (Future)

### 7-1. i18n 국제화 (한국어/영어)

- **작업**: `next-intl` 설치, 메시지 카탈로그 생성, 컴포넌트 텍스트 교체
- **파일**: `frontend/src/i18n/`, `frontend/src/app/[locale]/`
- **참고**: todo.md 11-5에 명시

### 7-2. 온보딩 투어

- **작업**: `react-joyride` 설치, 첫 로그인 시 대시보드 주요 기능 가이드 투어
- **파일**: `frontend/src/components/OnboardingTour.tsx`
- **참고**: todo.md 11-5에 명시

### 7-3. Excel 내보내기 (서식 포함)

- **작업**: `openpyxl` 활용, 보유종목/거래내역을 서식 있는 .xlsx로 내보내기
- **파일**: `backend/app/api/portfolio_export.py`
- **참고**: todo.md 15-4에 명시. 현재 CSV 내보내기만 구현됨

### 7-4. 세금 계산기 (국내/해외 양도소득세)

- **작업**: 국내 주식 대주주 양도세, 해외 주식 250만원 공제 후 22% 계산
- **파일**: `backend/app/services/tax_calculator.py`, `frontend/src/app/dashboard/tax/page.tsx`

### 7-5. 포트폴리오 공유 (익명 링크)

- **작업**: 공유 토큰 발급, 종목명 마스킹 옵션, 읽기 전용 공개 페이지
- **파일**: `backend/app/api/sharing.py`, `frontend/src/app/shared/[token]/page.tsx`

### 7-6. Claude API 포트폴리오 분석 요약

- **작업**: Claude API로 보유종목/수익률 데이터 분석 후 자연어 요약 생성
- **파일**: `backend/app/services/ai_insight.py`, `frontend/src/components/AIInsightCard.tsx`
- **참고**: todo.md 13-3에 명시

---

## 구현 순서 권장

```
Phase 1 (안정화):
  0-1 → 0-2 → 1-1 → 1-2 → 1-3

Phase 2 (테스트 기반 확보):
  2-4(MSW) → 2-1 → 2-2 → 2-3

Phase 3 (핵심 기능 완성):
  3-1 → 3-2 → 4-3 → 4-1 → 4-2

Phase 4 (사용자 가치 확장):
  5-1 → 5-5 → 5-4 → 5-2 → 5-3

Phase 5 (인프라 성숙):
  6-1 → 6-3 → 6-2 → 6-4

Phase 6 (장기):
  7-1 → 7-2 → 7-3 → 7-6 → 7-4 → 7-5
```

---

## 참고: 기존 manual-tasks.md 미완료 항목 연계

| manual-tasks 항목 | 본 문서 연계 |
|---|---|
| Sentry DSN 설정 | 1-1, 1-2 (코드 통합 후 사용자가 DSN 설정) |
| UptimeRobot/Betterstack 모니터링 | 사용자 수동 설정 유지 |
| DB Backup 외부 스토리지 (S3) | 사용자 수동 설정 유지 |
| 해외주식 52주 범위 API 확인 | 5-5 구현 시 KIS API 조사 필요 |
| 해외주식 캔들차트 | 5-5 구현 시 KIS 해외주식 일봉 TR_ID 확인 필요 |
| 섹터 배분 ETF 매핑 | 4-1 벤치마크 구현 시 함께 검토 |
