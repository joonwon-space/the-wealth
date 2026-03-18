# 인프라

## 1. 배포 아키텍처

```
┌───────────────────────────────────────────────────────┐
│                  Self-hosted Server                    │
│                   (joonwon.dev)                        │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │            Docker Compose (4 services)           │  │
│  │                                                  │  │
│  │  ┌────────────┐  ┌────────────┐                 │  │
│  │  │ frontend   │  │  backend   │                 │  │
│  │  │ :3000      │  │  :8000     │                 │  │
│  │  │ node:20    │  │  python3.12│                 │  │
│  │  │ standalone │  │  uvicorn   │                 │  │
│  │  └────────────┘  └─────┬──────┘                 │  │
│  │                        │                         │  │
│  │         ┌──────────────┼──────────────┐         │  │
│  │         │              │              │         │  │
│  │  ┌──────▼─────┐  ┌────▼──────┐       │         │  │
│  │  │ postgres   │  │  redis    │       │         │  │
│  │  │ :5432      │  │  :6379    │       │         │  │
│  │  │ 16-alpine  │  │  7-alpine │       │         │  │
│  │  │ volume:    │  │  volume:  │       │         │  │
│  │  │ pg_data    │  │  redis_dat│       │         │  │
│  │  └────────────┘  └───────────┘       │         │  │
│  │                                      │         │  │
│  │                               ┌──────▼──────┐  │  │
│  │                               │ KIS OpenAPI │  │  │
│  │                               │ (외부)       │  │  │
│  │                               └─────────────┘  │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  GitHub Actions Runner (self-hosted, deploy label)     │
└───────────────────────────────────────────────────────┘
```

배포 URL:
- **프론트엔드**: `https://joonwon.dev` (port 3000)
- **백엔드 API**: `https://api.joonwon.dev` (port 8000)

---

## 2. Docker 멀티 스테이지 빌드

### 2.1 백엔드 Dockerfile

3단계가 아닌 **2단계** 빌드로 이미지 크기를 최소화:

```
Stage 1: builder (python:3.12-slim)
  ├── gcc, libpq-dev 설치 (빌드 의존성)
  ├── venv 생성 → /venv
  └── pip install -r requirements.txt

Stage 2: runner (python:3.12-slim)
  ├── curl, libpq5만 설치 (런타임 최소 의존성)
  ├── /venv 복사 (builder에서)
  ├── 앱 코드 복사
  ├── EXPOSE 8000
  └── ENTRYPOINT: entrypoint.sh
```

**entrypoint.sh** 실행 순서:
1. `alembic upgrade head` — DB 마이그레이션 자동 실행
2. `uvicorn app.main:app --host 0.0.0.0 --port 8000` — 서버 시작

최적화 포인트:
- `PYTHONDONTWRITEBYTECODE=1` — `.pyc` 파일 생성 방지
- `PYTHONUNBUFFERED=1` — 로그 즉시 출력
- gcc/libpq-dev는 builder에서만 사용, runner에는 포함되지 않음

### 2.2 프론트엔드 Dockerfile

**3단계** 빌드:

```
Stage 1: deps (node:20-alpine)
  ├── package.json + package-lock.json 복사
  └── npm ci (의존성 설치)

Stage 2: builder (node:20-alpine)
  ├── node_modules 복사 (deps에서)
  ├── 소스 코드 복사
  ├── NEXT_PUBLIC_API_URL build arg 주입
  └── npm run build

Stage 3: runner (node:20-alpine)
  ├── NODE_ENV=production
  ├── .next/standalone 복사 (최소 서버)
  ├── .next/static 복사 (정적 에셋)
  ├── public/ 복사
  ├── EXPOSE 3000
  └── CMD: node server.js
```

최적화 포인트:
- Next.js `standalone` 출력 모드: node_modules 없이 `server.js` 단독 실행
- deps 스테이지 분리로 `package.json` 변경 시에만 npm ci 재실행
- Build arg로 API URL을 빌드 타임에 주입

