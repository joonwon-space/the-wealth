# 프로젝트 분석

## 1. 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        Client (Browser)                      │
│   Next.js 16 App Router + React 19 + Tailwind v4 + shadcn   │
│   ├── SSR (Server Components)                                │
│   ├── TanStack Query (server state, cache, refetch)          │
│   ├── Zustand (auth store)                                   │
│   ├── Axios (JWT interceptor + auto refresh)                 │
│   └── SSE (usePriceStream hook)                              │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/SSE (port 3000 → 8000)
┌────────────────────▼────────────────────────────────────────┐
│                     FastAPI Backend                           │
│   ├── 80 API endpoints (20 routers — analytics/portfolios split into sub-files)  │
│   ├── JWT auth + IDOR prevention                             │
│   ├── slowapi rate limiter (30-60/min per endpoint)          │
│   ├── SecurityHeadersMiddleware                              │
│   ├── APScheduler (sync 1h, snapshot KST 16:10)             │
│   └── structlog (request_id tracing)                         │
└──┬──────────────┬──────────────┬────────────────────────────┘
   │              │              │
   ▼              ▼              ▼
┌──────┐    ┌──────────┐    ┌──────────────────┐
│ PG16 │    │ Redis 7  │    │ KIS OpenAPI      │
│      │    │          │    │ (한국투자증권)     │
│10 TB │    │ JWT JTI  │    │ ├─ oauth2/tokenP │
│      │    │ KIS Token│    │ ├─ 현재가 조회    │
│      │    │ Price $  │    │ ├─ 일별 OHLCV    │
│      │    │ Stock DB │    │ └─ 잔고 조회      │
└──────┘    └──────────┘    └──────────────────┘
```

---

## 2. 프론트엔드 아키텍처

### 2.1 기술 스택 상세

| 라이브러리 | 버전 | 용도 |
|-----------|------|------|
| Next.js | 16.2.0 | App Router, SSR, 미들웨어 |
| React | 19.2.4 | UI 렌더링 |
| TypeScript | 5 | 타입 안전성 |
| Tailwind CSS | 4.2.2 | 유틸리티 기반 스타일링 |
| shadcn/ui | 4.1.0 | UI 컴포넌트 (base-nova/neutral) |
| TanStack Table | 8.21.3 | 보유종목 데이터 테이블 |
| TanStack Query | 5.91.0 | 서버 상태 관리 (캐시, refetchInterval) |
| Recharts | 3.8.0 | 도넛 차트, 히트맵 |
| lightweight-charts | 5.1.0 | 캔들스틱 차트 |
| Axios | 1.13.6 | HTTP 클라이언트 |
| Zustand | 5.0.12 | 클라이언트 상태 관리 (인증) |
| next-themes | 0.4.6 | 다크/라이트 테마 |
| Vitest | 4.1.0 | 단위 테스트 |
| Playwright | 1.58.2 | E2E 테스트 |

### 2.2 디렉토리 구조

```
frontend/src/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # 루트 레이아웃
│   ├── page.tsx                  # 루트 페이지 (/ → 리다이렉트)
│   ├── login/                    # 로그인 페이지
│   ├── register/                 # 회원가입 페이지
│   └── dashboard/                # 대시보드 (인증 필요)
│       ├── page.tsx              # 메인 대시보드 (thin shim, DashboardMetrics+PortfolioList 위임)
│       ├── DashboardMetrics.tsx  # 총 자산/수익 카드 컴포넌트
│       ├── PortfolioList.tsx     # 포트폴리오 목록 위젯
│       ├── error.tsx             # 대시보드 에러 바운더리
│       ├── layout.tsx            # 대시보드 레이아웃 (사이드바+하단 네비)
│       ├── analytics/            # 분석 페이지
│       ├── compare/              # 포트폴리오 비교 페이지
│       ├── journal/              # 투자 일지 페이지
│       ├── portfolios/           # 포트폴리오 목록/상세
│       │   ├── page.tsx          # 포트폴리오 목록
│       │   └── [id]/             # 포트폴리오 상세 (거래내역)
│       ├── stocks/[ticker]/      # 종목 상세 (캔들스틱 차트)
│       └── settings/             # 설정
├── components/
│   ├── AllocationDonut.tsx       # 자산 배분 도넛 차트
│   ├── BottomNav.tsx             # 모바일 하단 네비게이션
│   ├── CandlestickChart.tsx      # 캔들스틱 차트 (lightweight-charts)
│   ├── DayChangeBadge.tsx        # 일간 변동률 뱃지 (상승=빨강/하락=파랑)
│   ├── DynamicCharts.tsx         # 동적 import 차트 래퍼 (번들 최적화)
│   ├── ErrorBoundary.tsx         # React Error Boundary + fallback UI
│   ├── HoldingsTable.tsx         # 보유종목 테이블 (TanStack Table)
│   ├── KeyboardShortcutsDialog.tsx # 키보드 단축키 도움말 (Cmd+?)
│   ├── MonthlyHeatmap.tsx        # 월별 수익률 히트맵
│   ├── PnLBadge.tsx              # 수익/손실 뱃지 (상승=빨강/하락=파랑)
│   ├── PortfolioHistoryChart.tsx  # 포트폴리오 가치 추이
│   ├── SectorAllocationChart.tsx  # 섹터별 배분 차트
│   ├── Sidebar.tsx               # 데스크톱 사이드바
│   ├── StockSearchDialog.tsx     # Cmd+K 종목 검색
│   ├── ThemeProvider.tsx         # next-themes 테마 프로바이더
│   ├── TransactionChart.tsx      # 거래내역 차트 (월별 매수/매도)
│   ├── TopHoldingsWidget.tsx     # 상위 보유종목 위젯
│   ├── WatchlistSection.tsx      # 관심종목 섹션
│   ├── QueryProvider.tsx         # TanStack Query 프로바이더 (QueryClientProvider)
│   ├── PageError.tsx             # 페이지 에러 표시 컴포넌트
│   ├── CardSkeleton.tsx          # 카드 로딩 스켈레톤
│   ├── ChartSkeleton.tsx         # 차트 로딩 스켈레톤
│   ├── TableSkeleton.tsx         # 테이블 로딩 스켈레톤
│   ├── NotificationBell.tsx     # 알림 벨 아이콘 + 미읽음 배지 + 드롭다운
│   ├── OrderDialog.tsx          # 매수/매도 주문 다이얼로그 오케스트레이터
│   ├── PendingOrdersPanel.tsx   # 미체결 주문 패널 (주문 취소, 체결 알림)
│   ├── SentryInit.tsx           # Sentry 초기화 (프로덕션 전용)
│   ├── dashboard/               # 대시보드 서브컴포넌트
│   │   ├── DashboardMetrics.tsx # 총 자산/수익 카드 (page.tsx에서 분리)
│   │   └── PortfolioList.tsx    # 대시보드 포트폴리오 목록 (page.tsx에서 분리)
│   ├── orders/                  # 주문 서브컴포넌트
│   │   ├── OrderForm.tsx        # 주문 입력 폼 (지정가/시장가, 빠른비율)
│   │   └── OrderConfirmation.tsx # 주문 확인 스텝
│   └── ui/                       # shadcn/ui 컴포넌트
├── hooks/
│   ├── useCountUp.ts              # 숫자 카운트업 애니메이션 훅
│   ├── useDebounce.ts            # 검색 입력 디바운스 훅
│   ├── usePriceStream.ts         # SSE 실시간 가격 스트리밍 훅
│   ├── useNotifications.ts      # 알림 센터 TanStack Query 훅 (목록, 읽음, 전체 읽음)
│   └── useOrders.ts             # 주문 TanStack Query 훅 (주문, 예수금, 미체결, 취소)
├── lib/
│   ├── api.ts                    # Axios 인스턴스 (JWT interceptor)
│   ├── format.ts                 # 숫자/날짜 포맷팅 유틸리티
│   ├── debounce.ts               # 디바운스 유틸리티
│   └── utils.ts                  # cn() 등 일반 유틸리티
├── store/
│   └── auth.ts                   # Zustand 인증 스토어
└── types/
    ├── api.ts                    # API 응답 타입
    └── index.ts                  # 공통 타입 정의
