# THE WEALTH — Tasks (현재 작업)

이 문서는 **지금 바로 실행할 작업** 목록이다.
`/auto-task`와 `/next-task`가 이 문서에서 작업을 읽는다.
`/discover-tasks`가 이 문서를 갱신한다.

각 항목은 하나의 커밋 단위로 완료 가능한 크기여야 한다.

---

## 버그 & 안정성
- [ ] bcrypt 버전 확인 — 현재 5.0.0, passlib 호환 이슈 재확인
- [ ] CSRF: cookie 기반 JWT 사용 시 SameSite 속성 확인
- [ ] KIS API 실패 시 대시보드 에러 표시 (현재 빈 화면 가능)

## 테스트 인프라
- [ ] pytest + pytest-asyncio 설정 및 conftest 작성
- [ ] 인증 API 단위 테스트 (register, login, refresh)
- [ ] 포트폴리오 CRUD API 통합 테스트
- [ ] 종목 검색 서비스 단위 테스트
- [ ] reconciliation 서비스 단위 테스트
- [ ] vitest + React Testing Library 설정 (frontend)
- [ ] 인증 플로우 컴포넌트 테스트 (login, register)

## UI 개선
- [ ] shadcn/ui Dialog, Input, Card, Table 설치 및 인라인 HTML 교체
- [ ] 모바일 반응형: 사이드바 → 햄버거 메뉴 or 바텀 내비게이션
- [ ] 프론트엔드 전역 에러 바운더리 + toast 알림 통합
- [ ] 다크 모드 색상 점검 및 조정
- [ ] 로딩 스켈레톤 UI (대시보드, 포트폴리오 목록)

## 현재가 안정성
- [ ] Redis에 마지막 조회 가격 캐싱 (TTL 1h) — KIS API 폴백
- [ ] 가격 조회 실패 시 "마지막 업데이트: N분 전" 표시
- [ ] 서버 시작 시 종목 리스트 백그라운드 프리로딩 (첫 검색 지연 제거)