### 2.3 Docker Compose

```yaml
# docker-compose.yml 구성
services:
  postgres:    # postgres:16-alpine, port 5432, volume: postgres_data
  redis:       # redis:7-alpine, port 6379, volume: redis_data
  backend:     # ./backend Dockerfile, port 8000
  frontend:    # ./frontend Dockerfile, port 3000
```

서비스 의존성 체인:
```
postgres (healthcheck: pg_isready) ─┐
                                     ├─► backend (healthcheck: curl /health) ─► frontend
redis (healthcheck: redis-cli ping) ─┘
```

- `depends_on.condition: service_healthy` — 헬스체크 통과 후 다음 서비스 시작
- Backend 헬스체크: `curl -f http://localhost:8000/health`, 10초 간격, start_period 15초

---

## 3. CI/CD 파이프라인

### 3.1 워크플로우 전체 구성 (7개)

```
.github/workflows/
├── backend.yml               # 백엔드 CI (lint + test)
├── frontend.yml              # 프론트엔드 CI (lint + typecheck + test + build)
├── deploy.yml                # 배포 (self-hosted runner)
├── docker-build.yml          # Docker 빌드 검증
├── codeql.yml                # CodeQL 보안 분석
├── e2e.yml                   # E2E 테스트
└── dependabot-auto-merge.yml # Dependabot PR 자동 머지
```

### 3.2 Backend CI (`backend.yml`)

```
트리거: push/PR → backend/** 변경 시

┌─────────────────────────────────────┐
│ ubuntu-latest                        │
│ Services: postgres:16, redis:7       │
│                                      │
│ 1. Python 3.12 설치 (pip cache)      │
│ 2. pip install -r requirements.txt   │
│ 3. ruff check . (린트)              │
│ 4. pytest -v --cov=app (테스트)      │
│    ├── TEST_DATABASE_URL: asyncpg    │
│    ├── JWT_SECRET_KEY: ci-test-*     │
│    └── ENCRYPTION_MASTER_KEY: test   │
│ 5. Codecov 업로드 (coverage.xml)     │
└─────────────────────────────────────┘
```

### 3.3 Frontend CI (`frontend.yml`)

```
트리거: push/PR → frontend/** 변경 시

┌─────────────────────────────────────┐
│ ubuntu-latest                        │
│                                      │
│ 1. Node.js 22 설치 (npm cache)      │
│ 2. npm ci                            │
│ 3. npm run lint (ESLint)             │
│ 4. npx tsc --noEmit (타입 체크)      │
│ 5. npx vitest run (단위 테스트)      │
│ 6. npm run build (빌드 검증)         │
└─────────────────────────────────────┘
```

### 3.4 Deploy (`deploy.yml`)

```
트리거: push → main 브랜치

┌────────────────────────────────────────┐
│ self-hosted runner (deploy label)       │
│                                         │
│ 1. actions/checkout                     │
│ 2. backend/.env 시크릿 파일 생성         │
│ 3. macOS Keychain 잠금 해제             │
│ 4. docker compose build --parallel      │
│ 5. docker compose up -d --remove-orphans│
│ 6. 헬스체크 대기                         │
│    ├── Backend: /health (최대 60초)      │
│    └── Frontend: / (최대 30초)           │
│ 7. docker image prune -f (정리)         │
└────────────────────────────────────────┘
```

### 3.5 보안 & 자동화

- **CodeQL**: GitHub의 코드 보안 분석 자동 실행
- **Dependabot**: 의존성 업데이트 PR 자동 생성 + 조건부 자동 머지

---

## 4. PostgreSQL 연결 아키텍처

### 4.1 연결 구성

```
Backend (FastAPI)
  │
  ▼ SQLAlchemy 2.0 (async)
  │
  ▼ asyncpg 드라이버
  │
  ▼ PostgreSQL 16
```

