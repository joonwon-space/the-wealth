# 프로젝트 분석

## 1. 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        Client (Browser)                      │
│   Next.js 16 App Router + React 19 + Tailwind v4 + shadcn   │
│   ├── SSR (Server Components)                                │
│   ├── Zustand (auth store)                                   │
│   ├── Axios (JWT interceptor + auto refresh)                 │
│   └── SSE (usePriceStream hook)                              │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/SSE (port 3000 → 8000)
┌────────────────────▼────────────────────────────────────────┐
│                     FastAPI Backend                           │
│   ├── 42 API endpoints (12 routers)                          │
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
| Next.js | 16.1.7 | App Router, SSR, 미들웨어 |
| React | 19.2.4 | UI 렌더링 |
| TypeScript | 5 | 타입 안전성 |
| Tailwind CSS | v4 | 유틸리티 기반 스타일링 |
| shadcn/ui | 4.0.8 | UI 컴포넌트 (base-nova/neutral) |
| TanStack Table | 8.21.3 | 보유종목 데이터 테이블 |
| Recharts | 3.8.0 | 도넛 차트, 히트맵 |
| lightweight-charts | 5.1.0 | 캔들스틱 차트 |
| Axios | 1.13.6 | HTTP 클라이언트 |
| Zustand | 5.0.12 | 클라이언트 상태 관리 |
| next-themes | 0.4.6 | 다크/라이트 테마 |
| Vitest | 4.1.0 | 단위 테스트 |
| Playwright | 1.58.2 | E2E 테스트 |

### 2.2 디렉토리 구조

```
frontend/src/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # 루트 레이아웃
│   ├── login/                    # 로그인 페이지
│   ├── register/                 # 회원가입 페이지
│   └── dashboard/                # 대시보드 (인증 필요)
│       ├── page.tsx              # 메인 대시보드
│       ├── analytics/            # 분석 페이지
│       ├── chart/                # 차트 페이지
│       ├── alerts/               # 알림 관리
│       └── settings/             # 설정
├── components/
│   ├── AllocationDonut.tsx       # 자산 배분 도넛 차트
│   ├── BottomNav.tsx             # 모바일 하단 네비게이션
│   ├── CandlestickChart.tsx      # 캔들스틱 차트 (lightweight-charts)
│   ├── DayChangeBadge.tsx        # 일간 변동률 뱃지 (상승=빨강/하락=파랑)
│   ├── HoldingsTable.tsx         # 보유종목 테이블 (TanStack Table)
│   ├── MonthlyHeatmap.tsx        # 월별 수익률 히트맵
│   ├── PnLBadge.tsx              # 수익/손실 뱃지 (상승=빨강/하락=파랑)
│   ├── PortfolioHistoryChart.tsx  # 포트폴리오 가치 추이
│   ├── SectorAllocationChart.tsx  # 섹터별 배분 차트
│   ├── Sidebar.tsx               # 데스크톱 사이드바
│   ├── StockSearchDialog.tsx     # Cmd+K 종목 검색
│   ├── WatchlistSection.tsx      # 관심종목 섹션
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
├── api/                       # 12개 API 라우터
│   ├── auth.py                # 인증 (register, login, refresh, change-password)
│   ├── portfolios.py          # 포트폴리오/보유종목/거래내역 CRUD
│   ├── portfolio_export.py    # CSV 내보내기
│   ├── dashboard.py           # 대시보드 요약
│   ├── analytics.py           # 수익률 분석, 월별 수익률, 섹터 배분
│   ├── alerts.py              # 가격 알림
│   ├── stocks.py              # 종목 검색/상세
│   ├── sync.py                # KIS 계좌 동기화
│   ├── users.py               # KIS 계좌 관리
│   ├── chart.py               # 차트 데이터
│   ├── prices.py              # 가격 히스토리, SSE 스트림
│   └── watchlist.py           # 관심종목
├── core/
│   ├── config.py              # Pydantic Settings (환경변수)
│   ├── security.py            # JWT 생성/검증, bcrypt, refresh token rotation
│   ├── encryption.py          # AES-256-GCM 암호화/복호화
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
│   └── stock_search.py        # KRX 종목 검색
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

slowapi 기반 IP별 레이트 리미팅: **60 요청/분** (기본값)

---

## 관련 문서

- [프로젝트 개요](project_overview.md) — 기능 명세, API 엔드포인트 전체 목록
- [인프라](infrastructure.md) — Docker, CI/CD, 배포, 암호화 아키텍처
- [비용 관리](cost_management.md) — KIS API 최적화, Redis 캐싱 전략
