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
| `cash_balance:{portfolio_id}` | JSON (CashBalance) | 30초 | 예수금 캐시 |
| `order_lock:{portfolio_id}:{ticker}` | "1" | 10초 | 이중 주문 방지 락 |
| `order_rate:{user_id}` | count | 60초 | 주문 레이트 리밋 (10회/분) |
| `sse-ticket:{ticket}` | user_id (문자열) | 30초 | SSE 스트림 단기 인증 티켓 |

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
Strict-Transport-Security: max-age=31536000; includeSubDomains  # HSTS (프로덕션 환경에서만 추가)
```

HSTS 헤더는 `ENVIRONMENT=production` 설정 시에만 응답에 포함됩니다 (로컬/개발 환경 HTTPS 미사용 고려).

---

## 8. 레이트 리미팅

slowapi 기반 IP별 레이트 리미팅:

| 설정 | 값 |
|------|------|
| 기본 제한 | 60 요청/분 (IP 기준) |
| 키 함수 | `get_remote_address` |
| 초과 시 | `429 Too Many Requests` |

주요 엔드포인트별 개별 제한:

| 엔드포인트 | 제한 | 비고 |
|-----------|------|------|
| `POST /auth/register` | 3/min | 무차별 대입 방지 |
| `POST /auth/login` | 5/min | 무차별 대입 방지 |
| `POST /auth/refresh` | 20/min | SEC-101: 토큰 재발급 남용 방지 |
| `POST /auth/sse-ticket` | 30/min | SSE 티켓 남용 방지 |
| `POST /portfolios/{id}/orders` | 10/min | 주문 남용 방지 (Sprint 10에서 30→10 강화) |
| `GET /portfolios/{id}/orders/orderable` | 30/min | SEC-102: KIS API 보호 |
| `GET /portfolios/{id}/orders/pending` | 30/min | SEC-102: KIS API 보호 |
| `POST /portfolios/{id}/orders/settle` | 10/min | SEC-102: KIS API 보호 |
| `POST /sync/balance` | 5/min | KIS API 보호 |
| `POST /sync/{portfolio_id}` | 5/min | KIS API 보호 |
| `POST /users/me/change-password` | 5/min | 보안 계정 작업 |
| `POST /users/me/change-email` | 5/min | 보안 계정 작업 |
| `DELETE /users/me` | 5/min | 보안 계정 작업 |

---

## 9. 로깅 & 모니터링

### structlog 구조화 로깅

- 모든 요청에 `X-Request-ID` (UUID4) 자동 부여
- 로그에 request_id 포함으로 요청 추적 가능
- 응답 헤더에 `X-Request-ID` 반환

### MetricsMiddleware

- 모든 HTTP 요청에 `X-Process-Time` 응답 헤더 추가 (ms 단위)
- structlog에 `process_time_ms` 필드로 기록
- 엔드포인트별 응답 시간 추적 가능

### Sentry APM

- **백엔드**: `sentry-sdk[fastapi]` -- 글로벌 예외 핸들러 연동, `SENTRY_DSN` 환경변수
- **프론트엔드**: `@sentry/nextjs` -- Error Boundary `captureException` 연동, `NEXT_PUBLIC_SENTRY_DSN` 환경변수
- 프로덕션 환경에서만 활성화
- tracesSampleRate: 0.2, replaysOnErrorSampleRate: 1.0

### 헬스체크

```
GET /health → { "status": "ok" }
```

Docker Compose 헬스체크:
- PostgreSQL: `pg_isready -U postgres` (5초 간격)
- Redis: `redis-cli ping` (5초 간격)
- Backend: `curl -f http://localhost:8000/health` (10초 간격, start_period 15초)

---

## 10. 환경변수 (`backend/.env`)

`backend/.env.example`에서 복사하여 설정합니다.

