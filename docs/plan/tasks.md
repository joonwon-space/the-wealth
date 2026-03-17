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

## Milestone 11-2: 분석 페이지 강화

- [x] 투자 성과 지표 계산 API (`GET /analytics/metrics`) — 샤프 비율, MDD, CAGR, 총 수익률
- [x] 분석 페이지에 성과 지표 카드 표시

## Milestone 12-3: 성능 최적화

- [x] 대시보드 API KIS 중복 호출 제거 — `fetch_domestic_price_detail` 단일 호출로 통합
- [x] 백엔드 유닛 테스트 추가 — analytics 지표 계산 (CAGR, MDD, Sharpe)
- [x] 백엔드 유닛 테스트 추가 — price snapshot 서비스 (save_snapshots, get_prev_close)
- [x] 월별 수익률 데이터 API (`GET /analytics/monthly-returns`) + 분석 페이지 히트맵

## Milestone 11-1: PWA & 모바일 네비게이션

- [x] PWA 지원 — `manifest.json` + `<link rel="manifest">` + 앱 아이콘 (192/512px)
- [x] 모바일 하단 네비게이션 바 — 대시보드·분석·포트폴리오·설정 탭 (md:hidden)

## Milestone 12-3b: 쿼리 최적화

- [x] `GET /dashboard/summary` holdings 조회에 selectinload 제거 — N+1 없음 확인 + 느린 쿼리 로깅 추가
- [x] `analytics.py` `get_metrics`에서 `fetch_prices_parallel` → `fetch_domestic_price_detail` 단일 호출로 교체 (dashboard와 동일하게)

## Milestone 11-4: 종목 상세 페이지

- [x] `GET /stocks/{ticker}/detail` B/E — KIS 종목 기본 정보 (시가총액, PER, PBR, 배당수익률) `FHKST01010100` output 활용
- [x] `/dashboard/stocks/[ticker]` 프론트엔드 라우트 — 캔들스틱 차트 + 기본 정보 카드 + 내 보유 현황 오버레이

## Milestone 14: 인프라

- [x] Dockerfile 멀티스테이지 빌드 최적화 (backend) — builder + runtime 단계 분리, 이미지 슬림화

## Milestone 12-4: 알림 시스템 (기초)

- [x] `alerts` 테이블 + SQLAlchemy 모델 + Alembic 마이그레이션 (user_id, ticker, condition, threshold, is_active)
- [x] `POST /alerts` + `GET /alerts` + `DELETE /alerts/{id}` API
- [x] 대시보드 summary 응답 후 alert 조건 확인 로직 — 가격 도달 시 알림 생성 (`triggered_alerts` 응답 필드)
- [x] 프론트엔드: 설정 페이지에 목표가 알림 등록 UI + 알림 배지

## Milestone 13-1: 외부 데이터 & 분석 확장

- [x] `GET /analytics/portfolio-history` — price_snapshots 기반 일별 포트폴리오 총 가치 시계열 API
- [x] 분석 페이지 포트폴리오 가치 추이 선 차트 (Recharts LineChart, 기간 선택)
- [x] 백엔드 유닛 테스트 추가 — alerts API (create, list, delete, check_triggered_alerts)

## Milestone 16-2: 테스트 커버리지 강화

- [x] 백엔드 전체 테스트 커버리지 측정 + 80% 미달 모듈 목록 파악
- [x] `app/services/kis_token.py` 유닛 테스트 — TTL 파싱, 토큰 캐시 히트/미스
- [x] `app/api/portfolios.py` 통합 테스트 강화 — 다중 포트폴리오 holdings 쿼리 검증

## Milestone 11-5: UX 편의 기능

- [x] 다크모드 토글을 설정 페이지에도 노출 (현재 사이드바만)
- [x] 분석 페이지 로딩 스켈레톤 개선 — MetricCard, heatmap, history chart 각각 개별 스켈레톤