```

### 2.3 shadcn/ui DataTable 전략

보유종목 테이블(`HoldingsTable.tsx`)은 **TanStack Table v8**과 **shadcn/ui Table** 컴포넌트를 결합하여 구현:

```
┌─────────────────────────────────────────────────────┐
│ HoldingsTable (TanStack Table v8)                   │
│ ┌─────────┬──────┬───────┬──────┬──────┬─────────┐ │
│ │ 종목명   │ 수량 │ 평균가 │ 현재가│ 수익률│ 수익/손실│ │
│ ├─────────┼──────┼───────┼──────┼──────┼─────────┤ │
│ │ 삼성전자 │ 100  │ 60,000│68,000│+13.3%│+800,000 │ │
│ │ SK하이닉 │  50  │120,000│95,000│-20.8%│-1,250K  │ │
│ │ 카카오   │  30  │ 45,000│42,000│ -6.7%│ -90,000 │ │
│ └─────────┴──────┴───────┴──────┴──────┴─────────┘ │
│ ↕ 멀티 컬럼 정렬 지원                                │
└─────────────────────────────────────────────────────┘
```

핵심 구현 패턴:

- **멀티 컬럼 정렬**: TanStack Table의 `getSortedRowModel` 활용
- **현재가 컬럼**: KIS API에서 동적으로 가져온 가격 — DB에 저장하지 않음
- **수익률/수익금**: `(현재가 - 평균 매입가) / 평균 매입가 * 100`으로 실시간 계산
- **컬러 컨벤션**: `PnLBadge`/`DayChangeBadge`로 상승(빨강)/하락(파랑) 시각 구분
- **shadcn/ui Table**: `<Table>`, `<TableHeader>`, `<TableBody>`, `<TableRow>`, `<TableCell>` 래핑

### 2.4 차트 시각화 전략

#### Recharts (도넛 차트, 히트맵, 라인 차트)

```
┌──────────────────────────────────┐
│       AllocationDonut            │
│   ┌────────────────────────┐     │
│   │    ╭──────────╮        │     │
│   │   ╱   IT 35%   ╲       │     │
│   │  │   ┌──────┐   │      │     │
│   │  │   │ 총자산 │   │      │     │
│   │  │   │ 15.2M │   │      │     │
│   │  │   └──────┘   │      │     │
│   │   ╲  금융 25%  ╱       │     │
│   │    ╰──────────╯        │     │
│   │     소비재 20%          │     │
│   │     기타 20%            │     │
│   └────────────────────────┘     │
│   PieChart + center overlay text │
└──────────────────────────────────┘
```

- **AllocationDonut**: `<PieChart>` + 중앙 텍스트 오버레이로 총 자산 표시
- **MonthlyHeatmap**: 월별 수익률을 색상 강도로 표현
- **PortfolioHistoryChart**: 기간별 포트폴리오 가치 변동 라인 차트
- **SectorAllocationChart**: 섹터별 비중 차트

#### lightweight-charts (캔들스틱 차트)

```
┌──────────────────────────────────┐
│       CandlestickChart           │
│   ┌────────────────────────┐     │
│   │  ║    │                │     │
│   │  ║    ║  │    │        │     │
│   │  ║    ║  ║    │  │     │     │
│   │  │    ║  ║    ║  ║     │     │
│   │  │    │  ║    ║  ║     │     │
│   │       │  │    ║  │     │     │
│   │              │    │     │     │
│   └────────────────────────┘     │
│   TradingView lightweight-charts │
└──────────────────────────────────┘
```

- TradingView의 `lightweight-charts` 5.1.0 사용
- 일봉 OHLCV 데이터를 KIS API(`FHKST01010400`)에서 조회
- `usePriceStream` 훅으로 실시간 가격 업데이트 반영

### 2.5 프론트엔드 인증 패턴

```
┌──────────────────────────────────────────────────────┐
│ Zustand Auth Store                                    │
│  state: { accessToken, user, isAuthenticated }        │
│  persist: localStorage + cookie (dual write)          │
└────────┬─────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│ Next.js Edge Middleware                               │
│  - cookie에서 auth 토큰 확인                           │
│  - 미인증 시 /login 리다이렉트                          │
└────────┬─────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│ Axios Interceptor                                     │
│  Request: Authorization: Bearer {accessToken}         │
│  Response 401: auto refresh → retry original request  │
└──────────────────────────────────────────────────────┘
```

### 2.6 SSE 실시간 가격 스트리밍

`usePriceStream` 훅 동작 방식:

1. `GET /prices/stream?token={jwt}` 엔드포인트에 SSE 연결
2. 30초 간격으로 보유종목 현재가 전송
3. KST 09:00~15:30 (한국 장중)에만 활성화
4. 연결 해제 시 자동 재연결

---

## 3. 백엔드 아키텍처

### 3.1 기술 스택 상세

| 라이브러리 | 버전 | 용도 |
|-----------|------|------|
| FastAPI | 0.135.1 | 웹 프레임워크 |
| uvicorn | 0.42.0 | ASGI 서버 |
| SQLAlchemy | 2.0.48 | async ORM |
| asyncpg | 0.31.0 | PostgreSQL async 드라이버 |
| Alembic | 1.18.4 | DB 마이그레이션 |
| Pydantic | 2.12.5 | 스키마 검증 |
| PyJWT | 2.12.1 | JWT 토큰 |
| bcrypt | 5.0.0 | 비밀번호 해싱 |
| cryptography | 46.0.6 | AES-256-GCM 암호화 |
| redis | 7.3.0 | async Redis 클라이언트 |
| httpx | 0.28.1 | async HTTP (KIS API) |
| APScheduler | 3.11.2 | 백그라운드 스케줄러 |
| slowapi | 0.1.9 | 레이트 리미팅 |
| structlog | 25.4.0 | 구조화 로깅 |

### 3.2 디렉토리 구조

```
backend/app/
├── main.py                    # FastAPI app, CORS, 미들웨어, 라우터 등록
├── api/                       # 17개 API 라우터 + 공통 의존성
│   ├── deps.py                # get_current_user, get_current_user_sse 인증 의존성
│   ├── auth.py                # 인증 (register, login, refresh, change-password, logout)
│   ├── portfolios.py          # 포트폴리오 CRUD (thin shim: holdings/transactions 분리)
│   ├── portfolio_holdings.py  # 보유종목 CRUD + 일괄등록
│   ├── portfolio_transactions.py # 거래내역 CRUD + cursor 페이지네이션 + KIS 체결내역
│   ├── portfolio_export.py    # CSV 내보내기 (보유종목 + 거래내역)
│   ├── dashboard.py           # 대시보드 요약
│   ├── analytics.py           # thin re-export shim (→ analytics_metrics/history/fx)
│   ├── analytics_metrics.py   # 수익률 지표, 월별 수익률, 섹터 배분
│   ├── analytics_history.py   # 포트폴리오 히스토리, 원화 환산 자산 추이
│   ├── analytics_fx.py        # 환차익/환차손 분리, 환율 히스토리
│   ├── alerts.py              # 가격 알림 CRUD + 활성화/비활성화
│   ├── notifications.py       # 인앱 알림 센터 (목록, 읽음 처리)
│   ├── stocks.py              # 종목 검색/상세
│   ├── sync.py                # KIS 계좌 동기화
│   ├── users.py               # KIS 계좌 관리
│   ├── chart.py               # 차트 데이터
│   ├── prices.py              # 가격 히스토리, SSE 스트림
│   ├── watchlist.py           # 관심종목
│   ├── orders.py              # 주문 (매수/매도, 미체결, 취소, 예수금)
│   ├── health.py              # 헬스체크 (DB, Redis, KIS, backup 상태)
│   └── internal.py            # 내부 API (백업 상태 기록)
├── core/
│   ├── config.py              # Pydantic Settings (환경변수)
│   ├── security.py            # JWT 생성/검증, bcrypt, refresh token rotation
│   ├── encryption.py          # AES-256-GCM 암호화/복호화
│   ├── limiter.py             # slowapi 레이트 리미터 인스턴스
│   ├── middleware.py          # SecurityHeadersMiddleware
│   ├── redis_cache.py         # Redis 캐시 래퍼 (Redis 장애 시 in-memory 폴백)
│   ├── logging.py             # structlog 설정, request_id
│   └── ticker.py              # is_domestic() 유틸리티 (국내/해외 종목 판별)
├── middleware/
│   └── metrics.py             # MetricsMiddleware (X-Process-Time 헤더 + structlog process_time_ms)
├── db/
│   ├── base.py                # SQLAlchemy Base
│   └── session.py             # AsyncSession 팩토리
├── models/                    # SQLAlchemy ORM 모델 (14 테이블)
│   ├── user.py
│   ├── portfolio.py
│   ├── holding.py
│   ├── transaction.py
│   ├── kis_account.py
│   ├── alert.py
│   ├── notification.py
│   ├── watchlist.py
│   ├── price_snapshot.py
│   ├── fx_rate_snapshot.py
│   ├── order.py
│   ├── sync_log.py
│   ├── index_snapshot.py      # KOSPI200/S&P500 지수 스냅샷 (벤치마크)
│   └── security_audit_log.py  # 보안 감사 로그 (로그인/비밀번호 변경 등)
├── schemas/                   # Pydantic 검증 스키마
│   ├── auth.py
│   ├── portfolio.py
│   ├── dashboard.py
│   ├── order.py
│   ├── analytics.py
│   ├── notification.py
│   └── user.py
├── services/                  # 비즈니스 로직
│   ├── kis_token.py           # KIS OAuth2 토큰 관리
│   ├── kis_price.py           # 현재가/OHLCV 조회 (병렬)
│   ├── kis_account.py         # KIS 잔고 조회
│   ├── kis_balance.py         # KIS 예수금 조회 (국내 TTTC8434R + 해외 TTTS3012R)
│   ├── kis_order.py           # KIS 주문 thin re-export shim (→ kis_order_place/cancel/query)
│   ├── kis_order_place.py     # 국내/해외 매수/매도 주문 실행
│   ├── kis_order_cancel.py    # 주문 취소
│   ├── kis_order_query.py     # 미체결 조회, 주문 가능 수량, 예수금
│   ├── kis_benchmark.py       # KOSPI200 + S&P500 지수 스냅샷 수집
│   ├── kis_transaction.py     # KIS 체결내역 조회 (국내 TTTC8001R + 해외 TTTS3035R)
│   ├── reconciliation.py      # 보유종목 동기화 로직
│   ├── price_snapshot.py      # 일일 종가 스냅샷 저장
│   ├── scheduler.py           # APScheduler 설정
│   ├── stock_search.py        # KRX 종목 검색
│   ├── backup_health.py       # 백업 파일 상태 조회
│   └── kis_health.py          # KIS API 가용성 헬스체크 (시작 시 연결 테스트)
└── data/
    └── sector_map.py          # 종목별 섹터 매핑
