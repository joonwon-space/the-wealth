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
│   ├── 52 API endpoints (14 routers)                          │
│   ├── JWT auth + IDOR prevention                             │
│   ├── slowapi rate limiter (60/min)                          │
│   ├── SecurityHeadersMiddleware                              │
│   ├── APScheduler (sync 1h, snapshot KST 16:10)             │
│   └── structlog (request_id tracing)                         │
└──┬──────────────┬──────────────┬────────────────────────────┘
   │              │              │
   ▼              ▼              ▼
┌──────┐    ┌──────────┐    ┌──────────────────┐
│ PG16 │    │ Redis 7  │    │ KIS OpenAPI      │
│      │    │          │    │ (한국투자증권)     │
│ 9 TB │    │ JWT JTI  │    │ ├─ oauth2/tokenP │
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
│       ├── page.tsx              # 메인 대시보드
│       ├── error.tsx             # 대시보드 에러 바운더리
│       ├── layout.tsx            # 대시보드 레이아웃 (사이드바+하단 네비)
│       ├── analytics/            # 분석 페이지
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
│   ├── WatchlistSection.tsx      # 관심종목 섹션
│   ├── QueryProvider.tsx         # TanStack Query 프로바이더 (QueryClientProvider)
│   ├── PageError.tsx             # 페이지 에러 표시 컴포넌트
│   ├── TableSkeleton.tsx         # 테이블 로딩 스켈레톤
│   └── ui/                       # shadcn/ui 컴포넌트
├── hooks/
│   └── usePriceStream.ts         # SSE 실시간 가격 스트리밍 훅
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
| cryptography | 46.0.5 | AES-256-GCM 암호화 |
| redis | 7.3.0 | async Redis 클라이언트 |
| httpx | 0.28.1 | async HTTP (KIS API) |
| APScheduler | 3.11.2 | 백그라운드 스케줄러 |
| slowapi | 0.1.9 | 레이트 리미팅 |
| structlog | 25.4.0 | 구조화 로깅 |

### 3.2 디렉토리 구조

```
backend/app/
├── main.py                    # FastAPI app, CORS, 미들웨어, 라우터 등록
├── api/                       # 14개 API 라우터 + 공통 의존성
│   ├── deps.py                # get_current_user, get_current_user_sse 인증 의존성
│   ├── auth.py                # 인증 (register, login, refresh, change-password, logout)
│   ├── portfolios.py          # 포트폴리오/보유종목/거래내역 CRUD
│   ├── portfolio_export.py    # CSV 내보내기 (보유종목 + 거래내역)
│   ├── dashboard.py           # 대시보드 요약
│   ├── analytics.py           # 수익률 분석, 월별 수익률, 섹터 배분
│   ├── alerts.py              # 가격 알림
│   ├── stocks.py              # 종목 검색/상세
│   ├── sync.py                # KIS 계좌 동기화
│   ├── users.py               # KIS 계좌 관리
│   ├── chart.py               # 차트 데이터
│   ├── prices.py              # 가격 히스토리, SSE 스트림
│   ├── watchlist.py           # 관심종목
│   ├── health.py              # 헬스체크 (DB, Redis, KIS, backup 상태)
│   └── internal.py            # 내부 API (백업 상태 기록)
├── core/
│   ├── config.py              # Pydantic Settings (환경변수)
│   ├── security.py            # JWT 생성/검증, bcrypt, refresh token rotation
│   ├── encryption.py          # AES-256-GCM 암호화/복호화
│   ├── limiter.py             # slowapi 레이트 리미터 인스턴스
│   ├── middleware.py          # SecurityHeadersMiddleware
│   └── logging.py             # structlog 설정, request_id
├── db/
│   ├── base.py                # SQLAlchemy Base
│   └── session.py             # AsyncSession 팩토리
├── models/                    # SQLAlchemy ORM 모델 (9 테이블)
│   ├── user.py
│   ├── portfolio.py
│   ├── holding.py
│   ├── transaction.py
│   ├── kis_account.py
│   ├── alert.py
│   ├── watchlist.py
│   ├── price_snapshot.py
│   └── sync_log.py
├── schemas/                   # Pydantic 검증 스키마
│   ├── auth.py
│   ├── portfolio.py
│   ├── dashboard.py
│   ├── analytics.py
│   └── user.py
├── services/                  # 비즈니스 로직
│   ├── kis_token.py           # KIS OAuth2 토큰 관리
│   ├── kis_price.py           # 현재가/OHLCV 조회 (병렬)
│   ├── kis_account.py         # KIS 잔고 조회
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
┌─────────────────────────────────────────────┐
│ APScheduler (AsyncIOScheduler)               │
│                                              │
│ Job 1: kis_sync                              │
│   trigger: interval(hours=1)                 │
│   action: KIS 자격증명 있는 모든 사용자의      │
│           첫 번째 포트폴리오 잔고 동기화        │
│   결과: sync_logs 테이블에 기록               │
│                                              │
│ Job 2: daily_close_snapshot                  │
│   trigger: cron(mon-fri, 07:10 UTC)          │
│            = KST 16:10 (장 마감 후)           │
│   action: 전체 보유종목 OHLCV 조회            │
│           → price_snapshots 테이블 저장        │
│   폴백: OHLCV 실패 시 현재가로 close 저장     │
└─────────────────────────────────────────────┘
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
  ▼ Request ID Middleware
  │   X-Request-ID: uuid4 (structlog 연동)
  │
  ▼ Rate Limiter (slowapi)
  │   default: 60/minute per IP
  │
  ▼ Router → Handler
```

