# THE WEALTH — TODO (미래 로드맵)

이 문서는 **중장기 백로그**다. 당장 하지 않지만 언젠가 해야 할 일을 관리한다.
현재 바로 실행할 작업은 `tasks.md`에 있다.

`/discover-tasks` 커맨드가 이 문서를 갱신한다.

---

## 완료된 마일스톤

<details>
<summary>Milestone 1~7 (모두 완료)</summary>

### Milestone 1: 백엔드 초기화 & DB 스캐폴딩
- [x] PostgreSQL 연결, SQLAlchemy async, Alembic, 5개 테이블 모델

### Milestone 2: 인증 인프라
- [x] JWT access/refresh, bcrypt, register/login/refresh API, IDOR 방지

### Milestone 3: Next.js 앱 라우터 레이아웃
- [x] 사이드바, 테마, 로그인/회원가입, 대시보드, Axios 인터셉터, Zustand

### Milestone 4: KIS API 연동 & 종목 검색
- [x] KIS 토큰 캐싱, 종목 검색, holdings CRUD, 국내/해외 현재가

### Milestone 5: 대시보드 시각화 & 실시간 수익 계산
- [x] 대시보드 요약 API, 도넛 차트, 보유 종목 테이블, 한국 증시 컬러

### Milestone 6: 자동 계좌 연동
- [x] AES-256 암호화, KIS 계좌 잔고 조회, Reconciliation, APScheduler

### Milestone 7: 프론트엔드 UI 완성
- [x] 인증 플로우, 포트폴리오 CRUD UI, 종목 관리 UI, 대시보드 빈 상태, 설정 페이지

### 공통 / 인프라
- [x] Docker, Dockerfile, 환경변수, 에러 핸들링, Rate limiting, debounce

</details>

---

## Milestone 8: Python 3.10+ 업그레이드
- [ ] Python 3.9.6 → 3.10+ 업그레이드 (venv 재생성)
- [ ] python-multipart 0.0.22 업그레이드 (Python 3.10+ 필요, GHSA-wp53-j4wj-2cfg)
- [ ] `from __future__ import annotations` 제거하고 네이티브 union 문법(`str | None`) 사용

---

## Milestone 9: 기능 확장

### 거래 이력
- [ ] 거래 기록 API (POST/GET /portfolios/{id}/transactions)
- [ ] 거래 이력 UI (테이블 + 필터)
- [ ] 종목별 매매 히스토리 차트

### 분석 페이지 (`/dashboard/analytics`)
- [ ] 포트폴리오 성과 시계열 차트 (일/주/월)
- [ ] 섹터/자산군별 배분 차트
- [ ] KOSPI200 벤치마크 대비 성과
- [ ] 배당 수익 추적

### 검색 확장
- [ ] 해외주식 검색 지원 (US 주요 종목)
- [ ] 초성 검색 지원 (ㅅㅅ → 삼성전자)
- [ ] 최근 검색어 저장

---

## Milestone 10: 배포 & 운영

### 배포
- [ ] GitHub Actions CI/CD 파이프라인 (lint → test → build)
- [ ] Vercel 배포 (프론트엔드)
- [ ] Railway or Fly.io 배포 (백엔드 + PostgreSQL + Redis)
- [ ] 프로덕션 환경변수 관리 (dotenv → Vault or SSM)

### 알림 & 자동화
- [ ] 목표가 도달 알림 (웹 푸시 or 이메일)
- [ ] 일일 포트폴리오 리포트 (이메일)
- [ ] 다중 계좌 지원 (KIS 외 타 증권사)

### 성능
- [ ] WebSocket/SSE로 실시간 가격 업데이트 (polling 대체)
- [ ] 종목 검색 trie 구조 or Redis 인덱싱
- [ ] KIS 현재가 배치 API 탐색 (종목 수 많을 때 rate limit 대응)