```

### 3.3 KIS API 비동기 병렬 호출

현재가와 P&L은 **DB에 저장하지 않고** KIS API에서 실시간으로 조회하여 동적 계산합니다:

```
대시보드 요약 요청 (GET /dashboard/summary)
  │
  ▼
DB에서 보유종목 조회 (holdings 테이블)
  │
  ▼ tickers = ["005930", "000660", "035420", ...]
  │
  ▼ asyncio.gather() 병렬 호출
  ┌──────────────────────────────────────────┐
  │ KIS API 동시 요청 (N개 종목)              │
  │ ┌────────┐ ┌────────┐ ┌────────┐        │
  │ │005930  │ │000660  │ │035420  │ ...     │
  │ │FHKST01 │ │FHKST01 │ │FHKST01 │        │
  │ │010100  │ │010100  │ │010100  │        │
  │ └───┬────┘ └───┬────┘ └───┬────┘        │
  │     │          │          │              │
  │     ▼          ▼          ▼              │
  │  68,000     95,000     42,000            │
  └──────────────────────────────────────────┘
  │
  ▼ P&L 동적 계산
  {
    ticker: "005930",
    current_price: 68000,        // KIS API 실시간
    avg_price: 60000,            // DB 저장값
    quantity: 100,               // DB 저장값
    pnl: +800000,                // (68000-60000)*100 계산
    pnl_rate: +13.33%            // 계산
  }
```

핵심 코드 패턴 (`kis_price.py`):

```python
async def fetch_prices_parallel(
    tickers: list[str], app_key: str, app_secret: str, market: str = "domestic"
) -> dict[str, Optional[Decimal]]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [fetch_domestic_price(t, app_key, app_secret, client) for t in tickers]
        results = await asyncio.gather(*tasks)
    # 실패 시 Redis 캐시 폴백
