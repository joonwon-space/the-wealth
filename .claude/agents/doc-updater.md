---
name: doc-updater
description: Sync all docs/ files with current codebase state. Extracts ground truth from code first, then diffs against docs, then updates. Never relies on AI memory.
model: sonnet
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Documentation Updater

**Core principle**: Extract facts from code first → diff against docs → update only what's wrong.
Never rely on AI memory. Always verify from source before writing anything.

---

## Phase 1: Extract Ground Truth from Code

Run ALL of the following before reading any docs. Save results mentally as your "source of truth".

### 1a. Backend routes (full paths)

First get router prefixes:
```bash
grep -rn "APIRouter(prefix=" backend/app/api/*.py | \
  sed 's/.*api\/\([^.]*\)\.py.*prefix="\([^"]*\)".*/\2 → \1.py/' | sort
```

Then get all route decorators per file:
```bash
grep -rn "^@router\." backend/app/api/*.py | \
  grep -E '\.(get|post|patch|delete|put)\("' | \
  sed 's|backend/app/api/||; s|\.py:[0-9]*:@router\.| |; s|("| |; s|".*||'
```

Read `backend/app/main.py` to confirm router include order and any path overrides.

Combine prefix + relative path to build a **complete canonical route list**:
```
METHOD  /full/path                                FILE
GET     /portfolios                               portfolios.py
POST    /portfolios/{id}/holdings                 portfolios.py
POST    /portfolios/{id}/holdings/bulk            portfolios.py
...
```

### 1b. Frontend pages

```bash
find frontend/src/app -name "page.tsx" | \
  sed 's|frontend/src/app||; s|/page\.tsx$||' | sort
```

Also check sidebar nav items to confirm which pages are linked:
```bash
grep -n "href" frontend/src/components/Sidebar.tsx | grep dashboard
```

### 1c. DB models

```bash
grep -rn "^class " backend/app/models/*.py | grep "(Base)" | \
  sed 's/.*class \([A-Za-z]*\).*/\1/'
```

For each model, note its table name and key columns by reading the file.

### 1d. Recent changes

```bash
git log --oneline -20
```

Note every commit that adds/removes/renames a feature, endpoint, or page.

### 1e. Build & test status

```bash
cd frontend && npx tsc --noEmit 2>&1 | tail -5
```
```bash
cd backend && source venv/bin/activate && ruff check . 2>&1 | tail -5
```
```bash
cd backend && source venv/bin/activate && pytest -q --tb=no 2>&1 | tail -3
```

---

## Phase 2: Read All Docs

Read every doc file in full. Skip with a note if it does not exist (tracked in Sprint 16 if missing).

**Core architecture (always required):**
- `docs/architecture/overview.md`
- `docs/architecture/api-reference.md` (if exists)
- `docs/architecture/frontend-guide.md` (if exists)
- `docs/architecture/analysis.md`
- `docs/architecture/infrastructure.md`
- `docs/architecture/README.md` (index)

**Extended architecture (Sprint 16+, each guarded with `if exists`):**
- `docs/architecture/getting-started.md`
- `docs/architecture/testing-guide.md`
- `docs/architecture/kis-integration.md`
- `docs/architecture/auth-flow.md`
- `docs/architecture/feature-trading.md`
- `docs/architecture/feature-analytics.md`
- `docs/architecture/security-model.md`
- `docs/architecture/database-schema.md`
- `docs/architecture/design-system.md`
- `docs/architecture/cost-management.md`

**Runbooks (if exists):**
- `docs/runbooks/troubleshooting.md`
- `docs/runbooks/deploy.md`
- `docs/runbooks/*.md` (other existing runbooks)

**Read-only context:**
- `docs/plan/tasks.md`
- `docs/plan/todo.md`

If a doc in this list is missing, record it in the final report as "Missing (tracked in Sprint 16)" — do NOT auto-create unless the task explicitly asks for it.

---

## Phase 3: Build Explicit Diffs

For EACH doc, produce two lists before touching anything:

### API diff (for overview.md section 5 and api-reference.md)

**Missing from docs** (route exists in code, not in docs):
```
+ POST /portfolios/{id}/holdings/bulk
+ GET  /portfolios/{id}/export/xlsx
+ GET  /portfolios/{id}/transactions/paginated
...
```

**Stale in docs** (route in docs, not in code):
```
- POST /portfolios/{id}/something-removed
...
```

### Pages diff (for overview.md section 3 and frontend-guide.md)

