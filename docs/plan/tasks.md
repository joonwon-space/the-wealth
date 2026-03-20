# THE WEALTH -- Tasks

Current work items. Read by `/auto-task` and `/next-task`.
Each item should be completable in a single commit.

---

## Completed (archive)

<details>
<summary>Previously completed items</summary>

- [x] `filelock` 3.19.1 -> 3.25.2 upgrade
- [x] `python-jose` -> `PyJWT` migration
- [x] `passlib` -> `bcrypt` direct usage migration
- [x] `backend/.env.example` CORS_ORIGINS addition
- [x] KIS credential API connection test endpoint + UI
- [x] Milestone 11-1: Mobile UX (all items)
- [x] Milestone 11-2: Analytics page enhancement (all items)
- [x] Milestone 11-3: Holdings table 52-week high/low (all items)
- [x] Milestone 11-3: Watchlist (all items)
- [x] Milestone 11-4: Stock detail page (all items)
- [x] Milestone 11-5: UX convenience features (all items)
- [x] Milestone 12-1: Price history & day change (all items)
- [x] Milestone 12-2: SSE real-time prices (all items)
- [x] Milestone 12-3: Performance optimization (all items)
- [x] Milestone 12-3b: Query optimization (all items)
- [x] Milestone 12-4: Alert system (all items)
- [x] Milestone 12-5: API quality improvement (all items)
- [x] Milestone 13-1: Portfolio history API + chart (all items)
- [x] Milestone 14: Dockerfile multi-stage build
- [x] Milestone 14-2: Backend structured logging (structlog)
- [x] Milestone 14-3: CI/CD Docker build verification
- [x] Milestone 14-3 / 16-3: CI/CD & code quality (all items)
- [x] Milestone 14-4: Security headers (all items)
- [x] Milestone 15-4: Data export - CSV (all items)
- [x] Milestone 16-1: Claude Code agent expansion (all items)
- [x] Milestone 16-2: Test coverage 70%+ (all items)
- [x] Milestone 16-2: Playwright E2E test setup (all items)
- [x] Milestone 16-2b: Test coverage expansion (all items)
- [x] Milestone 16-3: openapi-typescript type generation (all items)
- [x] Short-term improvements: DB indexes, legacy columns, rate limits, ticker validation, pagination cap, soft delete, HttpOnly cookies, Error Boundary, bundle optimization, Graceful Shutdown
- [x] Milestone 10: AI browser agent (all items)
- [x] portfolios.py split - CSV export to portfolio_export.py
- [x] Fix ruff lint errors in test files (10 errors)
- [x] Test coverage 71% -> 93% (add router tests + .coveragerc sysmon fix)
- [x] Milestone 16-3: Commitlint config + Husky hook
- [x] Milestone 12-2: SSE connection hardening (per-user limit, heartbeat, 2h timeout)
- [x] Next.js middleware deprecation fix
- [x] Test coverage gaps (prices.py 61%, dashboard.py 85%)
- [x] P0 Automated DB Backup: daily pg_dump script + retention policy
- [x] P0 Single Server Resilience: restart policy + managed DB/Redis docs
- [x] Milestone 12-4: Alert Notification Logic (last_triggered_at, SSE integration, PATCH endpoint)
- [x] Milestone 16-2: Frontend Test Coverage (format.ts, auth store, usePriceStream)
- [x] Milestone 13-5c: Adaptive Cache TTL
- [x] Milestone 13-5b: Data Integrity Health Checks
- [x] Milestone 11-5: TanStack Query Adoption (all items)
- [x] Milestone 13-5b: Holdings quantity reconciliation endpoint
- [x] Milestone 13-5a: Redis failure fallback
- [x] Milestone 11-7: Frontend Quality (PnLBadge icons, ErrorBoundary, SSE status, bundle analyzer)
- [x] Milestone 13-5a: Scheduler Alerting (consecutive failure tracking)
- [x] Milestone 13-5b: Orphan Record Cleanup endpoint
- [x] Milestone 13-5c: KIS API Health Check on startup
- [x] Fix: 해외주식 관련 버그 수정 (52주 범위, 종목명, 환율, CAGR, 섹터배분)
- [x] Fix: MetricCard 툴팁 fixed 포지션
- [x] Visual QA bug fixes: accessibility, tablet layout, SSE, CSP
- [x] DB 백업 완성: restore 문서, sync_logs 기록, health last_backup_at

</details>

---

## Current work

### P0 -- Test coverage recovery (90% -> 93%+)

- [x] **test: health.py router 테스트 추가** (47% -> 85%+)
  - `/api/v1/health` 엔드포인트의 DB/Redis/KIS/backup 상태 응답 테스트
  - 파일: `backend/tests/test_health.py`

- [x] **test: internal.py router 테스트 추가** (58% -> 90%+)
  - `POST /internal/backup-status` 성공/실패 시나리오 테스트
  - 파일: `backend/tests/test_internal.py`

- [x] **test: backup_health.py service 테스트 추가** (69% -> 90%+)
  - 백업 디렉토리 존재/부재, 파일 mtime 조회 로직 테스트
  - 파일: `backend/tests/test_backup_health.py`

### P1 -- npm 의존성 보안/업데이트

- [ ] **chore: flatted Prototype Pollution 취약점 해결** (`npm audit fix`)
  - eslint -> file-entry-cache -> flat-cache -> flatted 3.4.1 (high severity)
  - `npm audit fix` 또는 eslint 버전 업데이트로 해결

- [ ] **chore: frontend 의존성 마이너 업데이트**
  - Next.js 16.1.7 -> 16.2.0, tailwindcss 4.2.1 -> 4.2.2, shadcn 4.0.8 -> 4.1.0
  - `npm update` 후 빌드 확인

