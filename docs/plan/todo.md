# The Wealth - TODO

## Milestone 1: 백엔드 초기화 & DB 스캐폴딩

- [x] PostgreSQL 연결 설정 (`DATABASE_URL` 환경변수)
- [x] SQLAlchemy async engine 및 session 설정 (`app/db/session.py`)
- [x] Base 모델 클래스 생성 (`app/db/base.py`)
- [x] `users` 테이블 모델 정의 (id, email, hashed_password, kis_app_key_enc, kis_app_secret_enc, created_at)
- [x] `portfolios` 테이블 모델 정의 (id, user_id, name, currency, created_at)
- [x] `holdings` 테이블 모델 정의 (id, portfolio_id, ticker, name, quantity, avg_price, created_at)
- [x] `transactions` 테이블 모델 정의 (id, portfolio_id, ticker, type, quantity, price, traded_at)
- [x] Alembic 초기화 및 첫 migration 생성
- [x] DB migration 실행 확인 (docs/plan/manual-tasks.md 참고 — DB 연결 후 `alembic upgrade head` 실행 필요)

## Milestone 2: 인증 인프라

- [x] JWT 액세스 토큰 발급 로직 구현 (`app/core/security.py`)
- [x] Refresh 토큰 rotation 로직 구현
- [x] passlib(bcrypt)으로 비밀번호 해싱 유틸 구현
- [x] 회원가입 API 엔드포인트 (`POST /auth/register`)
- [x] 로그인 API 엔드포인트 (`POST /auth/login`) → access + refresh 토큰 반환
- [x] 토큰 갱신 엔드포인트 (`POST /auth/refresh`)
- [x] JWT 검증 의존성(dependency) 구현 (`get_current_user`)
- [x] IDOR 방지: 모든 보호 엔드포인트에서 user ownership 검증

## Milestone 3: Next.js 앱 라우터 레이아웃

- [x] 반응형 사이드바 네비게이션 컴포넌트 구현 (shadcn/ui 기반)
- [x] 다크/라이트 테마 스위칭 설정 (Tailwind CSS)
- [x] 로그인 / 회원가입 페이지 (`/login`, `/register`)
- [x] 대시보드 메인 레이아웃 (`/dashboard`)
- [x] 포트폴리오 목록 페이지 (`/dashboard/portfolios`)
- [x] Axios 인스턴스 설정 + 응답 인터셉터(JWT 만료 처리, 자동 토큰 갱신)
- [x] 인증 상태 전역 관리 (Zustand or Context API)
- [x] 보호 라우트 미들웨어 구현

## Milestone 4: KIS API 연동 & 종목 검색

- [x] Redis 기반 KIS 액세스 토큰 캐싱 (`app/services/kis_token.py`)
- [x] KIS 토큰 24시간 생명주기 관리 + 만료 전 proactive rotation
- [x] KIS 종목 검색 프록시 엔드포인트 (`GET /stocks/search?q=`)
- [x] 프론트엔드 종목 검색 다이얼로그 컴포넌트 (300ms debounce)
- [x] 수동 보유 종목 추가 API (`POST /portfolios/{id}/holdings`)
- [x] 보유 종목 수정/삭제 API (`PATCH`, `DELETE /holdings/{id}`)
- [x] 국내주식 현재가 조회 (`asyncio.gather` 병렬 처리)
- [x] 해외주식 현재가 조회

## Milestone 5: 대시보드 시각화 & 실시간 수익 계산

- [x] 총 자산 / 투자원금 / 수익률 집계 API (`GET /dashboard/summary`)
- [x] 현재가 기반 동적 손익 계산 (DB에 저장하지 않고 API 호출로 계산)
- [x] 자산 배분 도넛 차트 컴포넌트 (Recharts, 중앙 텍스트 오버레이)
- [x] 보유 종목 테이블 컴포넌트 (TanStack Table, 다중 컬럼 정렬)
- [x] 한국 증시 컬러 적용: 상승 빨간색, 하락 파란색
- [x] 수익률/수익금 강조 표시 컴포넌트
- [x] 서버 사이드 렌더링으로 초기 대시보드 로드 최적화
- [x] 클라이언트 사이드 optimistic update 구현

## Milestone 6: 자동 계좌 연동 (Phase 2)

- [x] AES-256 기반 KIS 인증정보 암호화/복호화 유틸 (`app/core/encryption.py`)
- [x] 사용자 KIS 키 저장 API (`POST /users/kis-credentials`)
- [x] KIS OpenAPI 계좌 잔고 조회 연동
- [x] Reconciliation 알고리즘 구현:
  - [x] KIS 계좌 보유 종목 vs DB holdings 비교
  - [x] 신규 종목 INSERT
  - [x] 청산된 종목 DELETE
  - [x] 수량/평균단가 변경 시 UPDATE
- [x] 자동 동기화 스케줄러 (APScheduler or Celery)
- [x] 동기화 이력 로그 테이블 및 API

## 공통 / 인프라

- [x] `docker-compose.yml` 작성 (PostgreSQL + Redis)
- [x] 백엔드 `Dockerfile` 작성
- [x] 프론트엔드 `Dockerfile` 작성
- [x] 환경변수 문서화 (`.env.example` 업데이트)
- [x] API 에러 핸들링 표준화 (HTTPException 글로벌 핸들러)
- [x] Rate limiting 미들웨어 설정
- [x] 프론트엔드 500ms debounce 적용 (API 요청 최적화)

## Milestone 7: 프론트엔드 UI 완성

### 인증 플로우 수정
- [x] 로그인 후 토큰을 쿠키에도 저장 (proxy.ts가 쿠키 기반으로 동작하므로)
- [x] 로그아웃 시 쿠키 삭제
- [x] 로그인 → 대시보드 진입 동선 확인 및 수정

### 포트폴리오 페이지 (`/dashboard/portfolios`)
- [ ] 포트폴리오 목록 카드 UI
- [ ] 포트폴리오 생성 모달 (이름, 통화 입력)
- [ ] 포트폴리오 삭제 버튼

### 종목 추가/관리 UI
- [ ] 포트폴리오 상세 페이지 (`/dashboard/portfolios/[id]`)
- [ ] 종목 검색 다이얼로그 연결 (StockSearchDialog 활용)
- [ ] 종목 추가 폼 (수량, 평균단가 입력)
- [ ] 종목 수정 인라인 편집 or 모달
- [ ] 종목 삭제 버튼 + 확인 다이얼로그

### 대시보드 페이지 (`/dashboard`)
- [ ] 포트폴리오가 없을 때 빈 상태(empty state) UI
- [ ] 보유 종목이 없을 때 빈 상태 UI + 종목 추가 유도 버튼
- [ ] 대시보드 데이터 주기적 자동 새로고침 (30초 interval)

### 계좌 동기화 UI
- [ ] KIS 자격증명 설정 페이지 (`/dashboard/settings`)
- [ ] 계좌 수동 동기화 버튼 + 결과 토스트 알림
- [ ] 동기화 이력 목록
