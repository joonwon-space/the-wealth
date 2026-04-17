# Getting Started

Fresh clone → fully running local development in one reading.

---

## 사전 요구사항

| 도구 | 최소 버전 | 용도 |
|------|----------|------|
| Python | **3.13** | 백엔드 FastAPI 서버 |
| Node.js | **20** | 프론트엔드 Next.js |
| Docker Desktop | 최신 | Postgres + Redis 컨테이너 |
| Git | 2.x | 소스 관리 |

> Windows 사용자: WSL2 없이 Git Bash로 진행 가능. PowerShell이 아닌 Git Bash 사용 권장.

---

## 1. 저장소 클론

```bash
git clone https://github.com/joonwon-space/the-wealth.git
cd the-wealth
```

---

## 2. 인프라 기동 (Postgres + Redis)

```bash
docker compose -f docker-compose.dev.yml up -d
```

이 명령은 다음을 시작:
- **Postgres 16** — `localhost:5432`, DB: `the_wealth`, user: `postgres`, password: `postgres`
- **Redis 7** — `localhost:6379`

헬스 체크 통과 확인 (~10초):
```bash
docker compose -f docker-compose.dev.yml ps
```
Status가 `healthy`이면 진행.

> `scripts/pg-init-hba.sh`는 Docker 네트워크(`172.18.0.0/16`)에서 비밀번호 없이 접속하도록 `pg_hba.conf`를 초기화하는 스크립트. Postgres 컨테이너 첫 실행 시 자동 적용됨.

---

## 3. 백엔드 환경 설정

### 3.1 .env 파일 생성

```bash
cp backend/.env.example backend/.env
```

`backend/.env`에서 반드시 채워야 하는 변수:

| 변수 | 예시 | 설명 |
|------|------|------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/the_wealth` | PostgreSQL 연결. 기본값으로 docker-compose.dev.yml Postgres에 연결됨 |
| `JWT_SECRET_KEY` | `$(openssl rand -hex 32)` | JWT 서명 키. 32바이트 랜덤 hex |
| `ENCRYPTION_MASTER_KEY` | `$(openssl rand -hex 32)` | KIS 자격증명 AES-256 암호화 마스터 키 |
| `REDIS_URL` | `redis://localhost:6379` | Redis 연결. 기본값 그대로 사용 가능 |
| `KIS_BASE_URL` | `https://openapi.koreainvestment.com:9443` | KIS OpenAPI URL. 모의투자: `https://openapivts.koreainvestment.com:29443` |

개발에서 비워도 되는 변수 (선택):

| 변수 | 기본 동작 |
|------|----------|
| `CORS_ORIGINS` | `http://localhost:3000` — 기본값으로 로컬 개발 정상 동작 |
| `COOKIE_DOMAIN` | 비워두면 localhost에서 쿠키 정상 동작 |
| `INTERNAL_SECRET` | 비워두면 `/internal/*` 엔드포인트 비활성화 |
| `SENTRY_DSN` | 비워두면 Sentry 비활성화 |
| `ENVIRONMENT` | `development` 또는 `production` — HSTS 헤더 조건부 활성화 |
| `LOG_DIR` | 비워두면 stdout만 출력 |
| `R2_*` | 비워두면 백업 원격 업로드 비활성화 |
| `KIS_MOCK_MODE` | `False` — `True`로 설정 시 rate limit 비활성화 (테스트용) |

### 3.2 시크릿 키 생성 (처음 한 번)

```bash
# JWT_SECRET_KEY, ENCRYPTION_MASTER_KEY 각각 생성
openssl rand -hex 32
openssl rand -hex 32
```

생성된 값을 `backend/.env`의 해당 변수에 붙여넣기.

---

## 4. 백엔드 Python 환경 설정

```bash
cd backend

# 가상 환경 생성
python -m venv venv

# 활성화 (macOS/Linux)
source venv/bin/activate

# 활성화 (Windows Git Bash)
source venv/Scripts/activate

# 의존성 설치
pip install -r requirements.txt
```

---

## 5. DB 마이그레이션

```bash
cd backend
source venv/bin/activate   # (또는 Scripts/activate)

alembic upgrade head
```

성공 시:
```
INFO  [alembic.runtime.migration] Running upgrade ... -> <revision>, ...
```

> Alembic은 `backend/alembic/env.py`에서 `DATABASE_URL` env var을 읽어 비동기 엔진(`async_engine_from_config`)으로 마이그레이션 실행.

---

## 6. 백엔드 서버 실행

```bash
cd backend
source venv/bin/activate

uvicorn app.main:app --reload
```

서버 기동 확인:
```bash
curl http://localhost:8000/health
# {"status": "ok", "redis": "ok", ...}
```

API 문서:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 7. 프론트엔드 설정 및 실행

```bash
cd frontend

npm install
npm run dev
```

브라우저에서 http://localhost:3000 접속.

> 백엔드(`localhost:8000`)가 CORS에 `http://localhost:3000`을 허용함 (`backend/app/core/config.py:20`).

---

## 8. 최초 계정 생성

1. http://localhost:3000/register 접속
2. 이메일 + 비밀번호 입력 (8자 이상)
3. 로그인 후 Settings → KIS 계정 연결

---

## Windows에서 자주 막히는 문제

### PATH 문제 — `python` 명령어를 못 찾을 때

Windows에 Python 3.13이 설치되어 있지 않거나 PATH에 없는 경우:

```bash
# Git Bash에서
which python3 || which python

# 없으면 https://www.python.org/downloads/ 에서 Python 3.13 설치
# 설치 시 "Add Python to PATH" 체크 필수
```

### Node.js PATH 문제

```bash
node --version   # v20.x.x 이어야 함
npm --version
```

Node 20이 없으면 https://nodejs.org/en/download/ 에서 LTS 설치.

### WSL2 메모리 제한 (`next build` OOM)

WSL2 사용 시 `%USERPROFILE%\.wslconfig`:
```ini
[wsl2]
memory=8GB
```

또는:
```bash
NODE_OPTIONS="--max-old-space-size=4096" npm run build
```

### Postgres 포트 충돌

Windows에서 PostgreSQL이 이미 설치되어 있어 `5432` 포트 충돌 시:
```yaml
# docker-compose.dev.yml에서 포트 변경
ports:
  - "5433:5432"
# 그 후 backend/.env의 DATABASE_URL도 :5433으로 변경
```

---

## 빠른 재시작 (이미 설정 완료 후)

```bash
# 터미널 1 — 인프라 (이미 실행 중이면 불필요)
docker compose -f docker-compose.dev.yml up -d

# 터미널 2 — 백엔드
cd backend && source venv/bin/activate && uvicorn app.main:app --reload

# 터미널 3 — 프론트엔드
cd frontend && npm run dev
```

또는 `scripts/dev-tmux.sh` 사용 (tmux가 있는 경우):
```bash
./scripts/dev-tmux.sh
```

---

## Related

- [`docs/architecture/testing-guide.md`](./testing-guide.md) — 첫 실행 후 테스트 실행 방법
- [`docs/runbooks/troubleshooting.md`](../runbooks/troubleshooting.md) — 설정 중 막히면 여기
- [`docs/architecture/kis-integration.md`](./kis-integration.md) — KIS API 연동 세부 설정
