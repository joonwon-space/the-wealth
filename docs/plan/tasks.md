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

- [ ] PWA 지원 — `frontend/public/manifest.json` 생성, `<link rel="manifest">` 추가, 앱 아이콘 설정
- [ ] 사이드바 드로어 제스처 지원 — 모바일에서 swipe to close (터치 이벤트 기반)
- [ ] 모바일 하단 네비게이션 바 — 모바일(md 미만)에서 사이드바 대신 하단 탭 바 (홈/분석/종목검색/설정)

## Milestone 14-2: 백엔드 구조화 로깅

- [ ] `structlog` 도입 — `backend/requirements.txt`에 추가, `backend/app/core/logging.py` 설정, JSON 포맷 + request_id 컨텍스트
- [ ] 기존 `print()` 및 `logging.basicConfig` 호출을 structlog 로거로 교체 (api/, services/ 전체)