```

- **국내주식**: `FHKST01010100` TR — 응답 필드 `stck_prpr` (현재가)
- **해외주식**: `HHDFS00000300` TR — 응답 필드 `last` (현재가)
- **일별 OHLCV**: `FHKST01010400` TR — open/high/low/close/volume
- **폴백 전략**: KIS API 실패 시 Redis 캐시(`price:{ticker}`, TTL 300초)에서 마지막 가격 사용

### 3.4 스케줄러 (APScheduler)

```
┌─────────────────────────────────────────────────────────┐
│ APScheduler (AsyncIOScheduler) — 7개 cron 잡             │
│                                                         │
│ Job 1: kis_sync_us (미국 장 마감 후 동기화)               │
│   trigger: cron(mon-fri, 21:30 UTC) = KST 06:30         │
│   action: KIS 자격증명 있는 모든 사용자의 잔고 동기화      │
│   결과: sync_logs 테이블에 기록                           │
│                                                         │
│ Job 2: preload_prices_am (장 전 holdings 동기화 + 캐시)   │
│   trigger: cron(mon-fri, 23:00 UTC) = KST 08:00         │
│   action: 1) reconcile_holdings로 보유종목 최신화          │
│           2) 갱신된 holdings 기준 가격 캐시 워밍           │
│                                                         │
│ Job 3: daily_close_snapshot (일일 종가 스냅샷)            │
│   trigger: cron(mon-fri, 07:10 UTC) = KST 16:10         │
│   action: 전체 보유종목 OHLCV 조회                        │
│           → price_snapshots 테이블 저장                   │
│   폴백: OHLCV 실패 시 현재가로 close 저장                 │
│                                                         │
│ Job 4: preload_prices_pm (장 마감 후 holdings 동기화 + 캐시)│
│   trigger: cron(mon-fri, 07:00 UTC) = KST 16:00         │
│   action: 1) reconcile_holdings로 보유종목 최신화          │
│           2) 갱신된 holdings 기준 가격 캐시 워밍           │
│                                                         │
│ Job 5: fx_rate_snapshot (환율 스냅샷)                     │
│   trigger: cron(mon-fri, 07:30 UTC) = KST 16:30         │
│   action: USD/KRW 환율 조회 → fx_rate_snapshots 테이블 저장│
│                                                         │
│ Job 6: settle_orders (미체결 주문 자동 체결 확인)          │
│   trigger: cron(mon-fri, hour=9-15, minute=*/5) UTC      │
│            = KST 장중 09:00-15:00 매 5분                  │
│   action: 미체결 주문 KIS API 조회 → filled/partial 업데이트│
│                                                         │
│ Job 7: collect_benchmark (지수 스냅샷)                    │
│   trigger: cron(mon-fri, 07:20 UTC) = KST 16:20         │
│   action: KOSPI200 + S&P500 지수 스냅샷 수집              │
│           → index_snapshots 테이블 저장                   │
└─────────────────────────────────────────────────────────┘
```

### 3.5 미들웨어 체인

```
Request
  │
  ▼ SecurityHeadersMiddleware
  │   X-Content-Type-Options: nosniff
  │   X-Frame-Options: DENY
  │   Referrer-Policy: strict-origin-when-cross-origin
  │   Permissions-Policy: camera=(), microphone=(), geolocation=()
  │   X-XSS-Protection: 1; mode=block
  │
  ▼ CORSMiddleware
  │   allow_origins: localhost:3000, joonwon.dev
  │
  ▼ GZipMiddleware
  │   minimum_size: 1000 bytes (응답 압축)
  │
  ▼ Request ID Middleware
  │   X-Request-ID: uuid4 (structlog 연동)
  │
  ▼ MetricsMiddleware
  │   X-Process-Time 헤더 + structlog process_time_ms
  │
  ▼ Rate Limiter (slowapi)
  │   default: 60/minute per IP
  │
  ▼ Router → Handler
```

---

## 4. 데이터베이스 스키마 (14 테이블)

### 4.1 ERD 다이어그램

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   users     │     │  portfolios  │     │   holdings   │
├─────────────┤     ├──────────────┤     ├──────────────┤
│ id (PK)     │◄──┐ │ id (PK)      │◄──┐ │ id (PK)      │
│ email (UQ)  │   │ │ user_id (FK) │   │ │ portfolio_id │
│ hashed_pwd  │   │ │ name         │   │ │ ticker       │
│ created_at  │   │ │ currency     │   │ │ name         │
│             │   │ │ kis_account  │   │ │ quantity     │
│             │   │ │  _id (FK,UQ) │   │ │ avg_price    │
│             │   │ │ display_order│   │ │ created_at   │
│             │   │ │ created_at   │   │ └──────────────┘
└─────────────┘   │ └──────────────┘   │
      │           │         │          │
      │     ┌─────┘   ┌─────┘    ┌──────────────┐
      │     │         │          │ transactions │
      │     │         │          ├──────────────┤
      │     │         │          │ id (PK)      │
      │     │         └──────────│ portfolio_id │
      │     │                    │ ticker       │
      │     │                    │ type (B/S)   │
      │     │                    │ quantity     │
      │     │                    │ price        │
      │     │                    │ traded_at    │
      │     │                    │ deleted_at   │
      │     │                    │ memo         │
      │     │                    └──────────────┘
      │     │
      │  ┌──┴───────────┐    ┌──────────────┐
      │  │ kis_accounts │    │    alerts     │
      │  ├──────────────┤    ├──────────────┤
      ├─►│ id (PK)      │    │ id (PK)      │
      │  │ user_id (FK) │    │ user_id (FK) │◄── users
      │  │ label        │    │ ticker       │
      │  │ account_no   │    │ name         │
      │  │ acnt_prdt_cd │    │ condition    │
      │  │ app_key_enc  │    │ threshold    │
      │  │ app_secret   │    │ is_active    │
      │  │  _enc        │    │ last_trigger │
      │  │ created_at   │    │  _at         │
      │  │ UQ(user,acct,│    │ created_at   │
      │  │    prdt)     │    └──────────────┘
      │  └──────────────┘
      │
      │  ┌──────────────┐
      │  │notifications │
      │  ├──────────────┤
      ├─►│ id (PK)      │
      │  │ user_id (FK) │
      │  │ type         │
      │  │ title        │
      │  │ body         │
      │  │ is_read      │
      │  │ created_at   │
      │  └──────────────┘
      │
      │  ┌──────────────┐    ┌────────────────┐
      │  │  watchlist   │    │price_snapshots │
      │  ├──────────────┤    ├────────────────┤
      ├─►│ id (PK)      │    │ id (PK)        │
      │  │ user_id (FK) │    │ ticker         │
      │  │ ticker       │    │ snapshot_date  │
      │  │ name         │    │ open           │
      │  │ market       │    │ high           │
      │  │ added_at     │    │ low            │
      │  │ UQ(user,     │    │ close (NOT NUL)│
      │  │    ticker)   │    │ volume         │
      │  └──────────────┘    │ created_at     │
      │                      │ UQ(ticker,date)│
      │  ┌──────────────┐    └────────────────┘
      │  │  sync_logs   │
      │  ├──────────────┤
      └─►│ id (PK)      │
         │ user_id (FK) │
         │ portfolio_id │
         │ status       │
         │ inserted     │
         │ updated      │
         │ deleted      │
         │ message      │
         │ synced_at    │
         └──────────────┘

┌──────────────────┐
│ fx_rate_snapshots│
├──────────────────┤
│ id (PK)          │
│ currency_pair    │ (String, INDEX)
│ rate             │ (Numeric, NOT NULL)
│ snapshot_date    │ (Date)
│ created_at       │
│ UQ(pair, date)   │
└──────────────────┘

┌──────────────────┐
│ index_snapshots  │
├──────────────────┤
│ id (PK)          │
│ index_code       │ (String, INDEX) KOSPI200/SP500
│ timestamp        │ (DateTime tz)
│ close_price      │ (Numeric, NOT NULL)
│ change_pct       │ (Numeric, nullable)
│ created_at       │
│ UQ(code, ts)     │
└──────────────────┘

┌─────────────────────┐
│ security_audit_logs │
├─────────────────────┤
│ id (PK)             │
│ user_id (FK, SET NULL)│◄── users
│ action              │ (Enum: LOGIN_SUCCESS/FAILURE/LOGOUT/...)
│ ip_address          │ (String, nullable)
│ user_agent          │ (Text, nullable)
│ extra               │ (JSONB, nullable)
│ created_at          │
└─────────────────────┘

┌──────────────┐
│   orders     │
├──────────────┤
│ id (PK)      │
│ portfolio_id │◄── portfolios
│ kis_account  │
│  _id (FK)    │◄── kis_accounts
│ ticker       │
│ name         │
│ order_type   │ (BUY/SELL)
│ order_class  │ (limit/market)
│ quantity     │
│ price        │
│ order_no     │
│ status       │ (pending/filled/...)
│ filled_qty   │
│ filled_price │
│ memo         │
│ created_at   │
│ updated_at   │
└──────────────┘
```