---

## 4. 데이터베이스 스키마 (9 테이블)

### 4.1 ERD 다이어그램

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   users     │     │  portfolios  │     │   holdings   │
├─────────────┤     ├──────────────┤     ├──────────────┤
│ id (PK)     │◄──┐ │ id (PK)      │◄──┐ │ id (PK)      │
│ email (UQ)  │   │ │ user_id (FK) │   │ │ portfolio_id │
│ hashed_pwd  │   │ │ name         │   │ │ ticker       │
│ kis_app_key │   │ │ currency     │   │ │ name         │
│ kis_app_sec │   │ │ kis_account  │   │ │ quantity     │
│ kis_acct_no │   │ │  _id (FK,UQ) │   │ │ avg_price    │
│ kis_prdt_cd │   │ │ created_at   │   │ │ created_at   │
│ created_at  │   │ └──────────────┘   │ └──────────────┘
└─────────────┘   │         │          │
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
      │  │  _enc        │    │ created_at   │
      │  │ created_at   │    └──────────────┘
      │  │ UQ(user,acct,│
      │  │    prdt)     │
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
```

### 4.2 테이블 상세

#### users
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | 사용자 ID |
| email | String | UNIQUE, NOT NULL | 이메일 (로그인 ID) |
| hashed_password | String | NOT NULL | bcrypt 해시 비밀번호 |
| kis_app_key_enc | String | nullable | KIS App Key (AES-256 암호화) |
| kis_app_secret_enc | String | nullable | KIS App Secret (AES-256 암호화) |
| kis_account_no | String | nullable | KIS 계좌번호 |
| kis_acnt_prdt_cd | String | nullable | KIS 계좌 상품코드 |
| created_at | DateTime | default=now | 생성일시 |

#### portfolios
| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| id | Integer | PK, auto | 포트폴리오 ID |
| user_id | Integer | FK→users CASCADE, NOT NULL | 소유자 |
| name | String | NOT NULL | 포트폴리오 이름 |
| currency | String | default="KRW" | 통화 |
| kis_account_id | Integer | FK→kis_accounts SET NULL, UNIQUE | 연결된 KIS 계좌 |
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
| 기타 | 60/min (기본값) |

---

## 6. 프로젝트 현황 분석 (2026-03-21)

### 6.1 완성도

| 영역 | 상태 | 비고 |
|------|------|------|
| 인증 (JWT + HttpOnly Cookie) | 완료 | Refresh token rotation, IDOR 방지, 로그아웃 |
| 포트폴리오 CRUD | 완료 | CSV export (보유종목 + 거래내역), 거래내역 soft delete 포함 |
| 대시보드 | 완료 | SSE 실시간, 30초 폴링, 자산 배분 도넛, 해외주식 USD 가격 표시, KIS 장애 감지 배너 |
| KIS API 연동 | 완료 | 국내/해외 현재가, OHLCV, 잔고 동기화, 장애 감지 (kis_status: degraded) |
| 분석 페이지 | 완료 | 월별 히트맵, 섹터 배분, 포트폴리오 히스토리 |
| 종목 검색 | 완료 | Cmd+K, 초성 검색, KRX+NYSE+NASDAQ |
| 관심종목 | 완료 | 마켓별 구분 |
| 알림 | 완료 | 가격 알림 CRUD + SSE 조건 체크 (푸시 알림 미구현) |
| 자동 동기화 | 완료 | APScheduler 1시간 주기 + 일일 스냅샷 |
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
| 모니터링 | 미착수 | Sentry + 로그 수집 예정 |

### 6.2 테스트 커버리지 (백엔드)

전체: **92%** (577 tests passed, 2 failed)

| 모듈 | 커버리지 | 비고 |
|------|---------|------|
| core/ (security, encryption, middleware, limiter) | 95-100% | 우수 |
| models/ | 100% | ORM 모델 |
| schemas/ | 100% | Pydantic 스키마 |
| services/ | 93-100% | backup_health(100%), kis_health(100%), kis_price(94%) |
| api/ routers | 83-100% | 대부분 90%+ |
| db/ | 75-100% | session.py 75% |
| main.py | 85% | lifespan, 예외 핸들러 |

참고: 2개 테스트 실패 (`test_overseas_support.py`) -- `kis_account.py`가 빈 배열 대신 `RuntimeError`를 raise하도록 변경됨에 따른 기대값 불일치

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
- 테스트 커버리지 92% (577 tests) -- ruff lint 오류 0건
- Commitlint 커밋 메시지 검증 자동화
- 표준화된 에러 응답 envelope (error.code, error.message, request_id)
- Graceful shutdown (SSE 연결 종료 시그널, 스케줄러 정지)
- Next.js proxy 컨벤션 마이그레이션 완료
- DB 백업 자동화 + health endpoint 통합
- TanStack Query 도입으로 캐시 일관성 확보 (대시보드 30s refetch, SSE queryClient 연동)
- 접근성 개선 (aria-label, touch targets, navigation aria-current)
- 데이터 무결성 헬스체크: price_snapshots 갭 감지, holdings 정합성, 고아 레코드 감지
- KIS API 시작 시 연결 테스트 (비가용 시 캐시 전용 모드)

### 6.4 약점 및 개선 필요 사항

- 모니터링/APM 미도입 (structlog만 운용)
- 알림 전송 채널 미구현 (SSE 조건 체크만 존재, 실제 푸시/이메일 없음)
- 2개 테스트 실패: `test_overseas_support.py`에서 `kis_account.py` RuntimeError 변경 미반영
- 프론트엔드 테스트 커버리지 최소 (백엔드 92% 대비)

### 6.5 리스크

| 리스크 | 심각도 | 설명 |
|--------|--------|------|
| KIS API 의존성 | 중 | KIS API 장애 시 가격 조회 불가 (Redis 폴백 300초, 장 마감 후 24h). degraded 배너로 사용자에게 알림 |
| 단일 서버 | 중 | self-hosted 단일 서버, 서버 장애 시 전체 서비스 중단 |
| 단일 사용자 환경 | 저 | 현재 다중 사용자 동시 접속 부하 테스트 미실시 |
| 테스트 실패 | 저 | `test_overseas_support.py` 2건 실패 (RuntimeError 변경 미반영) |

---

## 관련 문서

- [프로젝트 개요](overview.md) -- 기능 명세, API 엔드포인트 전체 목록
- [인프라](infrastructure.md) -- Docker, CI/CD, 배포, 암호화 아키텍처
- [API 레퍼런스](api-reference.md) -- 전체 엔드포인트 상세
- [프론트엔드 가이드](frontend-guide.md) -- 프론트엔드 구조
- [비용 관리](../reviews/cost_management.md) -- KIS API 최적화, Redis 캐싱 전략