**Missing from docs**:
```
+ /dashboard/journal
...
```

**Stale in docs**:
```
- /dashboard/old-page
...
```

### Features diff (for overview.md section 2)

From git log, identify features added since docs were last updated. For each:
- Does overview.md section 2 mention it? If not → add.

If diffs are all empty → docs are in sync, skip to Phase 5.

---

## Phase 4: Update Docs

Apply only what the diff found. Do NOT rewrite sections that are still accurate.

### `docs/architecture/overview.md`

**Section 2 (기능 명세)** — Add missing features:
- New table rows only. Do not reorganize existing accurate rows.
- Example: "Excel 내보내기", "보유종목 일괄 등록", "투자 일지" if added since last update.

**Section 3 (페이지 구조)** — Sync tree with extracted page list:
- Add missing pages with a short description.
- Remove pages that no longer exist.

**Section 5 (API 엔드포인트 전체 목록)** — Sync with canonical route list:
- Update group counts in headers (e.g., "### 포트폴리오 (21)").
- Add missing rows. Remove stale rows.
- Keep existing descriptions for unchanged routes.

### `docs/architecture/api-reference.md`

For each **missing** endpoint from the diff, add a section:
```markdown
### METHOD /full/path
- **Auth**: Required / None
- **Rate limit**: X/minute (if applicable)
- **Request body**: `{ field: type }` (read the schema file to fill this in accurately)
- **Response** (status_code): shape or description
- **Description**: what it does in one sentence
```

Read the actual schema/route handler before writing request/response shapes — do not guess.

For each **stale** endpoint, remove its section entirely.

### `docs/architecture/frontend-guide.md`

- Sync the page routing map with the extracted page list.
- Add sections for new pages (what they show, key components used).
- Remove sections for deleted pages.
- If the file doesn't exist, create it with the structure below.

### `docs/architecture/analysis.md`

- Update "최근 변경사항" / "Recent improvements" section from git log.
- Update test coverage numbers from pytest output.
- Remove weaknesses that are now resolved (cross-reference git log).
- Add new risks if introduced (e.g., new external API dependency).

### `docs/architecture/infrastructure.md`

Update only if:
- New env vars were added (cross-reference `backend/.env.example`)
- New services added (Redis, new scheduler jobs, etc.)
- Docker compose changed

---

## Phase 4b: Extended Doc Drift Vectors (Sprint 16 docs)

For each file below, extract specific facts from code and patch only those. **Do not rewrite narrative sections** — only update code-derived tables/lists/versions.

### `docs/architecture/kis-integration.md`

Code-derived facts to verify:
- **TR_ID table**: `grep -rn 'tr_id\s*=\s*"' backend/app/services/kis_*.py` → compare extracted TR_IDs against doc's table. Add missing rows, remove dead ones.
- **Rate limiter params**: read `backend/app/core/config.py` for `KIS_RATE_LIMIT_PER_SEC`, `KIS_RATE_LIMIT_BURST`, `KIS_MOCK_MODE` defaults → sync with doc.
- **Token cache key**: `grep -n "kis_access_token" backend/app/services/kis_token.py` → confirm Redis key pattern in doc matches.
- **KIS base URLs**: `grep "KIS_BASE_URL\|KIS_MOCK_BASE_URL" backend/app/core/config.py` → verify doc.

Narrative sections (error-handling philosophy, rationale) — leave alone.

### `docs/architecture/auth-flow.md`

Code-derived facts:
- JWT TTL constants: `grep -n "ACCESS_TOKEN_EXPIRE\|REFRESH_TOKEN_EXPIRE" backend/app/core/config.py`
- Cookie names and flags: `grep -n "set_cookie\|HttpOnly\|samesite" backend/app/api/auth.py`
- Redis key patterns: `grep -rn "refresh_token:\|sse-ticket:" backend/app/`
- Endpoint list: `/auth/login`, `/auth/register`, `/auth/refresh`, `/auth/logout`, `/auth/sessions`, `/auth/sessions/{jti}`, `/auth/sse-ticket`, `/auth/change-password` (if moved back)

If the sequence diagram mentions an endpoint that no longer exists or a Redis key renamed, update the diagram.

### `docs/architecture/feature-trading.md`

