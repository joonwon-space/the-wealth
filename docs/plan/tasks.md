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

- [x] **chore: flatted Prototype Pollution 취약점 해결** (`npm audit fix`)
  - eslint -> file-entry-cache -> flat-cache -> flatted 3.4.1 (high severity)
  - `npm audit fix` 또는 eslint 버전 업데이트로 해결

- [x] **chore: frontend 의존성 마이너 업데이트**
  - Next.js 16.1.7 -> 16.2.0, tailwindcss 4.2.1 -> 4.2.2, shadcn 4.0.8 -> 4.1.0
  - `npm update` 후 빌드 확인

---

### P1 -- Milestone 14-2: API 응답시간 미들웨어

- [ ] **feat: MetricsMiddleware — process_time structlog 기록 + X-Process-Time 헤더**
  - `backend/app/middleware/metrics.py` 신규 파일
  - `app/main.py` 에 미들웨어 등록
  - structlog 로그: `method`, `path`, `status_code`, `process_time_ms` 필드
  - 응답 헤더: `X-Process-Time: <ms>ms`

### P1 -- Milestone 12-4: 알림 센터

- [ ] **feat: notifications 테이블 Alembic 마이그레이션**
  - `backend/app/models/notification.py` — `id`, `user_id`, `alert_id`, `ticker`, `message`, `is_read`, `created_at` 컬럼
  - Alembic migration 파일 생성

- [ ] **feat: notifications CRUD API** (`GET /api/v1/notifications`, `PATCH /api/v1/notifications/{id}/read`, `POST /api/v1/notifications/read-all`)
  - `backend/app/api/notifications.py` 신규
  - `backend/app/schemas/notification.py` 신규
  - alert SSE 트리거 시 `notifications` 테이블에 레코드 생성 (alerts.py 수정)

- [ ] **feat: 프론트엔드 알림 벨 + 읽지 않은 배지 + 드롭다운 패널**
  - `frontend/src/components/NotificationBell.tsx` 신규
  - 30초 폴링 또는 SSE로 미읽은 알림 개수 표시
  - 드롭다운 패널에서 읽음 처리 가능

### P1 -- Milestone 16-2: MSW + 프론트엔드 컴포넌트 테스트

- [ ] **chore: MSW (Mock Service Worker) 설정**
  - `npm install -D msw` 후 `frontend/src/test/mocks/` 핸들러 구조 생성
  - `frontend/src/test/mocks/handlers.ts` — auth/portfolio/dashboard API 핸들러
  - `frontend/src/test/mocks/server.ts` — vitest용 setupServer
  - `frontend/src/test/setup.ts` 업데이트 (MSW server lifecycle)

- [ ] **test: format.ts 유틸 단위 테스트**
  - `frontend/src/test/lib/format.test.ts` 신규
  - formatCurrency, formatPercent, formatNumber 등 엣지 케이스 포함

- [ ] **test: auth store (zustand) 단위 테스트**
  - `frontend/src/test/store/auth.test.ts` 신규
  - 로그인 상태, 토큰 갱신, 로그아웃 플로우 테스트

### P2 -- Milestone 11-5: Trade 메모 기능

- [ ] **feat: transactions.memo 컬럼 추가 (Alembic)**
  - `backend/app/models/transaction.py` 에 `memo: str | None` 컬럼 추가
  - Alembic migration 파일

- [ ] **feat: transactions API memo 필드 반영**
  - `backend/app/schemas/transaction.py` — `memo` 필드 추가
  - `PUT /api/v1/portfolios/{id}/transactions/{tx_id}` 엔드포인트에서 memo 업데이트 지원

### P2 -- Milestone 13-5a: Disk 모니터링

- [ ] **feat: health 엔드포인트 disk_usage 필드 추가**
  - `backend/app/services/backup_health.py` 에 `get_disk_usage()` 함수 추가
  - `backend/app/api/health.py` — `disk_usage: {path, used_gb, total_gb, percent}` 필드 추가
  - 80% 초과 시 `disk_status: "warning"` 반환

