# THE WEALTH — Project Overview

## 프로젝트 소개

KIS(한국투자증권) OpenAPI 기반 개인 자산관리 대시보드.
한국 증시 컬러 컨벤션(상승=빨간색, 하락=파란색)을 따르며, 실시간 수익률 추적과 자동 계좌 동기화를 제공한다.

## 기술 스택

| 레이어 | 기술 | 비고 |
|--------|------|------|
| **프론트엔드** | Next.js 16 (App Router), React 19, TypeScript, Tailwind v4 | SSR + CSR 혼합 |
| **UI 라이브러리** | shadcn/ui (base-nova), TanStack Table v8, Recharts, Sonner | Dialog, Input, Card, Table, Skeleton, Toast |
| **상태관리** | Zustand | 인증 상태 (localStorage + cookie 이중 저장) |
| **HTTP** | Axios | JWT 자동 갱신 인터셉터 |
| **백엔드** | FastAPI (Python 3.9+), async/await | uvicorn, CORS localhost:3000 |
| **ORM** | SQLAlchemy 2.0 (async) + Alembic | asyncpg 드라이버 |
| **DB** | PostgreSQL | Homebrew 로컬 or Docker |
| **캐시** | Redis | KIS 토큰(24h), 종목 리스트(24h) |
| **인증** | JWT (access 30min + refresh 7d rotation) | passlib/bcrypt |
| **암호화** | AES-256-GCM | KIS 자격증명 저장용 |
| **스케줄러** | APScheduler | 1시간 간격 자동 동기화 |
| **Rate Limiting** | slowapi | 60 req/min |

## 아키텍처 개요

```
┌─────────────────┐     HTTP/JSON     ┌──────────────────┐
│   Next.js 16    │ ◄──────────────► │    FastAPI        │
│   (port 3000)   │                   │   (port 8000)    │
│                 │                   │                   │
│  App Router     │                   │  ┌─── api/ ────┐ │
│  Zustand Auth   │                   │  │ auth        │ │
│  shadcn/ui      │                   │  │ portfolios  │ │
│  Recharts       │                   │  │ dashboard   │ │
│  TanStack Table │                   │  │ stocks      │ │
│                 │                   │  │ users       │ │
│                 │                   │  │ sync        │ │
│                 │                   │  └─────────────┘ │
└─────────────────┘                   └──────┬───────────┘
                                             │
                              ┌──────────────┼──────────────┐
                              │              │              │
                         ┌────▼────┐   ┌─────▼────┐  ┌─────▼─────┐
                         │ Postgres │   │  Redis   │  │  KIS API  │
                         │ (users,  │   │ (tokens, │  │ (현재가,  │
                         │  holdings│   │  stocks) │  │  계좌잔고)│
                         │  etc.)   │   │          │  │           │
                         └─────────┘   └──────────┘  └───────────┘
```

## 디렉토리 구조

```
the-wealth/
├── frontend/                     # Next.js 16 App Router
│   └── src/
│       ├── app/                  # 페이지 (App Router)
│       │   ├── dashboard/        # 대시보드, 포트폴리오, 설정
│       │   ├── login/            # 로그인
│       │   └── register/         # 회원가입
│       ├── components/           # 공통 컴포넌트
│       ├── lib/                  # Axios, 유틸리티
│       └── store/                # Zustand (auth)
├── backend/                      # FastAPI
│   └── app/
│       ├── api/                  # 라우터 (6개)
│       ├── core/                 # config, security, encryption
│       ├── db/                   # SQLAlchemy session, base
│       ├── models/               # ORM 모델 (5개)
│       ├── schemas/              # Pydantic 스키마
│       └── services/             # 비즈니스 로직 (6개)
├── docs/
│   ├── analysis/                 # 프로젝트 분석 문서
│   └── plan/                     # 로드맵, 수동 작업
└── .claude/                      # Claude Code 설정
```

## API 엔드포인트 목록

### 인증 (`/auth`)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/auth/register` | 회원가입 |
| POST | `/auth/login` | 로그인 (access + refresh 토큰) |
| POST | `/auth/refresh` | 토큰 갱신 |

### 포트폴리오 (`/portfolios`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/portfolios` | 포트폴리오 목록 |
| POST | `/portfolios` | 포트폴리오 생성 |
| DELETE | `/portfolios/{id}` | 포트폴리오 삭제 |
| GET | `/portfolios/{id}/holdings` | 보유 종목 목록 |
| POST | `/portfolios/{id}/holdings` | 종목 추가 |
| PATCH | `/portfolios/holdings/{id}` | 종목 수정 |
| DELETE | `/portfolios/holdings/{id}` | 종목 삭제 |

### 대시보드 (`/dashboard`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/dashboard/summary` | 총 자산, 수익률, 자산 배분 |

### 종목 (`/stocks`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/stocks/search?q=` | 종목 검색 (KOSPI + KOSDAQ + ETF) |

### 사용자 (`/users`)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/users/kis-credentials` | KIS 자격증명 저장 |

### 동기화 (`/sync`)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/sync/{portfolio_id}` | KIS 계좌 동기화 |
| GET | `/sync/logs` | 동기화 이력 |

## DB 모델

| 테이블 | 주요 컬럼 | 비고 |
|--------|-----------|------|
| **users** | email, hashed_password, kis_app_key_enc, kis_app_secret_enc, kis_account_no | KIS 키는 AES-256 암호화 |
| **portfolios** | user_id, name, currency | 사용자별 다중 포트폴리오 |
| **holdings** | portfolio_id, ticker, name, quantity, avg_price | 보유 종목 (현재가는 DB 미저장) |
| **transactions** | portfolio_id, ticker, type, quantity, price, traded_at | 매매 이력 |
| **sync_logs** | user_id, portfolio_id, status, inserted, updated, deleted | 동기화 감사 로그 |

## 프론트엔드 페이지

| 경로 | 설명 |
|------|------|
| `/` | 랜딩 페이지 |
| `/login` | 로그인 |
| `/register` | 회원가입 |
| `/dashboard` | 메인 대시보드 (총 자산, 도넛 차트, 보유 종목 테이블) |
| `/dashboard/portfolios` | 포트폴리오 목록/생성/삭제 |
| `/dashboard/portfolios/[id]` | 포트폴리오 상세 (종목 CRUD) |
| `/dashboard/analytics` | 분석 (placeholder — 준비 중) |
| `/dashboard/settings` | KIS 자격증명, 수동 동기화, 동기화 이력 |

## 핵심 서비스 로직

| 서비스 | 역할 |
|--------|------|
| **kis_token.py** | KIS OAuth 토큰 발급/캐싱 (Redis 24h TTL) |
| **kis_price.py** | 국내/해외 현재가 조회 (`asyncio.gather` 병렬, Redis 캐시 폴백) |
| **kis_account.py** | KIS 계좌 잔고 조회 (TTTC8434R) |
| **reconciliation.py** | DB vs KIS 보유종목 비교 → INSERT/UPDATE/DELETE |
| **stock_search.py** | KRX KIND + Naver Finance ETF → Redis 캐싱 → 로컬 검색 |
| **scheduler.py** | APScheduler 1시간 간격 자동 동기화 |