### 4.2 테이블 상세

#### users
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | 사용자 ID |
| email | String | UNIQUE, NOT NULL | 이메일 (로그인 ID) |
| name | String(100) | nullable | 사용자 이름 |
| hashed_password | String | NOT NULL | bcrypt 해시 비밀번호 |
| created_at | DateTime | default=now | 생성일시 |

#### portfolios
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | 포트폴리오 ID |
| user_id | Integer | FK→users CASCADE, NOT NULL | 소유자 |
| name | String | NOT NULL | 포트폴리오 이름 |
| currency | String | default="KRW" | 통화 |
| kis_account_id | Integer | FK→kis_accounts SET NULL, UNIQUE | 연결된 KIS 계좌 |
| display_order | Integer | NOT NULL, default=0 | 표시 순서 |
| created_at | DateTime | default=now | 생성일시 |

#### holdings
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | 보유종목 ID |
| portfolio_id | Integer | FK→portfolios CASCADE, NOT NULL | 소속 포트폴리오 |
| ticker | String | NOT NULL | 종목 코드 |
| name | String | NOT NULL | 종목명 |
| quantity | Numeric(18,6) | NOT NULL | 보유 수량 |
| avg_price | Numeric(18,4) | NOT NULL | 평균 매입가 |
| created_at | DateTime | default=now | 생성일시 |

#### transactions
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | 거래 ID |
| portfolio_id | Integer | FK→portfolios CASCADE, NOT NULL | 소속 포트폴리오 |
| ticker | String | NOT NULL | 종목 코드 |
| type | String | NOT NULL | 거래 유형 ("BUY" / "SELL") |
| quantity | Numeric | NOT NULL | 거래 수량 |
| price | Numeric | NOT NULL | 거래 가격 |
| traded_at | DateTime | NOT NULL | 거래일시 |
| deleted_at | DateTime | nullable | 소프트 삭제 일시 |
| memo | String(500) | nullable | 거래 메모 (투자 일지) |

#### kis_accounts
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | KIS 계좌 ID |
| user_id | Integer | FK→users CASCADE, NOT NULL | 소유자 |
| label | String | NOT NULL | 계좌 별칭 |
| account_no | String | NOT NULL | 계좌번호 |
| acnt_prdt_cd | String | NOT NULL | 계좌 상품코드 |
| app_key_enc | String | NOT NULL | App Key (AES-256-GCM 암호화) |
| app_secret_enc | String | NOT NULL | App Secret (AES-256-GCM 암호화) |
| created_at | DateTime | default=now | 생성일시 |
| | | UNIQUE(user_id, account_no, acnt_prdt_cd) | 복합 유니크 제약 |

#### alerts
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | 알림 ID |
| user_id | Integer | FK→users CASCADE, NOT NULL | 소유자 |
| ticker | String | NOT NULL | 종목 코드 |
| name | String | NOT NULL | 종목명 |
| condition | String | NOT NULL | 조건 ("above" / "below") |
| threshold | Numeric | NOT NULL | 목표가 |
| is_active | Boolean | default=True | 활성 여부 |
| last_triggered_at | DateTime | nullable | 마지막 트리거 시간 (쿨다운 1h) |
| created_at | DateTime | default=now | 생성일시 |

#### notifications
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | 알림 ID |
| user_id | Integer | FK→users CASCADE, NOT NULL | 소유자 |
| type | String(50) | NOT NULL, default="system" | 유형 (alert_triggered, system 등) |
| title | String(200) | NOT NULL | 알림 제목 |
| body | Text | nullable | 알림 본문 |
| is_read | Boolean | NOT NULL, default=False | 읽음 여부 |
| created_at | DateTime | default=now | 생성일시 |

#### watchlist
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | 관심종목 ID |
| user_id | Integer | FK→users CASCADE, NOT NULL | 소유자 |
| ticker | String | NOT NULL | 종목 코드 |
| name | String | NOT NULL | 종목명 |
| market | String | NOT NULL | 마켓 (KRX/NYSE/NASDAQ) |
| added_at | DateTime | default=now | 추가일시 |
| | | UNIQUE(user_id, ticker) | 사용자별 종목 유니크 |

#### price_snapshots
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | 스냅샷 ID |
| ticker | String | NOT NULL | 종목 코드 |
| snapshot_date | Date | NOT NULL | 스냅샷 날짜 |
| open | Numeric | nullable | 시가 |
| high | Numeric | nullable | 고가 |
| low | Numeric | nullable | 저가 |
| close | Numeric | NOT NULL | 종가 |
| volume | BigInteger | nullable | 거래량 |
| created_at | DateTime | default=now | 생성일시 |
| | | UNIQUE(ticker, snapshot_date) | 종목+날짜 유니크 |

#### fx_rate_snapshots
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | 스냅샷 ID |
| currency_pair | String(10) | NOT NULL, INDEX | 통화쌍 (예: USDKRW) |
| rate | Numeric(18,6) | NOT NULL | 환율 |
| snapshot_date | Date | NOT NULL | 스냅샷 날짜 |
| created_at | DateTime | default=now | 생성일시 |
| | | UNIQUE(currency_pair, snapshot_date) | 통화쌍+날짜 유니크 |

#### sync_logs
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | 로그 ID |
| user_id | Integer | FK→users CASCADE, NOT NULL | 대상 사용자 |
| portfolio_id | Integer | FK→portfolios CASCADE, NOT NULL | 대상 포트폴리오 |
| status | String | NOT NULL | 결과 ("success" / "error") |
| inserted | Integer | nullable | 신규 추가 건수 |
| updated | Integer | nullable | 수정 건수 |
| deleted | Integer | nullable | 삭제 건수 |
| message | String | nullable | 에러 메시지 (최대 500자) |
| synced_at | DateTime | default=now | 동기화 일시 |

#### index_snapshots
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | 스냅샷 ID |
| index_code | String(20) | NOT NULL, INDEX | 지수 코드 (KOSPI200, SP500) |
| timestamp | DateTime(tz) | NOT NULL | 스냅샷 시각 |
| close_price | Numeric(18,4) | NOT NULL | 종가 |
| change_pct | Numeric(8,4) | nullable | 전일 대비 변동률 (%) |
| created_at | DateTime(tz) | server_default=now | 생성일시 |
| | | UNIQUE(index_code, timestamp) | 지수+시각 유니크 |

#### security_audit_logs
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | 로그 ID |
| user_id | Integer | FK→users SET NULL, nullable | 대상 사용자 (탈퇴 시 NULL 유지) |
| action | Enum | NOT NULL | 행동 유형 (LOGIN_SUCCESS/FAILURE/LOGOUT/PASSWORD_CHANGE/ACCOUNT_DELETE/KIS_CREDENTIAL_ADD/KIS_CREDENTIAL_DELETE) |
| ip_address | String | nullable | 클라이언트 IP |
| user_agent | Text | nullable | 클라이언트 User-Agent |
| extra | JSONB | nullable | 추가 컨텍스트 (이메일 등) |
| created_at | DateTime(tz) | server_default=now | 생성일시 |

