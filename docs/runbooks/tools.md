# 운영 도구 목록

The Wealth 프로젝트에서 사용 중인 외부 서비스 및 도구 모음.

---

## 모니터링 & APM

### Sentry
- **용도**: 에러 트래킹 및 성능 모니터링 (APM)
- **플랜**: Free
- **프로젝트**:
  - `the-wealth-backend` (FastAPI) — `sentry-sdk[fastapi]` 2.55.0
  - `the-wealth-frontend` (Next.js) — `@sentry/nextjs`
- **설정 위치**:
  - 백엔드: `backend/app/main.py` (`sentry_sdk.init`)
  - 프론트엔드: `frontend/sentry.client.config.ts`, `sentry.server.config.ts`, `sentry.edge.config.ts`
  - ErrorBoundary: `frontend/src/components/ErrorBoundary.tsx` (`captureException`)
- **env**:
  - `SENTRY_DSN` (backend `.env`)
  - `NEXT_PUBLIC_SENTRY_DSN` (frontend `.env.local`)
- **샘플링**: traces 20%, profiles 10%, replays 5% (에러 시 100%)

### UptimeRobot
- **용도**: 서버 다운타임 감지 — 외부에서 주기적으로 헬스체크 엔드포인트 호출
- **플랜**: Free (모니터 50개, 5분 간격)
- **모니터 URL**: `https://api.joonwon.dev/api/v1/health`
- **알림**: 이메일
- **참고**: HEAD 요청도 허용하도록 FastAPI 엔드포인트 `api_route(methods=["GET", "HEAD"])` 처리

---

## CI/CD & 코드 품질

### GitHub Actions
- **용도**: lint, test, build, E2E, Docker 빌드 자동화
- **워크플로우 위치**: `.github/workflows/`

### Dependabot
- **용도**: 의존성 자동 업데이트 PR 생성

### CodeQL
- **용도**: 코드 보안 취약점 정적 분석

### Husky + lint-staged
- **용도**: 커밋 전 ESLint / tsc 자동 실행
- **설정 위치**: `frontend/.husky/`, `frontend/package.json` (`lint-staged`)

### Commitlint
- **용도**: conventional commit 형식 강제
- **설정 위치**: `frontend/commitlint.config.js`

---

## 개발 도구

### Claude Code
- **용도**: AI 코딩 어시스턴트 (Anthropic)
- **에이전트**: planner, architect, tdd-guide, code-reviewer, security-reviewer, database-reviewer
- **설정 위치**: `.claude/`

### Playwright MCP
- **용도**: 브라우저 자동화, Visual QA, E2E 테스트
- **설정 위치**: `.mcp.json`

---

## 인프라

### PostgreSQL
- **용도**: 메인 데이터베이스
- **백업**: 일일 `pg_dump` (7일 보관) — `backend/scripts/backup-postgres.sh`

### Redis
- **용도**: KIS API 토큰 캐시, 적응형 캐시 TTL

### Docker
- **용도**: 멀티스테이지 빌드로 백엔드 + 프론트엔드 컨테이너화
- **설정 위치**: `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`