Code-derived facts:
- Order states enum: `grep -rn "class OrderStatus\|OrderStatus\." backend/app/models/ backend/app/schemas/`
- Scheduler job names touching orders: `grep -rn "add_job\|@scheduler" backend/app/services/scheduler*.py` → filter for order/settlement jobs
- Functions involved: list all public functions in `kis_order_place.py`, `order_settlement.py`, `reconciliation.py`

### `docs/architecture/feature-analytics.md`

Code-derived facts:
- Analytics endpoints: `grep -n "@router\." backend/app/api/analytics*.py`
- Scheduler job table: every `scheduler.add_job(...)` call across `scheduler.py`, `scheduler_portfolio_jobs.py`, `scheduler_market_jobs.py`, `scheduler_ops_jobs.py` — id, trigger, target function
- Metrics formulas: update only if the actual calculation code changed (verify by reading the relevant handler)

### `docs/architecture/security-model.md`

Code-derived facts:
- Encrypted fields: `grep -rn "encrypt_field\|decrypt_field\|EncryptedField" backend/app/` → list actually encrypted columns
- Audit-logged events: `grep -rn "audit_service\.\|log_security_event" backend/app/` → enumerate event types
- bcrypt cost: `grep -n "bcrypt\|CryptContext" backend/app/core/security.py`
- Rate-limited endpoints count: from api-reference/infrastructure rate limit table

### `docs/architecture/database-schema.md`

Code-derived facts:
- Table list + row count: `grep -rn "^class \w\+.*Base" backend/app/models/*.py` → sync ERD table count
- FK relationships: `grep -rn "ForeignKey(" backend/app/models/` → verify every relationship drawn in ERD exists
- Index definitions: `grep -rn "Index(\|index=True" backend/app/models/`
- Latest migration: `ls -t backend/alembic/versions/*.py | head -1` → doc should reference the head revision

### `docs/architecture/getting-started.md`

Code-derived facts:
- Python version: `grep "^python" backend/Dockerfile\|python_version` in `backend/requirements.txt` or `backend/pyproject.toml`
- Node version: `cat frontend/package.json | grep '"engines"'` or `.nvmrc`
- Env var list: diff `backend/.env.example` fields against doc's env table
- Startup commands: verify each command in doc still works (e.g., `alembic upgrade head`, `uvicorn app.main:app --reload`)

### `docs/architecture/testing-guide.md`

Code-derived facts:
- pytest markers: `grep -rn "pytestmark\|@pytest.mark" backend/tests/ | sed 's/.*@pytest.mark.\([a-z]*\).*/\1/' | sort -u`
- MSW handlers list: `grep -n "http.get\|http.post" frontend/src/test/handlers.ts`
- Coverage target: `grep "fail_under\|--cov-fail" backend/pytest.ini backend/pyproject.toml 2>/dev/null`
- E2E spec count: `ls frontend/e2e/*.spec.ts | wc -l`

### `docs/architecture/design-system.md`

Code-derived facts:
- Theme tokens: `grep "^  --" frontend/src/app/globals.css | head -40`
- shadcn config: `cat frontend/components.json`
- Installed UI components: `ls frontend/src/components/ui/`

### `docs/runbooks/troubleshooting.md`

Code-derived facts — verify each "증상 → 원인 → 해결" still matches:
- Env var names referenced must exist in `backend/.env.example`
- File paths mentioned must exist (`ls` check)
- Error messages quoted should be greppable in the codebase

### `docs/runbooks/deploy.md`

Code-derived facts:
- CI workflow jobs: `grep -A1 "^  [a-z-]*:" .github/workflows/deploy.yml | grep "name:" | head -10`
- Docker image names: `grep "image:" docker-compose.prod.yml` (if present)

---

## Phase 5: Create Missing Files

### If `docs/architecture/api-reference.md` doesn't exist

Generate from canonical route list. For every route, read the handler and schema to fill in accurate request/response shapes.

Structure:
```markdown
# API Reference

Base URL: `/api/v1`
Auth: Bearer token required on all endpoints except /auth/* and /health

---

## Auth (`/auth`)
### POST /auth/register
...

## Portfolios (`/portfolios`)
### GET /portfolios
...
```

### If `docs/architecture/frontend-guide.md` doesn't exist