#### orders
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | 주문 ID |
| portfolio_id | Integer | FK->portfolios CASCADE, NOT NULL | 소속 포트폴리오 |
| kis_account_id | Integer | FK->kis_accounts SET NULL, nullable | KIS 계좌 |
| ticker | String(20) | NOT NULL, INDEX | 종목 코드 |
| name | String(100) | nullable | 종목명 |
| order_type | String(10) | NOT NULL | 주문 유형 ("BUY" / "SELL") |
| order_class | String(10) | NOT NULL, default="limit" | 주문 종류 ("limit" / "market") |
| quantity | Numeric(18,6) | NOT NULL | 주문 수량 |
| price | Numeric(18,4) | nullable | 주문 가격 (시장가 시 null) |
| order_no | String(50) | nullable | KIS 주문번호 |
| status | String(20) | NOT NULL, default="pending", INDEX | 상태 (pending/filled/partial/cancelled/failed) |
| filled_quantity | Numeric(18,6) | nullable | 체결 수량 |
| filled_price | Numeric(18,4) | nullable | 체결 가격 |
| memo | String(500) | nullable | 주문 메모 |
| created_at | DateTime(tz) | server_default=now | 생성일시 |
| updated_at | DateTime(tz) | server_default=now, onupdate=now | 수정일시 |

---

## 5. 보안 아키텍처

### 5.1 IDOR 방지

모든 리소스 접근 시 `user_id` 소유권 검증:

```python
# 예시: 포트폴리오 조회
portfolio = await db.get(Portfolio, portfolio_id)
if portfolio.user_id != current_user.id:
    raise HTTPException(403, "Forbidden")
```

### 5.2 보안 헤더

`SecurityHeadersMiddleware`가 모든 응답에 보안 헤더 추가:

| 헤더 | 값 |
|------|------|
| X-Content-Type-Options | nosniff |
| X-Frame-Options | DENY |
| Referrer-Policy | strict-origin-when-cross-origin |
| Permissions-Policy | camera=(), microphone=(), geolocation=() |
| X-XSS-Protection | 1; mode=block |

### 5.3 레이트 리미팅

slowapi 기반 IP별 레이트 리미팅:

| 엔드포인트 | 제한 |
|-----------|------|
| POST /auth/login | 5/min |
| POST /auth/register | 3/min |
| POST /sync/* | 5/min |
| GET /dashboard/* | 120/min |
| POST/PATCH/DELETE /portfolios/* (쓰기) | 60/min |
| POST /portfolios/{id}/orders | 10/min (Sprint 10에서 강화) |
| DELETE /portfolios/{id}/orders/* | 30/min |
| 기타 | 60/min (기본값) |

---

## 6. 프로젝트 현황 분석 (2026-04-07)

### 6.1 완성도

| 영역 | 상태 | 비고 |
|------|------|------|
| 인증 (JWT + HttpOnly Cookie) | 완료 | Refresh token rotation, IDOR 방지, 로그아웃 |
| 포트폴리오 CRUD | 완료 | CSV/Excel export, 보유종목 일괄등록, 거래내역 cursor 페이지네이션, soft delete 포함 |
| 대시보드 | 완료 | SSE 실시간, 30초 폴링, 자산 배분 도넛, 해외주식 USD 가격 표시, KIS 장애 감지 배너 |
| KIS API 연동 | 완료 | 국내/해외 현재가, OHLCV, 잔고 동기화, 장애 감지 (kis_status: degraded) |
| 분석 페이지 | 완료 | 월별 히트맵, 섹터 배분, 포트폴리오 히스토리, 환차익/환차손 분리, 원화 환산 총 자산 추이 |
| 투자 일지 | 완료 | 전용 페이지 (/dashboard/journal), 월별/종목별 필터링, 메모 키워드 검색, 최근 30일 매수 회고 위젯 |
| 종목 검색 | 완료 | Cmd+K, 초성 검색, KRX+NYSE+NASDAQ |
| 관심종목 | 완료 | 마켓별 구분 |
| 알림 | 완료 | 가격 알림 CRUD + SSE 조건 체크 + 인앱 알림 센터 (이메일 알림 미구현) |
| 주식 매매 | 완료 | 국내/해외 매수/매도 주문, 미체결 조회/취소, 예수금 조회 (국내+해외 합산), 이중 주문 방지 락 |
| 자동 동기화 | 완료 | APScheduler 7개 cron 잡: KST 06:30 미국 장 마감 sync, KST 08:00/16:00 holdings sync + 캐시 워밍, KST 16:10 일일 스냅샷, KST 16:30 환율 스냅샷, 장중 5분마다 미체결 주문 체결 확인, KST 16:20 KOSPI200+S&P500 지수 스냅샷 |
| SSE 연결 관리 | 완료 | 사용자별 최대 3 연결, 15초 하트비트, 2시간 타임아웃 |
| API 버전관리 | 완료 | /api/v1 prefix |
| 에러 처리 | 완료 | 표준 에러 응답 (envelope), Error Boundary, 전역 예외 핸들러 |
| 데이터 무결성 | 완료 | price_snapshots 갭 감지, holdings 수량 정합성, 고아 레코드 감지 |
| Commitlint | 완료 | @commitlint/config-conventional + Husky hook |
| Docker + CI/CD | 완료 | 멀티 스테이지 빌드, GitHub Actions 7개 워크플로우, self-hosted 배포 |
| 프로덕션 배포 | 운영 중 | joonwon.dev (self-hosted Docker Compose) |
| DB 백업 | 완료 | 일일 pg_dump + 보존 정책 (7일/4주/3월), health endpoint 노출 |
| 접근성 (a11y) | 완료 | aria-label, aria-current, 터치 타겟 44px, CSP 수정 |
| TanStack Query | 완료 | 대시보드/포트폴리오 캐시, refetchInterval, SSE queryClient 연동 |
| 모니터링 | 완료 | Sentry (백엔드+프론트, ENVIRONMENT 환경변수화), MetricsMiddleware (X-Process-Time) |
| 로깅 시스템 | 완료 | structlog + RotatingFileHandler (10MB x5, JSON) + Dozzle 컨테이너 로그 뷰어 |
| 응답 압축 | 완료 | GZipMiddleware (minimum_size=1000) |
| 코드 품질 | 완료 | is_domestic() 공통 유틸리티 (app/core/ticker.py), 쓰기 엔드포인트 레이트 리밋 강화 |
| DB 인덱스 최적화 | 완료 | transactions.ticker, price_snapshots(ticker, snapshot_date) 복합 인덱스 추가 |
| 보안 강화 (sprint-3) | 완료 | bcrypt DoS 방지(max_length=128), Sentry 자격증명 스크러빙, CSP 수정, tags 길이 제한 |
| 성능 최적화 (sprint-3) | 완료 | Redis ConnectionPool 싱글턴, DISTINCT ON prev_close 쿼리, fx-gain-loss 캐시, SSE React Compiler 호환 |
| 멀티 에이전트 개발 도구 | 완료 | team-implement (backend-worker + frontend-worker + infra-worker + implement-synthesizer) 병렬 구현 |
| 코드 파일 분할 (Sprint 9/10) | 완료 | analytics.py→3분할, portfolios.py→holdings+transactions, kis_order.py→place+cancel+query, dashboard/page.tsx→DashboardMetrics+PortfolioList |
| 벤치마크 수집 기반 (Sprint 10) | 완료 (데이터 수집) | IndexSnapshot 모델 + collect_benchmark 스케줄러 잡. 분석 페이지 UI 연동 미착수 |
| 미체결 주문 자동 체결 확인 (Sprint 10) | 완료 | settle_orders 스케줄러 잡 (장중 5분 주기) |
| 의존성 안정성 (Sprint 9) | 완료 | Starlette 1.0.0, pytest-asyncio 1.3.0 업그레이드. 803 테스트 통과 |

### 6.2 테스트 커버리지 (백엔드)

전체: 803 passed (Sprint 10 완료 후 기준; 2026-04-07), 78% 커버리지

CI 수정 사항:
- `test_kis_price.py` MagicMock import 누락 수정
- Redis mock 경로를 `aioredis.from_url`에서 `get_redis_client`로 통일
- conftest `client` fixture에서 Redis 풀 이벤트 루프 간 공유 문제 수정 (풀 리셋 추가)
- portfolio-detail 테스트 중복 텍스트 매칭 수정

| 모듈 | 커버리지 | 비고 |
|------|---------|------|
| core/ (security, encryption, middleware, limiter, redis_cache, logging) | 91-100% | logging.py 98% |
| models/ | 100% | ORM 모델 |
| schemas/ | 98-100% | Pydantic 스키마 (order.py 98%) |
| services/ | 79-100% | kis_order(92%), kis_price(80%), kis_transaction(93%), scheduler(79%) |
| services/backup_health, kis_health, reconciliation, price_snapshot | 100% | 완전 커버 |
| api/ routers | 25-100% | 대부분 통합 테스트 통과 |
| db/ | 75-100% | session.py 75% |
| main.py | 85% | lifespan, 예외 핸들러 |

### 6.3 강점

- KIS API 비동기 병렬 호출 + Redis 캐시 폴백으로 안정적 가격 조회
- KIS API 장애 감지: 전체 가격 조회 실패 시 `kis_status: "degraded"` 반환 + 프론트엔드 배너 표시
- KIS 잔고 조회 실패 시 `RuntimeError` raise로 명확한 에러 전파 (silent fail 방지)
- HttpOnly Cookie 인증으로 XSS 토큰 탈취 방지
- AES-256-GCM으로 KIS 자격증명 안전하게 저장
- 구조화 로깅 (structlog) + request_id 트레이싱
- 해외주식 USD 가격 표시 및 원화 환산 (환율 자동 적용)
- 보유종목 market_value_krw 기준 내림차순 정렬
- SSE 연결 하드닝: 사용자별 제한, 하트비트, 유휴 감지, 최대 연결 시간
- ruff lint 오류 0건 (코드 품질 유지)
- Commitlint 커밋 메시지 검증 자동화
- 표준화된 에러 응답 envelope (error.code, error.message, request_id)
- Graceful shutdown (SSE 연결 종료 시그널, 스케줄러 정지)
- Next.js proxy 컨벤션 마이그레이션 완료
- DB 백업 자동화 + health endpoint 통합
- TanStack Query 도입으로 캐시 일관성 확보 (대시보드 30s refetch, SSE queryClient 연동)
- 접근성 개선 (aria-label, touch targets, navigation aria-current)
- 데이터 무결성 헬스체크: price_snapshots 갭 감지, holdings 정합성, 고아 레코드 감지
- KIS API 시작 시 연결 테스트 (비가용 시 캐시 전용 모드)
- Sentry APM 통합 (백엔드 sentry-sdk + 프론트 @sentry/nextjs), DSN 환경변수화 완료
- MetricsMiddleware: 모든 요청에 X-Process-Time 헤더 + structlog process_time_ms 기록
- 파일 로깅: RotatingFileHandler (10MB x 5 rotation, JSON 포맷, 쓰기 불가 시 graceful degradation)
- Dozzle 컨테이너 로그 뷰어 Docker 서비스 추가
- 국내 주식 주문 버그 4건 수정: Decimal 타입 보존, 지정가 price 검증, SELL 보유수량 검증, KIS 에러 메시지 개선
- 인앱 알림 센터: notifications 테이블 + 벨 아이콘 + 미읽음 배지 + 읽음 처리
- 거래 메모 기능: transactions.memo 컬럼 + 인라인 편집 UI
- **[PERF-001]** DISTINCT ON 쿼리로 prev_close 조회 최적화 (14600→20행 DB 스캔)
- **[PERF-002/003]** fx-gain-loss Redis 캐시 추가 + 해외 티커 라우팅 수정
- **[PERF-004]** SSE 연결 상태 추적 useRef→useState 변경 (React Compiler lint 대응)
- **[PERF-005/TD-001]** Redis ConnectionPool 모듈 레벨 싱글턴으로 변경 (요청별 TCP 오버헤드 제거)
- **[PERF-006]** mutation onError 중복 핸들러 제거
- **[SEC-001]** Sentry before_send: KIS 자격증명(appkey, appsecret, authorization) 스크러빙
- **[SEC-002]** password max_length=128 제한 (bcrypt DoS 방지)
- **[SEC-004]** CSP 수정 (AlertDialog 등 접근성 개선)
- **[SEC-006]** TransactionMemoUpdate tags 최대 20개, 각 50자 제한
- **[TD-005]** cryptography 46.0.5 → 46.0.6 보안 패치
- **[UX-001/004/006/007]** AlertDialog 접근성, query key 정규화, 불필요한 재렌더링 제거
- 포트폴리오 이름 holding 응답에 포함 (dashboard 요약, analytics, journal 연동)
- 거래내역 컬럼 KIS 체결내역 컬럼과 통일 (portfolio detail 페이지)
- team-implement 멀티 에이전트 병렬 구현 시스템 (backend-worker + frontend-worker + infra-worker + implement-synthesizer)
- worker/auto-task 빌드 검증을 CI와 동일하게 맞춤 (React Compiler 린트 포함)
- 포트폴리오 순서 변경: display_order + 드래그 앤 드롭 (@dnd-kit)
- KIS 체결내역 조회: 국내(TTTC8001R) + 해외(TTTS3035R) 체결 내역 API
- Redis 장애 폴백: RedisCache 래퍼가 in-memory dict으로 자동 전환
- KIS 주식 매매: 국내/해외 매수/매도 주문 실행 + 주문 취소 + 미체결 조회
- 이중 주문 방지: Redis 락 (TTL 10초) + 레이트 리밋 (5회/분)
- 예수금 조회: 국내+해외 합산 (TTTC8434R + 해외 잔고), Redis 캐시 30초
- 계좌 유형별 TR_ID 분기: 일반/ISA/연금저축/IRP 자동 구분
- 주문 다이얼로그: 지정가/시장가 전환, 빠른 비율 버튼(10%/25%/50%/100%), 확인 스텝
- 미체결 주문 패널: 주문 취소 + 체결 감지 시 toast 알림
- Excel(xlsx) 내보내기: 보유종목 + 거래내역 시트 포함
- 보유종목 일괄등록 API: 최대 100건 일괄 등록/업데이트 (가중평균 합산)
- 투자 일지 전용 페이지 (/dashboard/journal)
- 거래내역 커서 기반 페이지네이션 (무한 스크롤)
- KIS API 중복 호출 제거 및 장 전 가격 캐시 워밍
- 테스트 일괄 실행 안정성 개선: 294 ERROR -> 0 ERROR (async DB session 격리 문제 해결)
- holdings 동기화 + 가격 캐시 워밍을 KST 08:00, 16:00 두 번 실행 (장 전/후 최신화)
- FX 환율 히스토리 API + 평일 KST 16:30 환율 스냅샷 자동 저장
- 해외주식 환차익/환차손 분리 분석: GET /analytics/fx-gain-loss (주가 수익 vs 환율 효과 분리)
- 원화 환산 총 자산 추이 스택 영역 차트: GET /analytics/krw-asset-history (국내+해외 KRW 환산)
- 투자 일지 월별/종목별 필터링 및 메모 키워드 검색
- 투자 일지 최근 30일 매수 회고 위젯
- 포트폴리오 비교 페이지 (/dashboard/compare)
- 디스크 모니터링 헬스 엔드포인트 (GET /health/disk)
- docker-compose.dev.yml: 로컬 인프라 전용 개발 환경 구성
- 스케줄러 해외 holdings 누락 수정: reconcile_holdings 내 fetch_overseas_account_holdings 호출 추가
- 연금저축/IRP 등 nxdy_excc_amt 미반영 계좌 예수금 계산 보완 (thdt_buy_amt 기반 직접 계산 폴백)
- 주문 실패 시 KIS 실제 오류 메시지 표시 (이전: '알 수 없는 오류', 이후: KIS msg1 그대로 노출)
- 매수 후 예수금 미갱신 수정: nxdy_excc_amt로 실질 잔액 반영 + 에러 시 상태 표시
- CI 최적화: docker-build·codeql 워크플로우를 main push 제외 PR 전용으로 변경
- GZipMiddleware 추가: minimum_size=1000 응답 압축으로 전송 크기 절감
- is_domestic() 유틸리티 추출: app/core/ticker.py로 중복 코드 5개 제거
- analytics.py fx-gain-loss/krw-asset-history 캐시 무효화 수정
- DB 인덱스 추가: transactions.ticker, price_snapshots(ticker, snapshot_date) 복합
- 포트폴리오/보유종목/주문 쓰기 엔드포인트에 레이트 리밋 추가 (60~30/분)
- CORS 명시적 메서드/헤더 지정으로 와일드카드 대체 (보안 강화)
- StockSearchDialog localStorage 파싱 타입 검증 강화
- Sentry ENVIRONMENT 환경변수화 (settings.ENVIRONMENT 사용)
- 비교 페이지 포트폴리오 2개 미만 시 빈 상태 표시
- 종목 상세 캔들스틱 데이터 로딩 중 ChartSkeleton 표시
- **[Sprint 8]** slowapi 레이트 리밋 추가: stocks(30/min), chart(30/min), alerts(30/min), watchlist(60/min)
- **[Sprint 8]** analytics.py 도메인별 분리: analytics_metrics.py + analytics_history.py + analytics_fx.py + analytics_utils.py 서비스
- **[Sprint 8]** analytics/page.tsx 섹션 컴포넌트 분리 (MetricsSection, MonthlyReturnsSection, SectorFxSection, HistorySection)
- **[Sprint 8]** 투자 일지 월별 빈 상태 개선 (월 필터 시 "이 달에는 거래 내역이 없습니다" + 거래 추가 링크)
- **[Sprint 8]** 포트폴리오 비교 페이지 기간 필터 항상 표시 (포트폴리오 선택 전에도 노출)
- **[Sprint 8]** kis_order.py 도메인별 분리: kis_domestic_order.py + kis_overseas_order.py + kis_order_query.py
- **[Sprint 8]** CVE 패치: pygments 2.19.2→2.20.0 (CVE-2026-4539), requests 2.32.5→2.33.0 (CVE-2026-25645)
- **[Sprint 8]** 의존성 업그레이드: fastapi 0.115→0.135.3, redis 6.x→7.4.0, sentry-sdk 2.x→2.57.0, sqlalchemy 2.0.x→2.0.49, ruff 0.11.x→0.15.9
- **[Sprint 8]** fx-gain-loss 현재가 조회 병렬화 (asyncio.gather, sequential Redis 호출 제거)
- **[Sprint 8]** analytics/fx-history currency_pair 입력 검증 (허용 목록: USDKRW/EURKRW/JPYKRW/CNYKRW)
- **[Sprint 9]** Starlette 0.52.1 → 1.0.0 업그레이드 (803 테스트 통과)
- **[Sprint 9]** pytest-asyncio 0.25.3 → 1.3.0 업그레이드
- **[Sprint 9]** analytics.py API 라우터 3분할 → analytics_metrics.py + analytics_history.py + analytics_fx.py (각 독립 APIRouter)
- **[Sprint 9]** portfolios.py API 라우터 분할 → portfolio_holdings.py + portfolio_transactions.py
- **[Sprint 9]** dashboard/page.tsx 603L → DashboardMetrics + PortfolioList 컴포넌트 분리
- **[Sprint 9]** analytics 섹션 컴포넌트 ErrorBoundary 래핑 (개별 섹션 실패 시 독립적 에러 표시)
- **[Sprint 10]** 주문 레이트 리밋 강화: POST /orders 30/min → 10/min
- **[Sprint 10]** 대시보드 요약 staleTime 60초 추가 (불필요한 refetch 감소)
- **[Sprint 10]** IndexSnapshot 모델 + index_snapshots 마이그레이션 추가
- **[Sprint 10]** kis_benchmark.py: KOSPI200 + S&P500 스냅샷 수집 서비스
- **[Sprint 10]** 스케줄러 Job 6 추가: settle_orders (장중 5분 주기)
- **[Sprint 10]** 스케줄러 Job 7 추가: collect_benchmark (KST 16:20)
- **[Sprint 10]** kis_order.py 추가 분할: kis_order_place.py (384L) + kis_order_cancel.py (103L) + kis_order_query.py 분리; kis_order.py thin shim으로 유지
- **[Sprint 10]** a11y 개선: HoldingsSection 수치 입력 inputMode="numeric"/"decimal" 추가
- **[Sprint 10]** 테스트 회귀 수정: 21개 실패 → 0 (신규 모듈 경로 픽스처 업데이트)

### 6.4 약점 및 개선 필요 사항

- 이메일 알림 미구현 (인앱 알림 센터는 완료, 이메일/푸시 채널 없음)
- 프론트엔드 테스트 커버리지 부족 (MSW 설정 완료, HoldingsTable 등 일부 컴포넌트 테스트 추가됨, 페이지 테스트 미착수)
- 벤치마크 비교 UI 미구현 (Sprint 10에서 index_snapshots 데이터 수집 기반 완료, 분석 페이지 차트 연동 미착수)
- invalidate_analytics_cache가 포트폴리오별 캐시 키를 무효화하지 않음 (TTL 1시간 만료 후 자동 갱신)

### 6.5 리스크

| 리스크 | 심각도 | 설명 |
|--------|--------|------|
| KIS API 의존성 | 중 | KIS API 장애 시 가격 조회 불가 (Redis 폴백 300초, 장 마감 후 24h). degraded 배너로 사용자에게 알림 |
| 단일 서버 | 중 | self-hosted 단일 서버, 서버 장애 시 전체 서비스 중단 |
| 단일 사용자 환경 | 저 | 현재 다중 사용자 동시 접속 부하 테스트 미실시 |

---

## 관련 문서

- [프로젝트 개요](overview.md) -- 기능 명세, API 엔드포인트 전체 목록
- [인프라](infrastructure.md) -- Docker, CI/CD, 배포, 암호화 아키텍처
- [API 레퍼런스](api-reference.md) -- 전체 엔드포인트 상세
- [프론트엔드 가이드](frontend-guide.md) -- 프론트엔드 구조
- [비용 관리](../reviews/cost_management.md) -- KIS API 최적화, Redis 캐싱 전략
