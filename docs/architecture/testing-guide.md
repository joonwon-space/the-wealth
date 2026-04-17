# Testing Guide

백엔드(pytest) + 프론트엔드(Vitest + MSW) + E2E(Playwright) 테스트 전체 가이드.

---

## 1. 백엔드 테스트 (pytest)

### 1.1 빠른 실행

```bash
cd backend
source venv/bin/activate   # Windows: source venv/Scripts/activate

# 단위 테스트만 (Postgres 불필요)
pytest -m unit -q

# 모든 테스트 (Postgres 필요 — docker compose로 기동 후 실행)
pytest -q --tb=short

# 커버리지 포함
pytest --cov=app --cov-report=term-missing -q
```

### 1.2 pytest 마커

`backend/pytest.ini`에 정의:
```ini
markers =
    unit: Unit tests
    integration: Integration tests
asyncio_mode = auto
```

사용법:
```python
import pytest

@pytest.mark.unit
def test_some_pure_function():
    ...

@pytest.mark.integration
async def test_api_endpoint(client, db_session):
    ...
```

- `@pytest.mark.unit` — 외부 의존성(DB, Redis, HTTP) 없이 실행 가능한 테스트
- `@pytest.mark.integration` — 실제 Postgres 필요. `TEST_DATABASE_URL` env var 사용
- 비동기 테스트는 `async def`로 정의하면 `asyncio_mode = auto` 설정으로 자동 처리

### 1.3 DB Isolation (per-test transaction rollback)

`backend/tests/conftest.py` 핵심 fixtures:

| Fixture | 스코프 | 역할 |
|---------|--------|------|
| `db_engine` | `session` | 테스트 전 스키마 생성, 후 드롭 (line 44) |
| `db_tables` | `session` | `CREATE ALL` / `DROP ALL` once (line 49) |
| `db_session` | `function` | 각 테스트에 트랜잭션 롤백 세션 제공 (line 105) |
| `session_factory` | `function` | `async_sessionmaker` 바인딩 (line 116) |

**동작 원리** (`conftest.py:103-118`):
```python
@pytest_asyncio.fixture
async def db_session(db_engine):
    async with db_engine.begin() as conn:
        async with AsyncSession(bind=conn) as session:
            yield session
            await session.rollback()   # 테스트 후 자동 롤백
```
각 테스트는 독립된 트랜잭션에서 실행되므로 테스트 간 데이터가 누출되지 않음.

**테스트 DB URL** (`conftest.py:23-25`):
```python
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
)
```
다른 사용자 이름을 쓰는 경우:
```bash
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/the_wealth_test"
```

### 1.4 테스트 파일 현황

`backend/tests/`에 총 64개 파일. 주요 파일:

| 파일 | 내용 |
|------|------|
| `test_auth.py` | 로그인, refresh, 세션 revoke |
| `test_dashboard.py` | 대시보드 summary API |
| `test_analytics_metrics.py` | Sharpe/MDD/CAGR 계산 |
| `test_kis_rate_limiter.py` | Token bucket 단위 + 통합 |
| `test_encryption.py` | AES-256 암호화/복호화 |
| `test_error_response_format.py` | API 에러 응답 포맷 일관성 |

---

## 2. 프론트엔드 테스트 (Vitest + MSW)

### 2.1 빠른 실행

```bash
cd frontend

# 단발 실행
npx vitest run

# watch 모드
npx vitest

# UI 모드
npx vitest --ui

# 커버리지
npx vitest run --coverage
```

### 2.2 MSW (Mock Service Worker) 핸들러

`frontend/src/test/handlers.ts` — 백엔드 API를 모킹하는 MSW 핸들러 목록.

핸들러 추가 방법:
```typescript
// frontend/src/test/handlers.ts
import { http, HttpResponse } from "msw";

const API_BASE = "http://localhost:8000/api/v1";

export const handlers = [
  // 기존 핸들러들...

  // 새 엔드포인트 핸들러 추가
  http.post(`${API_BASE}/portfolios`, () => {
    return HttpResponse.json({ id: 1, name: "Test Portfolio" }, { status: 201 });
  }),

  // 에러 응답 모킹
  http.get(`${API_BASE}/holdings`, () => {
    return HttpResponse.json({ detail: "Not found" }, { status: 404 });
  }),
];
```