```markdown
# Frontend Guide

## Page Routing Map

| Route | Description |
|-------|-------------|
| /login | 로그인 |
| /register | 회원가입 |
| /dashboard | 메인 대시보드 |
...

## State Management
- TanStack Query: server state, cache invalidation on mutations
- Zustand (`useAuthStore`): auth token, user info
- Optimistic updates via `queryClient.setQueryData`

## HTTP Client
- Axios instance in `frontend/src/lib/api.ts`
- Response interceptor: JWT expiry → auto refresh rotation
- Base URL: `process.env.NEXT_PUBLIC_API_URL`

## How to Add a New Page
1. Create `frontend/src/app/dashboard/{name}/page.tsx`
2. Add nav entry in `Sidebar.tsx` (desktop) and `BottomNav.tsx` (mobile)
3. Register query key in relevant hook file
4. Update this doc's page routing map

## Key Components
| Component | Purpose |
|-----------|---------|
...

## Theming
- shadcn/ui `base-nova` style, `neutral` base color
- Korean color convention: red = gain, blue = loss
- Dark mode via `next-themes`
```

---

## Phase 5b: Templates for Sprint 16 Docs (only if explicitly requested to create)

**Default behavior: do NOT auto-create any Sprint 16 doc file.** Those are owned by explicit tasks in `docs/plan/tasks.md` (DOC-201~211). Creation from template loses the author's framing and rationale.

If the task explicitly says "create `docs/architecture/<file>.md` from template", use these scaffolds:

- `kis-integration.md` — sections: Overview / TR_ID table (domestic+overseas, real vs mock) / Rate limiter (token bucket params, mock mode) / Token lifecycle / Error codes / Domestic vs overseas routing
- `auth-flow.md` — sections: JWT strategy / Refresh rotation sequence (ASCII diagram) / SSE ticket flow (ASCII diagram) / Session management / Cookie flags / Redis key patterns
- `feature-trading.md` — sections: Order state diagram / Public service functions / Locks and idempotency / Settlement trigger / Reconciliation scope
- `feature-analytics.md` — sections: Metric definitions + formulas / Data sources (tables) / Scheduler job table / Benchmark collection
- `security-model.md` — sections: Threat model (scoped) / Encrypted fields / Non-encrypted sensitive fields / Key rotation / Audit events / bcrypt + JWT params
- `database-schema.md` — sections: ERD / Table-by-table summary / Key indexes / Migration workflow (generate → review → apply → rollback) / Seed data
- `getting-started.md` — sections: Prerequisites (versions) / Clone → install → env → DB → run / Windows-specific gotchas / Verifying the setup
- `testing-guide.md` — sections: pytest markers / conftest fixtures / MSW handlers / E2E (Playwright) / Coverage policy / TDD checklist
- `design-system.md` — sections: Theme tokens / Korean color convention / shadcn extension rules / `cn()` usage / Dark mode / Component authoring checklist
- `runbooks/troubleshooting.md` — sections organized by symptom, each with: Symptom / Root cause / Resolution steps (command-level)
- `runbooks/deploy.md` — sections: Normal deploy flow / Rollback / Hotfix / Manual migration / Smoke tests

Each template is a skeleton — the task author is responsible for filling narrative. The agent's job on re-runs is to keep code-derived facts (tables, version numbers, keys) in sync with code.

---

## Phase 6: Commit

```bash
git add docs/
git commit -m "docs: sync documentation with current codebase state"
```

---

## Phase 7: Output Report

```
## Ground Truth (extracted from code)
- Backend routes: N total
- Frontend pages: N total
- DB models: N total

## Diffs Applied
### overview.md
  Added endpoints: POST /portfolios/{id}/holdings/bulk, GET /portfolios/{id}/export/xlsx, ...
  Added pages: /dashboard/journal
  Added features: Excel 내보내기, 보유종목 일괄 등록, 투자 일지

### api-reference.md
  Added sections: POST /portfolios/{id}/holdings/bulk, GET /portfolios/{id}/export/xlsx, ...
  Removed sections: (none)

### frontend-guide.md
  Added pages: /dashboard/journal
  No other changes.

### analysis.md
  Updated: test coverage N% → N%, added 3 recent improvements

### infrastructure.md
  No changes needed.

## Unchanged (verified accurate)
- docs/architecture/infrastructure.md (no env var or service changes)

## Missing (tracked in Sprint 16)
- docs/architecture/kis-integration.md (DOC-202)
- docs/runbooks/troubleshooting.md (DOC-201)
- ... (list files that were in Phase 2 but did not exist)

## Build Status
  TypeScript: ✓ / ✗ (N errors)
  Ruff: ✓ / ✗ (N issues)
  Tests: N passed, N failed — coverage N%

## Committed
  docs: sync documentation with current codebase state
```
