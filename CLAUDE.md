# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KIS(한국투자증권) API 기반 개인 자산관리 대시보드. "더리치" 앱의 UI/UX를 벤치마킹하며, 한국 증시 컬러 컨벤션(상승=빨간색, 하락=파란색)을 따른다.

## Commands

### Frontend (`frontend/`)
```bash
npm run dev      # dev server at localhost:3000
npm run build    # production build
npm run lint     # ESLint
```

### Backend (`backend/`)
```bash
source venv/bin/activate
uvicorn app.main:app --reload   # dev server at localhost:8000
alembic upgrade head            # run migrations
alembic revision --autogenerate -m "description"  # create migration
```

### Adding shadcn/ui components
```bash
cd frontend && npx shadcn@latest add <component>
```

## Architecture

### Monorepo structure
- `frontend/` — Next.js 16 App Router (React 19, TypeScript, Tailwind v4)
- `backend/` — FastAPI with async SQLAlchemy + Alembic migrations
- `docs/plan/todo.md` — 6-milestone implementation roadmap

### Frontend
- **App Router** with server components for initial SSR load optimization
- **shadcn/ui** (style: `base-nova`, baseColor: `neutral`) — copy-paste component model; components live in `src/components/ui/`
- **Path alias**: `@/` maps to `src/`
- **State**: client-side auth state via Zustand or Context API; optimistic updates on mutations
- **HTTP**: Axios instance with response interceptor for JWT expiry + auto refresh token rotation
- **Data grids**: TanStack Table v8 for holdings table with multi-column sorting
- **Charts**: Recharts — donut chart with center overlay text for asset allocation

### Backend
- **Entry point**: `app/main.py` — CORS allows `localhost:3000`
- **Planned directory layout**: `app/{api, core, db, models, schemas, services}`
- **Auth**: JWT access tokens (30min) + refresh token rotation; passlib/bcrypt for password hashing; `get_current_user` dependency on all protected routes
- **KIS token lifecycle**: Redis caches the 24h KIS access token; proactive rotation before expiry
- **Price calculation**: Current prices and P&L are computed dynamically via KIS API (`asyncio.gather` for concurrent requests) — never stored in DB to avoid stale data
- **Encryption**: AES-256 for storing KIS API credentials in DB; master key from env

### Database (PostgreSQL via async SQLAlchemy)
Core tables: `users`, `portfolios`, `holdings`, `transactions`
Migrations managed with Alembic.

### Security patterns
- IDOR prevention: always validate `user_id` ownership before returning/modifying records
- KIS credentials stored AES-256 encrypted; master key in env, never in code
- Bearer token required on all non-auth endpoints

## Environment
Copy `backend/.env.example` to `backend/.env` and fill in values before running the backend.
