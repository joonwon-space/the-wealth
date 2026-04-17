# Deployment Runbook

배포 프로세스, CI/CD 실패 대응, 롤백, 핫픽스, 수동 마이그레이션.

---

## 1. 배포 흐름

### 자동 배포 (CI/CD)

`main` 브랜치에 push/merge 되면 `.github/workflows/deploy.yml`이 자동 실행:

```
main branch push
    │
    ▼
deploy.yml (self-hosted runner)
    │
    ├─ Write backend .env from GitHub Secret (BACKEND_ENV_FILE)
    ├─ Unlock macOS Keychain (KEYCHAIN_PASSWORD)
    ├─ docker compose build --parallel
    ├─ docker compose up -d --remove-orphans
    ├─ Wait for backend health (localhost:8000/health, 최대 60s)
    ├─ Wait for frontend health (localhost:3000, 최대 30s)
    └─ docker image prune -f
```

> 주의: 배포 워크플로는 Alembic migration을 **자동으로 실행하지 않음**. 스키마 변경이 포함된 PR은 반드시 수동으로 마이그레이션을 실행해야 함 (섹션 4 참조).

---

## 2. CI 실패 대응

### 2.1 Backend CI (`backend.yml`) 실패

CI는 `backend/**` 경로 변경 시 실행. 실패 케이스:

| 실패 단계 | 원인 | 해결 |
|-----------|------|------|
| `ruff check` | lint 오류 | `cd backend && ruff check . --fix` |
| `pytest` | 테스트 실패 | 에러 메시지 확인 후 코드 수정 |
| `alembic upgrade head` | 마이그레이션 충돌 | 섹션 5 참조 |
| Postgres/Redis service 불안정 | GitHub Actions 인프라 이슈 | Re-run job |

로컬에서 동일 환경 재현:
```bash
cd backend
source venv/bin/activate
ruff check .
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/the_wealth_test"
pytest -q --tb=short
```

### 2.2 Frontend CI (`frontend.yml`) 실패

| 실패 단계 | 원인 | 해결 |
|-----------|------|------|
| `npm run lint` | ESLint 오류 | `cd frontend && npm run lint -- --fix` |
| `npx tsc --noEmit` | 타입 오류 | 타입 오류 수정 |
| `npm run build` | 빌드 실패 | 에러 메시지 확인 |
| OOM during build | heap 부족 | `NODE_OPTIONS="--max-old-space-size=4096" npm run build` |

---

## 3. 롤백 절차

현재 배포 방식은 Docker image를 빌드 후 즉시 실행. 명시적 image tagging이 없으므로 롤백은 Git을 통해 수행.

### 빠른 롤백 (revert commit)

```bash
# 1. 문제 커밋 SHA 확인
git log --oneline -10

# 2. Revert 커밋 생성 (PR 불필요하면 main에 직접)
git revert <bad-commit-sha> --no-edit
git push origin main

# 3. 배포 워크플로가 자동 트리거됨 → 이전 상태로 복구
```

### 이전 Docker image로 수동 복구 (서버 SSH 접속)

서버에 이전 이미지가 남아 있는 경우:
```bash
# 현재 실행 중인 이미지 확인
docker images | grep the-wealth

# 이전 이미지 태그로 docker-compose.yml 수정 후 재시작
docker compose up -d --force-recreate backend
```

> 일반적으로는 revert commit이 더 안전하고 추적 가능.

---

## 4. 수동 Alembic 마이그레이션 (배포 후)

스키마 변경이 있는 PR 머지 후 서버에서 실행:

```bash
# 1. 서버 SSH 접속
ssh user@server

# 2. 프로젝트 디렉토리로 이동
cd /path/to/the-wealth

# 3. 백엔드 컨테이너에서 alembic 실행
docker compose exec backend alembic upgrade head

# 4. 결과 확인 (에러 없이 완료되어야 함)
```

또는 컨테이너 외부에서 (venv 사용):
```bash
cd backend
source venv/bin/activate
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/the_wealth" \
  alembic upgrade head
```

**마이그레이션 전 확인 사항**:
- `alembic heads` — 단일 head인지 확인 (복수이면 merge 필요)
- `alembic current` — 현재 DB revision 확인
- `alembic history --verbose` — 적용될 마이그레이션 목록

---

## 5. 핫픽스 프로세스

critical 버그로 PR 없이 main에 직접 push가 필요한 경우:

```bash
# 1. main 기준으로 hotfix 브랜치 생성
git checkout main && git pull
git checkout -b hotfix/issue-description

# 2. 수정 → commit
# (로컬에서 ruff, pytest, tsc --noEmit 확인 필수)

# 3. main에 직접 머지 (PR 권장이나 긴급 시 direct push 가능)
git checkout main
git merge --no-ff hotfix/issue-description
git push origin main

# 4. 배포 자동 트리거 확인
# GitHub Actions → deploy.yml 실행 확인
```

direct push to main이 가능한 경우: 서버 장애, 데이터 손실 위험, 보안 취약점.
일반 버그 수정은 PR 필수.

---

## 6. 배포 전/후 Smoke 체크

### 배포 전 (로컬)

```bash
# Backend
cd backend && source venv/bin/activate
ruff check .
pytest -m unit -q   # 빠른 확인

# Frontend
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

### 배포 후 (서버)

```bash
# 1. 헬스 체크
curl https://api.joonwon.dev/health
# 기대 응답: {"status": "ok", "redis": "ok", ...}

# 2. 주요 API 응답 확인
curl -I https://api.joonwon.dev/docs   # Swagger UI 200 OK

# 3. 프론트엔드 접속
curl -I https://joonwon.dev   # 200 OK

# 4. 로그에 에러 없는지 확인
docker compose logs backend --since 5m | grep -i "error\|exception\|critical"

# 5. Docker 컨테이너 상태
docker compose ps   # 모두 healthy 상태여야 함
```

---

## 7. 환경 변수 관리

배포 시 `.env`는 GitHub Secret `BACKEND_ENV_FILE`에서 주입됨 (deploy.yml).

**새 env var 추가 시 절차**:
1. `backend/.env.example`에 주석과 함께 추가
2. `backend/app/core/config.py`에 Settings 클래스 필드 추가
3. GitHub → Settings → Secrets → `BACKEND_ENV_FILE` 업데이트
4. PR 머지 후 배포 확인

---

## Related

- [`docs/runbooks/troubleshooting.md`](./troubleshooting.md) — 배포 후 서비스 이상 시
- [`docs/architecture/database-schema.md`](../architecture/database-schema.md) — Alembic migration 체크리스트
- [`docs/architecture/getting-started.md`](../architecture/getting-started.md) — 로컬 환경 설정
