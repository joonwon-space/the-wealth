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

Read every doc file in full:
- `docs/architecture/overview.md`
- `docs/architecture/api-reference.md` (if exists)
- `docs/architecture/frontend-guide.md` (if exists)
- `docs/architecture/analysis.md`
- `docs/architecture/infrastructure.md`
- `docs/plan/tasks.md` — read-only context
- `docs/plan/todo.md` — read-only context

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

## Build Status
  TypeScript: ✓ / ✗ (N errors)
  Ruff: ✓ / ✗ (N issues)
  Tests: N passed, N failed — coverage N%

## Committed
  docs: sync documentation with current codebase state
```