- **연결 문자열**: `postgresql+asyncpg://postgres:postgres@{host}:5432/the_wealth`
- **로컬**: `localhost:5432`
- **Docker**: `postgres:5432` (서비스명 기반 DNS)
- **세션 관리**: `AsyncSessionLocal` 팩토리 → 요청별 세션 생성/해제

### 4.2 마이그레이션 (Alembic)

```bash
# 마이그레이션 생성
alembic revision --autogenerate -m "description"

# 마이그레이션 적용
alembic upgrade head

# 배포 시: entrypoint.sh에서 자동 실행
```

- 자동 마이그레이션 감지: SQLAlchemy 모델 변경 → Alembic이 diff 생성
- 배포 시 `entrypoint.sh`에서 `alembic upgrade head` 자동 실행

---

## 5. JWT 인증 인프라

### 5.1 토큰 플로우

```
┌─────────┐     POST /auth/login      ┌──────────┐
│ Client  │ ──────────────────────────► │ Backend  │
│         │ ◄────────────────────────── │          │
│         │  { access_token (30min),    │          │
│         │    refresh_token (7d) }     │          │
└────┬────┘                            └────┬─────┘
     │                                      │
     │  매 요청: Authorization: Bearer {at}  │
     │ ────────────────────────────────────► │
     │                                      │
     │  Access Token 만료 (30분 후)          │
     │                                      │
     │  POST /auth/refresh                  │
     │  { refresh_token }                   │
     │ ────────────────────────────────────► │
     │                                      │ Redis: JTI 확인 + 소비
     │  { new_access_token,                 │ Redis: 새 JTI 저장
     │    new_refresh_token }               │
     │ ◄──────────────────────────────────── │
```

### 5.2 Refresh Token Rotation

```
1. 클라이언트가 refresh_token 전송
2. JWT 디코딩 → { sub: user_id, jti: uuid4, type: "refresh" }
3. Redis 조회: refresh_jti:{jti} → user_id
4. 존재하면 → Redis에서 삭제 (1회성 소비)
5. 새 access_token + 새 refresh_token (새 jti) 발급
6. 새 jti를 Redis에 저장 (TTL: 7일)
```

보안 특성:
- **1회성 JTI**: 한 번 사용된 refresh token은 재사용 불가
- **탈취 감지**: 이미 소비된 JTI로 재시도 시 → None 반환 → 401
- **비밀번호 변경 시**: `revoke_all_refresh_tokens_for_user()`로 모든 토큰 무효화

### 5.3 Redis 키 패턴

| 키 패턴 | 값 | TTL | 용도 |
|---------|------|-----|------|
| `refresh_jti:{uuid}` | user_id (문자열) | 7일 | Refresh token JTI 저장 |

### 5.4 프론트엔드 연동

```
Zustand auth store
  ├── accessToken → localStorage + cookie (dual write)
  ├── refreshToken → localStorage
  └── isAuthenticated → boolean

Next.js Edge Middleware
  └── cookie에서 auth 토큰 확인 → 미인증 시 /login 리다이렉트

Axios Interceptor
  ├── Request: Authorization 헤더 자동 설정
  └── Response 401: refresh → retry (자동 토큰 갱신)
```

---

## 6. AES-256-GCM 암호화 아키텍처

### 6.1 목적

KIS OpenAPI 자격증명(App Key, App Secret)을 데이터베이스에 안전하게 저장하기 위한 대칭 암호화.

### 6.2 암호화 흐름

