# The Wealth — 개인 자산관리 대시보드

한국투자증권(KIS) OpenAPI 기반의 실시간 자산관리 대시보드입니다. 포트폴리오 현황, 수익률 분석, 섹터 배분, 관심종목 등을 한눈에 파악할 수 있습니다.

## 주요 기능

- 포트폴리오 관리 (보유종목, 거래내역, CSV 내보내기)
- 실시간 현재가 조회 (SSE 스트리밍, 30초 주기)
- 수익률 분석 (일별/월별 수익률, 히트맵, 포트폴리오 히스토리)
- 섹터별 자산 배분 (도넛 차트)
- 캔들스틱 차트 (lightweight-charts)
- KIS 계좌 자동 동기화 (1시간 주기)
- 가격 알림 (목표가 상한/하한)
- 관심종목 관리
- Cmd+K 종목 검색

## 기술 스택

| 영역 | 기술 |
|------|------|
| **Frontend** | Next.js 16, React 19, TypeScript 5, Tailwind v4, shadcn/ui 4 |
| **Backend** | FastAPI 0.135, SQLAlchemy 2.0 (async), Pydantic 2.12 |
| **Database** | PostgreSQL 16, Redis 7 |
| **인프라** | Docker Compose, GitHub Actions CI/CD, Self-hosted deploy |
| **차트** | Recharts 3.8, lightweight-charts 5.1, TanStack Table 8 |
| **인증** | JWT (access + refresh rotation), bcrypt, AES-256-GCM |

## 프로젝트 구조

```
the-wealth/
├── docker-compose.yml          # PostgreSQL, Redis, Backend, Frontend
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI 엔트리포인트
│   │   ├── api/                # 라우터 (auth, portfolios, dashboard 등 12개)
│   │   ├── core/               # config, security, encryption, middleware
│   │   ├── db/                 # SQLAlchemy async session, base
│   │   ├── models/             # ORM 모델 (9 테이블)
│   │   ├── schemas/            # Pydantic 스키마
│   │   ├── services/           # KIS API, 스케줄러, 검색 등
│   │   └── data/               # 정적 데이터 (섹터 맵)
│   ├── tests/
│   ├── alembic/                # DB 마이그레이션
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js App Router 페이지
│   │   ├── components/         # UI 컴포넌트
│   │   ├── hooks/              # 커스텀 훅 (usePriceStream 등)
│   │   ├── lib/                # API 클라이언트, 유틸리티
│   │   ├── store/              # Zustand 상태 관리
│   │   └── types/              # TypeScript 타입 정의
│   ├── Dockerfile
│   └── package.json
├── .github/workflows/          # CI/CD (7 워크플로우)
└── docs/                       # 프로젝트 문서
```

## 로컬 개발 환경 설정

### 사전 요구사항

- Node.js 22+
- Python 3.12+
- Docker & Docker Compose
- PostgreSQL 16 / Redis 7 (또는 Docker로 실행)

### 1. 인프라 서비스 실행 (Docker)

```bash
# PostgreSQL + Redis만 실행
docker compose up postgres redis -d
```

### 2. 백엔드 설정

```bash
cd backend

# 환경변수 설정
cp .env.example .env
# .env 파일을 열어 아래 값들을 수정:
#   JWT_SECRET_KEY      → openssl rand -hex 32
#   ENCRYPTION_MASTER_KEY → openssl rand -hex 32

# 가상환경 생성 및 의존성 설치
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# DB 마이그레이션
alembic upgrade head

# 개발 서버 실행 (http://localhost:8000)
uvicorn app.main:app --reload
```

### 3. 프론트엔드 설정

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행 (http://localhost:3000)
npm run dev
```

### 4. Docker Compose 전체 실행 (선택)

```bash
# 4개 서비스 모두 빌드 및 실행
docker compose up --build -d
```

## 환경변수

| 변수 | 설명 | 예시 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 연결 문자열 | `postgresql+asyncpg://postgres:postgres@localhost:5432/the_wealth` |
| `JWT_SECRET_KEY` | JWT 서명 키 (32바이트 hex) | `openssl rand -hex 32` |
| `JWT_ALGORITHM` | JWT 알고리즘 | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access Token 만료 시간 | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh Token 만료 시간 | `7` |
| `ENCRYPTION_MASTER_KEY` | AES-256 마스터 키 (64자 hex) | `openssl rand -hex 32` |
| `REDIS_URL` | Redis 연결 문자열 | `redis://localhost:6379` |
| `CORS_ORIGINS` | 허용 Origin (쉼표 구분) | `http://localhost:3000` |
| `KIS_BASE_URL` | 한국투자증권 API URL | `https://openapi.koreainvestment.com:9443` |

## 개발 명령어

```bash
# Backend
source backend/venv/bin/activate
pytest --cov=app --cov-report=term-missing   # 테스트 + 커버리지
ruff check .                                  # 린트
black .                                       # 포맷팅

# Frontend
cd frontend
npm run lint                                  # ESLint
npm run build                                 # 프로덕션 빌드
npx vitest run                                # 테스트
```

## 문서

- [프로젝트 개요](docs/project_overview.md) — 기능 명세, 페이지 구조
- [프로젝트 분석](docs/project_analysis.md) — 아키텍처 분석, DB 스키마
- [인프라](docs/infrastructure.md) — 배포, Docker, CI/CD, 보안
- [비용 관리](docs/cost_management.md) — KIS API 최적화, Redis 캐싱 전략

## 라이선스

Private repository.
