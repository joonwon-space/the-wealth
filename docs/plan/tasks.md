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
- [x] Milestone 12-1: 가격 히스토리 & 전일 대비 (all items)
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

</details>

---

## Milestone 12-1: 가격 히스토리 & 전일 대비

- [ ] `price_snapshots` 테이블 Alembic 마이그레이션 생성 (ticker, date, open, high, low, close, volume; unique index on ticker+date)
- [ ] 장 마감 후 일별 종가 스냅샷 스케줄러 — APScheduler cron KST 16:10, 보유 종목만, KIS 일별 시세 API 활용
- [ ] `GET /dashboard/summary` 응답에 "전일 대비" 변동률 필드 추가 (price_snapshots 기반 계산)
- [ ] 가격 히스토리 API — `GET /prices/{ticker}/history?from=&to=` 엔드포인트
- [ ] 대시보드 요약 카드에 "전일 대비" 배지 표시 (▲ +2.3% / ▼ -1.5%, 한국 증시 컬러 적용)
