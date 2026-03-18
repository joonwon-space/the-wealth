# THE WEALTH — Tasks

Current work items. Read by `/auto-task` and `/next-task`.
Each item should be completable in a single commit.

---

## Completed (archive)

<details>
<summary>Previously completed items</summary>

- [x] `filelock` 3.19.1 → 3.25.2 업그레이드
- [x] `python-jose` → `PyJWT` 마이그레이션
- [x] `passlib` → `bcrypt` 직접 사용으로 마이그레이션
- [x] `backend/.env.example`에 `CORS_ORIGINS` 항목 추가
- [x] KIS 자격증명 등록 시 API 연결 테스트 엔드포인트
- [x] KIS 자격증명 연결 테스트 UI
- [x] Milestone 11-1: 모바일 UX (all items)
- [x] Milestone 11-3: 보유 종목 테이블 52주 고/저 (all items)
- [x] Milestone 12-2: SSE 실시간 가격 (all items)
- [x] Milestone 11-2: 분석 페이지 강화 (all items)
- [x] Milestone 12-3: 성능 최적화 (all items)
- [x] Milestone 11-1: PWA & 모바일 네비게이션 (all items)
- [x] Milestone 12-3b: 쿼리 최적화 (all items)
- [x] Milestone 11-4: 종목 상세 페이지 (all items)
- [x] Milestone 14: 인프라 — Dockerfile 멀티스테이지 빌드
- [x] Milestone 12-4: 알림 시스템 (all items)
- [x] Milestone 13-1: 포트폴리오 히스토리 API + 차트 (all items)
- [x] Milestone 16-2: 테스트 커버리지 강화 (all items)
- [x] Milestone 11-5: UX 편의 기능 (all items)
- [x] Milestone 12-5: API 품질 개선 (all items)
- [x] Milestone 16-2b: 테스트 커버리지 확대 (all items)
- [x] Milestone 14-3 / 16-3: CI/CD & 코드 품질 (all items)
- [x] Milestone 10: AI 브라우저 에이전트 (all items)
- [x] Milestone 16-1: Claude Code 에이전트 확장 (all items)
- [x] Milestone 16-2: Playwright E2E 테스트 셋업 (all items)
- [x] Milestone 16-3: openapi-typescript 타입 자동 생성 (all items)
- [x] Milestone 11-2: 섹터 배분 차트 (all items)
- [x] Milestone 11-3: 워치리스트 (all items)
- [x] Milestone 14-4: 보안 헤더 강화 (all items)
- [x] Milestone 15-4: 데이터 내보내기 — CSV export (all items)
- [x] Milestone 14-3: CI/CD — Docker 빌드 검증 워크플로우
- [x] 테스트 커버리지 보강 (신규 기능) — watchlist, csv_export, security_headers, sector_allocation, WatchlistSection, SectorAllocationChart
- [x] portfolios.py 분할 — CSV export 로직을 portfolio_export.py로 분리
- [x] Milestone 12-1: 가격 히스토리 & 전일 대비 (all items)

</details>

---

## Milestone 11-1: 모바일 UX (잔여)

- [x] PWA 지원 — `frontend/public/manifest.json` 생성, `<link rel="manifest">` 추가, 앱 아이콘 설정
- [x] 사이드바 드로어 제스처 지원 — 모바일에서 swipe to close (터치 이벤트 기반)
- [x] 모바일 하단 네비게이션 바 — 모바일(md 미만)에서 사이드바 대신 하단 탭 바 (홈/분석/종목검색/설정)

## Milestone 14-2: 백엔드 구조화 로깅

- [x] `structlog` 도입 — `backend/requirements.txt`에 추가, `backend/app/core/logging.py` 설정, JSON 포맷 + request_id 컨텍스트
- [x] 기존 `print()` 및 `logging.basicConfig` 호출을 structlog 로거로 교체 (api/, services/ 전체)

---

## Short-term 개선 (아키텍처 리뷰 기반)

- [x] DB 인덱스 추가 — Alembic 마이그레이션: portfolios.user_id, holdings.portfolio_id, transactions(portfolio_id+traded_at DESC), price_snapshots(ticker+snapshot_date DESC), sync_logs(user_id+synced_at DESC), watchlist.user_id, alerts(user_id+is_active) partial index
- [x] users 테이블 레거시 컬럼 정리 — 코드에서 legacy 컬럼 참조 제거 후 Alembic DROP COLUMN 마이그레이션 (kis_app_key_enc, kis_app_secret_enc, kis_account_no, kis_acnt_prdt_cd)
- [x] 엔드포인트별 Rate Limit 세분화 — slowapi decorator로 /auth/login 5/min, /auth/register 3/min, /sync/* 5/min, /dashboard/* 120/min 개별 설정
- [x] ticker 정규식 검증 추가 — HoldingCreate, TransactionCreate, WatchlistCreate 스키마에 field_validator 추가 (국내: `^[0-9]{6}$`, 해외: `^[A-Z]{1,5}$`)
- [x] pagination max limit 캡 — transactions list, sync_logs list 엔드포인트에 최대 limit=100 제한
- [x] transactions soft delete — `deleted_at` nullable DateTime 컬럼 추가 Alembic 마이그레이션 + DELETE API → SET deleted_at + 조회 쿼리 WHERE deleted_at IS NULL
- [x] HttpOnly cookie 인증 마이그레이션 — 백엔드 Set-Cookie (HttpOnly+Secure+SameSite=Lax), 프론트엔드 withCredentials:true + localStorage 토큰 저장 제거
- [x] Error Boundary 추가 — 대시보드/분석/포트폴리오 페이지에 React Error Boundary + fallback UI (에러 메시지 + Retry 버튼)
- [x] 번들 최적화 — lightweight-charts와 Recharts를 next/dynamic으로 동적 import 전환, @next/bundle-analyzer 설치 및 스크립트 추가
- [x] Graceful Shutdown — FastAPI lifespan shutdown에 SSE 연결 종료 이벤트 + APScheduler.shutdown(wait=True) + docker-compose.yml에 stop_grace_period: 30s 추가

---

## Milestone 16-2: 테스트 커버리지 강화

- [x] core/security.py 테스트 보강 — `revoke_all_refresh_tokens_for_user`, `decode_refresh_token` 엣지케이스, 만료 JWT, 잘못된 타입 검증 (목표: 90%+)
- [x] services/kis_price.py KIS API 모킹 테스트 — httpx 응답 모킹으로 정상/429/401/timeout/빈 응답 시나리오 (목표: 85%+)
- [x] services/kis_account.py 테스트 보강 — KIS 계정 CRUD 및 잔고 동기화 로직 단위 테스트 (목표: 85%+)
- [x] 보안 테스트 — IDOR 시도(타 사용자 리소스 접근), 만료 JWT 거부, 소진 JTI 거부, rate limit 429 검증

## Milestone 12-5: API 품질 개선

- [x] 표준화된 에러 응답 포맷 — `{"error": {"code": "...", "message": "...", "request_id": "..."}}` 형식으로 FastAPI exception handler 통일
- [x] API 버전관리 — 모든 APIRouter에 `/api/v1` prefix 추가, 프론트엔드 Axios baseURL 업데이트

## Milestone 16-3: 코드 품질 도구

- [x] Husky + lint-staged — `frontend/` 에 설치, 커밋 전 `eslint --fix` + `tsc --noEmit` 자동 실행
