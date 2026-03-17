# THE WEALTH — Tasks

Current work items. Read by `/auto-task` and `/next-task`.
Each item should be completable in a single commit.

---

- [x] `filelock` 3.19.1 → 3.25.2 업그레이드 (GHSA-w853-jp5j-5j7f, GHSA-qmgc-5h2g-mvrw)
- [x] `python-jose` → `PyJWT` 마이그레이션 (`ecdsa` 취약점 GHSA-wj6h-64fc-37mp 해소)
- [x] `passlib` → `bcrypt` 직접 사용으로 마이그레이션 (Python 3.13 `crypt` 모듈 제거 대비)
- [x] `backend/.env.example`에 `CORS_ORIGINS` 항목 추가
- [x] KIS 자격증명 등록 시 API 연결 테스트 엔드포인트 (B/E: `/users/kis-accounts/{id}/test`)
- [x] KIS 자격증명 연결 테스트 UI ("연결 테스트" 버튼 + 성공/실패 피드백)

## Milestone 12-1: 가격 히스토리 & 전일 대비

- [x] `price_snapshots` SQLAlchemy 모델 생성 + Alembic 마이그레이션
- [x] KIS 전일 종가 조회 서비스 함수 (`FHKST01010100`)
- [x] APScheduler 장 마감 스냅샷 job 추가 (KST 16:05, 보유 종목 대상)
- [x] `GET /dashboard/summary` 응답에 종목별 `day_change_rate` 추가
- [x] 대시보드 프론트엔드에 전일 대비 배지 표시 (▲ +1.2% / ▼ -0.8%)

## Milestone 11-1: 모바일 UX

- [x] 사이드바 드로어 스와이프로 닫기 제스처 (swipe left to close)
- [x] 가격 히스토리 API `GET /prices/{ticker}/history`
- [x] analytics 페이지 `day_change_rate` 컬럼 반영
- [x] 대시보드 요약 카드에 포트폴리오 전일 대비 변동률 배지 (`total_day_change_rate`)

## Milestone 11-3: 보유 종목 테이블 52주 고/저

- [x] `PriceDetail`에 `w52_high` / `w52_low` 추가 (FHKST01010100 응답 활용)
- [x] dashboard API 응답 `HoldingWithPnL`에 `w52_high` / `w52_low` 추가
- [x] 보유 종목 테이블에 52주 범위 프로그레스 바 컬럼 추가

## Milestone 12-2: SSE 실시간 가격

- [x] `GET /prices/stream` SSE 엔드포인트 — 보유 종목 가격 30초 간격 push
- [x] 프론트엔드 SSE 클라이언트 — 대시보드 가격 실시간 업데이트 (시장 개장 시간 한정)