`frontend/src/test/server.ts` — MSW 서버 설정. `handlers`를 import해서 테스트 시 intercept.

`frontend/src/test/setup.ts` — Vitest 글로벌 setup. MSW 서버 `beforeAll/afterEach/afterAll` 처리.

### 2.3 컴포넌트 테스트 패턴

```typescript
// example: src/components/__tests__/MyComponent.test.tsx
import { render, screen } from "@testing-library/react";
import { server } from "@/test/server";
import { http, HttpResponse } from "msw";
import MyComponent from "../MyComponent";

test("renders error state when API fails", async () => {
  // 특정 테스트에서만 핸들러 오버라이드
  server.use(
    http.get("http://localhost:8000/api/v1/some-endpoint", () => {
      return HttpResponse.json({ detail: "error" }, { status: 500 });
    })
  );

  render(<MyComponent />);
  expect(await screen.findByText(/오류/)).toBeInTheDocument();
});
```

---

## 3. E2E 테스트 (Playwright)

### 3.1 로컬 실행

```bash
cd frontend

# 브라우저 설치 (첫 실행 시)
npx playwright install

# 모든 E2E 테스트 실행 (dev 서버 자동 시작)
npx playwright test

# 특정 테스트 파일만
npx playwright test e2e/auth.spec.ts

# UI 모드 (시각적 디버깅)
npx playwright test --ui

# 헤드 모드 (브라우저 표시)
npx playwright test --headed
```

### 3.2 설정 (`frontend/playwright.config.ts`)

| 설정 | 값 | 의미 |
|------|-----|------|
| `testDir` | `./e2e` | E2E 파일 위치 |
| `workers` | `1` | 순차 실행 (병렬 X) |
| `retries` | `2` (CI), `0` (로컬) | CI에서 재시도 |
| `baseURL` | `http://localhost:3000` | `PLAYWRIGHT_BASE_URL` env var로 오버라이드 가능 |
| `projects` | Chromium + iPhone 14 | 데스크탑 + 모바일 |

로컬에서 `webServer` 설정이 dev 서버를 자동 시작함. CI에서는 `webServer: undefined`이므로 서버를 별도로 기동해야 함.

### 3.3 E2E 환경 변수

```bash
# E2E/Visual QA 테스트 계정 (.env에 설정)
VISUAL_QA_EMAIL=qa@example.com
VISUAL_QA_PASSWORD=yourpassword

# 기본 URL 오버라이드 (staging 등)
PLAYWRIGHT_BASE_URL=https://staging.joonwon.dev
```

---

## 4. 커버리지 타겟 80% 유지

### 백엔드
```bash
cd backend
pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

커버리지 리포트 해석:
- `MISS` 라인이 많은 파일 → 해당 API 엔드포인트 통합 테스트 추가
- 서비스 레이어 함수는 단위 테스트로 커버

### 프론트엔드
```bash
cd frontend
npx vitest run --coverage
# v8 coverage 사용 (vite.config.ts에 설정됨)
```

80% 미달 시 커버 전략:
1. 에러 상태 분기 (API 실패, 빈 데이터) 테스트 추가
2. 조건부 렌더 (`if (loading)`, `if (error)`) 커버

---

## 5. TDD 체크리스트

새 기능 구현 전:

```
[ ] 실패하는 테스트 작성 (RED)
[ ] 테스트 실행 → FAIL 확인
[ ] 최소 구현으로 통과 (GREEN)
[ ] 테스트 실행 → PASS 확인
[ ] 리팩토링 (IMPROVE) — 로직 중복 제거, 가독성
[ ] 커버리지 80%+ 확인
[ ] CI 통과 확인
```

백엔드 새 API 엔드포인트 TDD 순서:
1. `backend/tests/test_{resource}.py`에 테스트 작성
2. Pydantic schema (`app/schemas/`) 정의
3. 라우터 함수 stub (`app/api/`) — HTTPException 반환
4. 서비스 로직 구현 (`app/services/`)
5. 라우터 함수 완성

---

## Related

- [`docs/architecture/getting-started.md`](./getting-started.md) — 테스트 실행 전 환경 설정
- [`docs/runbooks/troubleshooting.md`](../runbooks/troubleshooting.md) — pytest DB 연결 실패 해결
- [`docs/architecture/database-schema.md`](./database-schema.md) — 테스트 DB 스키마 이해
