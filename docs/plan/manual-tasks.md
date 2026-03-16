# 수동 처리 필요 항목

auto-task 실행 중 사용자가 직접 처리해야 하는 항목 목록입니다.
각 항목을 완료한 후 관련 작업을 다시 요청해주세요.

---

## 1. PostgreSQL 데이터베이스 설정

**파일**: `backend/.env`

`backend/.env.example`을 복사해서 `backend/.env`를 생성하고 아래 값을 실제 환경에 맞게 수정하세요.

```bash
cp backend/.env.example backend/.env
```

수정 필요 항목:
- `DATABASE_URL` — PostgreSQL 연결 문자열
  - 기본값: `postgresql+asyncpg://postgres:postgres@localhost:5432/the_wealth`
  - 로컬 PostgreSQL이 없으면 `docker-compose up -d` 실행 (docker-compose.yml 생성 후)
- `SECRET_KEY` — JWT 서명용 비밀키 (랜덤 32바이트 이상 문자열)
  - 생성 방법: `openssl rand -hex 32`
- `ENCRYPTION_MASTER_KEY` — AES-256 암호화 마스터키 (32바이트)
  - 생성 방법: `openssl rand -hex 32`

---

## 2. Redis 설정

**파일**: `backend/.env`

- `REDIS_URL` — Redis 연결 문자열
  - 기본값: `redis://localhost:6379`
  - 로컬 Redis가 없으면 Docker로 실행: `docker run -d -p 6379:6379 redis:alpine`

---

## 3. KIS (한국투자증권) API 자격증명

KIS OpenAPI 계좌 연동 기능을 사용하려면 한국투자증권 OpenAPI를 신청해야 합니다.

- 신청 URL: https://apiportal.koreainvestment.com/
- 발급 후 앱에서 사용자 계정에 KIS 자격증명 등록 API (`POST /users/kis-credentials`) 호출

---

## 4. Alembic 마이그레이션 실행

DB 연결 설정 완료 후 아래 명령어로 마이그레이션을 실행하세요:

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

---

## 5. Docker Compose로 로컬 인프라 실행 (선택)

PostgreSQL + Redis를 Docker로 실행하려면:

```bash
docker-compose up -d
```

(Milestone 공통/인프라 작업에서 docker-compose.yml이 생성됩니다)