| 변수 | 필수 | 설명 | 예시 |
|------|------|------|------|
| `DATABASE_URL` | O | PostgreSQL 연결 문자열 (asyncpg) | `postgresql+asyncpg://postgres:postgres@localhost:5432/the_wealth` |
| `JWT_SECRET_KEY` | O | JWT 서명 키 (최소 32자 hex 권장) | `openssl rand -hex 32` |
| `JWT_ALGORITHM` | - | JWT 알고리즘 (기본: HS256) | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | - | Access token 유효시간 (기본: 30) | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | - | Refresh token 유효일수 (기본: 7) | `7` |
| `ENCRYPTION_MASTER_KEY` | O | AES-256 마스터 키 (64자 hex) | `openssl rand -hex 32` |
| `REDIS_URL` | O | Redis 연결 URL | `redis://localhost:6379` |
| `CORS_ORIGINS` | O | 허용 Origin (쉼표 구분) | `http://localhost:3000,https://joonwon.dev` |
| `COOKIE_DOMAIN` | - | 쿠키 도메인 (프로덕션: `.joonwon.dev`) | `.joonwon.dev` |
| `KIS_BASE_URL` | - | KIS OpenAPI 기본 URL | `https://openapi.koreainvestment.com:9443` |
| `INTERNAL_SECRET` | - | 내부 API 인증 시크릿 (백업 스크립트용) | `openssl rand -hex 16` |
| `SENTRY_DSN` | - | Sentry 에러 트래킹 DSN (백엔드) | `https://xxx@sentry.io/xxx` |
| `ENVIRONMENT` | - | Sentry 환경 이름 (기본: `development`) | `production` |
| `LOG_DIR` | - | 파일 로깅 디렉토리 (비어 있으면 stdout만) | `/var/log/the-wealth` |
| `LOG_MAX_BYTES` | - | 로그 파일 최대 크기 (기본: 10MB) | `10485760` |
| `LOG_BACKUP_COUNT` | - | 로그 파일 보존 개수 (기본: 5) | `5` |
| `R2_ENDPOINT` | - | Cloudflare R2 엔드포인트 (비어 있으면 원격 업로드 비활성) | `https://<account-id>.r2.cloudflarestorage.com` |
| `R2_BUCKET` | - | R2 버킷 이름 | `the-wealth-backup` |
| `R2_ACCESS_KEY_ID` | - | R2 액세스 키 | |
| `R2_SECRET_ACCESS_KEY` | - | R2 시크릿 키 | |
| `KIS_RATE_LIMIT_PER_SEC` | - | KIS API 토큰 버킷 보충 속도 (기본: 5.0 req/s) | `5.0` |
| `KIS_RATE_LIMIT_BURST` | - | KIS API 버스트 최대 크기 (기본: 15 토큰, KIS 18/s 정책 반영) | `15` |
| `KIS_TOKEN_RATE_LIMIT_PER_SEC` | - | KIS 토큰 발급 전용 레이트 리밋 속도 (기본: 1.0 req/s) | `1.0` |
| `KIS_TOKEN_RATE_LIMIT_BURST` | - | KIS 토큰 발급 버스트 크기 (기본: 1 토큰) | `1` |
| `KIS_HTTP_MAX_RETRIES` | - | KIS HTTP 429/EGW00201 수신 시 재시도 횟수 (기본: 1) | `1` |
| `KIS_MOCK_MODE` | - | `true` 설정 시 KIS 레이트 리밋 비활성화 (로컬 개발/테스트용) | `false` |

> KIS App Key/Secret은 환경변수가 아닌 `kis_accounts` 테이블에 AES-256-GCM 암호화하여 저장됩니다.

### Web Push (VAPID)

| 키 | 필수 | 설명 | 예시 |
|----|-----|------|------|
| `VAPID_PUBLIC_KEY` | push 사용 시 | URL-safe base64 공개키. 빈 문자열이면 푸시 비활성. | `BH...` |
| `VAPID_PRIVATE_KEY` | push 사용 시 | URL-safe base64 비공개키 (서버 전용). | |
| `VAPID_SUBJECT` | push 사용 시 | `mailto:` 또는 `https://` 연락처 (RFC 8292). | `mailto:admin@joonwon.dev` |

- 키 쌍 생성: `python -c "from py_vapid import Vapid; v = Vapid(); v.generate_keys(); print(v.private_pem().decode()); print(v.public_pem().decode())"` (또는 `web-push` CLI).
- 키 회전: 새 키 발급 → `push_subscriptions` 전 레코드 invalidate 필요 (클라이언트가 새 public key 로 재구독해야 함). `TRUNCATE push_subscriptions;` + 사용자 재구독 유도.
- 엔드포인트:
  - `GET /api/v1/push/public-key` — `{public_key, enabled}` 반환 (인증 불필요 + 분당 30회)
  - `POST /api/v1/push/subscribe` — `endpoint` unique, 재호출은 upsert (인증 필요 + 분당 10회)
  - `DELETE /api/v1/push/subscribe?endpoint=...` — 소유자만 삭제 가능 (IDOR 방지)
- 발송 경로: `app/services/push_sender.py → pywebpush` (동기 → asyncio 스레드풀). 410/404 응답 시 해당 구독 자동 삭제.
- 알림 트리거: `app/api/prices.py:_check_alerts_and_emit` 가 가격 알림 발생 시 push 병행.

### E2E / 테스트 전용 환경변수

다음 환경변수는 백엔드 서버 환경변수가 아니라 E2E 테스트 실행 환경에서만 사용됩니다.

| 키 | 설명 | 예시 |
|----|------|------|
| `VISUAL_QA_EMAIL` | E2E 테스트용 계정 이메일 | `qa@example.com` |
| `VISUAL_QA_PASSWORD` | E2E 테스트용 계정 비밀번호 | |

---

## 관련 문서

- [프로젝트 분석](analysis.md) -- 아키텍처 분석, DB 스키마
- [비용 관리](../reviews/cost_management.md) -- KIS API 최적화, Redis 캐싱 전략
- [API 레퍼런스](api-reference.md) -- 전체 엔드포인트 상세
- [프론트엔드 가이드](frontend-guide.md) -- 프론트엔드 구조