```
┌──────────────────────────────────────────────────┐
│ 암호화 (encrypt)                                  │
│                                                   │
│ 입력: plaintext (KIS App Key/Secret)              │
│                                                   │
│ 1. ENCRYPTION_MASTER_KEY (64자 hex) → 32바이트    │
│    → AES-256 키                                   │
│                                                   │
│ 2. os.urandom(12) → 12바이트 nonce 생성           │
│                                                   │
│ 3. AESGCM.encrypt(nonce, plaintext, None)         │
│    → ciphertext + tag (16바이트 인증 태그 포함)     │
│                                                   │
│ 4. base64(nonce[12] + ciphertext + tag[16])       │
│    → DB 저장용 문자열                              │
│                                                   │
│ 출력: base64 인코딩된 암호문                       │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ 복호화 (decrypt)                                  │
│                                                   │
│ 입력: base64 암호문                               │
│                                                   │
│ 1. base64 디코딩 → raw bytes                      │
│ 2. raw[:12] → nonce                               │
│ 3. raw[12:] → ciphertext + tag                    │
│ 4. AESGCM.decrypt(nonce, ciphertext+tag, None)   │
│    → 무결성 검증 (tag) + 복호화                    │
│                                                   │
│ 출력: plaintext (원래 App Key/Secret)              │
└──────────────────────────────────────────────────┘
```

### 6.3 보안 특성

| 특성 | 설명 |
|------|------|
| **알고리즘** | AES-256-GCM (Galois/Counter Mode) |
| **키 길이** | 256비트 (32바이트, 64자 hex 문자열) |
| **Nonce** | 12바이트 랜덤 (매 암호화마다 새로 생성) |
| **인증 태그** | 16바이트 (데이터 무결성 보장) |
| **키 소스** | `ENCRYPTION_MASTER_KEY` 환경변수 (코드에 포함하지 않음) |
| **저장 형식** | `base64(nonce + ciphertext + tag)` |

### 6.4 적용 테이블/컬럼

| 테이블 | 암호화 컬럼 | 내용 |
|--------|-----------|------|
| `users` | `kis_app_key_enc` | 레거시 KIS App Key |
| `users` | `kis_app_secret_enc` | 레거시 KIS App Secret |
| `kis_accounts` | `app_key_enc` | KIS App Key |
| `kis_accounts` | `app_secret_enc` | KIS App Secret |

### 6.5 마스터 키 관리

```bash
# 키 생성
openssl rand -hex 32
# → 64자 hex 문자열 (예: a1b2c3d4...64자)

# .env 설정
ENCRYPTION_MASTER_KEY=a1b2c3d4e5f6...

# 검증: 64자가 아니면 시작 시 ValueError 발생
# "ENCRYPTION_MASTER_KEY must be a 64-char hex string (32 bytes)"
```

---

## 7. 보안 헤더 미들웨어

`SecurityHeadersMiddleware`가 모든 HTTP 응답에 자동 추가:

```
X-Content-Type-Options: nosniff          # MIME 스니핑 방지
X-Frame-Options: DENY                    # 클릭재킹 방지
Referrer-Policy: strict-origin-when-cross-origin  # Referer 정보 제한
Permissions-Policy: camera=(), microphone=(), geolocation=()  # 브라우저 기능 제한
X-XSS-Protection: 1; mode=block          # XSS 필터 활성화
```

---

## 8. 레이트 리미팅

slowapi 기반 IP별 레이트 리미팅:

| 설정 | 값 |
|------|------|
| 기본 제한 | 60 요청/분 (IP 기준) |
| 키 함수 | `get_remote_address` |
| 초과 시 | `429 Too Many Requests` |

---

## 9. 로깅 & 모니터링

### structlog 구조화 로깅

- 모든 요청에 `X-Request-ID` (UUID4) 자동 부여
- 로그에 request_id 포함으로 요청 추적 가능
- 응답 헤더에 `X-Request-ID` 반환

### 헬스체크

```
GET /health → { "status": "ok" }
```

Docker Compose 헬스체크:
- PostgreSQL: `pg_isready -U postgres` (5초 간격)
- Redis: `redis-cli ping` (5초 간격)
- Backend: `curl -f http://localhost:8000/health` (10초 간격, start_period 15초)

---

## 관련 문서

- [프로젝트 분석](project_analysis.md) — 아키텍처 분석, DB 스키마
- [비용 관리](cost_management.md) — KIS API 최적화, Redis 캐싱 전략
