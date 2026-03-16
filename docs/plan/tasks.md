# THE WEALTH — Tasks (실행 가능한 작업 목록)

## 이 문서의 용도

`todo.md`가 마일스톤 단위의 **완료된 로드맵**이라면,
이 문서는 **앞으로 할 작업**을 우선순위와 실행 단위로 관리한다.

- 각 작업은 하나의 커밋 또는 PR 단위로 완료 가능한 크기
- 우선순위: P0 (즉시) → P1 (이번 주) → P2 (이번 달) → P3 (백로그)
- 완료 시 `[x]`로 체크하고 완료 날짜 기록

---

## P0 — 즉시 (안정성 & 품질)

### 테스트 인프라
- [ ] pytest + pytest-asyncio 설정 및 conftest 작성
- [ ] 인증 API 단위 테스트 (register, login, refresh)
- [ ] 포트폴리오 CRUD API 통합 테스트
- [ ] 종목 검색 서비스 단위 테스트
- [ ] reconciliation 서비스 단위 테스트
- [ ] vitest + React Testing Library 설정 (frontend)
- [ ] 인증 플로우 컴포넌트 테스트 (login, register)

### 버그 & 안정성
- [ ] bcrypt 버전 확인 — 현재 5.0.0, passlib 호환 이슈 재확인
- [ ] CSRF: cookie 기반 JWT 사용 시 SameSite 속성 확인
- [ ] KIS API 실패 시 대시보드 에러 표시 (현재 빈 화면 가능)

---

## P1 — 단기 (UX 개선)

### UI 개선
- [ ] shadcn/ui Dialog, Input, Card, Table 설치 및 인라인 HTML 교체
- [ ] 모바일 반응형: 사이드바 → 햄버거 메뉴 or 바텀 내비게이션
- [ ] 프론트엔드 전역 에러 바운더리 + toast 알림 통합
- [ ] 다크 모드 색상 점검 및 조정
- [ ] 로딩 스켈레톤 UI (대시보드, 포트폴리오 목록)

### 현재가 안정성
- [ ] Redis에 마지막 조회 가격 캐싱 (TTL 1h) — KIS API 폴백
- [ ] 가격 조회 실패 시 "마지막 업데이트: N분 전" 표시
- [ ] 서버 시작 시 종목 리스트 백그라운드 프리로딩 (첫 검색 지연 제거)

---

## P2 — 중기 (기능 확장)

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

## P3 — 장기 (백로그)

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

---

## 문서 관계

| 문서 | 용도 | 업데이트 시점 |
|------|------|--------------|
| `docs/plan/todo.md` | 마일스톤 로드맵 (완료 이력) | 마일스톤 완료 시 |
| `docs/plan/tasks.md` | 실행 가능한 작업 큐 (이 문서) | 작업 추가/완료 시 |
| `docs/plan/manual-tasks.md` | 사용자가 직접 수행할 설정 작업 | 환경 설정 변경 시 |
| `docs/analysis/project-overview.md` | 프로젝트 구조/기술 스택 스냅샷 | 아키텍처 변경 시 |
| `docs/analysis/project-analysis.md` | 기술 분석/리스크/개선 기회 | 정기 리뷰 시 |
