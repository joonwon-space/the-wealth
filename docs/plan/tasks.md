# THE WEALTH — Tasks (현재 작업)

이 문서는 **지금 바로 실행할 작업** 목록이다.
`/auto-task`와 `/next-task`가 이 문서에서 작업을 읽는다.
`/discover-tasks`가 이 문서를 갱신한다.

각 항목은 하나의 커밋 단위로 완료 가능한 크기여야 한다.

---

## 보안 & 의존성
- [x] setuptools 58.0.4 → 82.0.1 업그레이드 (3개 CVE 해결)
- [x] python-multipart — 0.0.22는 Python 3.10+ 필요, 현재 3.9.6에서 불가 → Python 업그레이드를 todo.md에 추가
- [x] ecdsa 0.19.1 — 최신 버전이며 패치 없음, 사용처(python-jose) 확인 완료

## 버그 & 안정성
- [x] KIS API 실패 시 대시보드 에러 표시 — 에러 메시지 + 다시 시도 버튼 추가
- [x] scheduler.py _sync_all_accounts 실제 구현 — DB에서 KIS 자격증명 있는 사용자 조회 후 동기화 실행
- [x] ruff 린터 venv에 설치 및 기존 코드 lint 수정 (4개 unused import 제거)

## 테스트 인프라
- [x] pytest + pytest-asyncio 설정 및 conftest 작성
- [x] 인증 API 단위 테스트 (register, login, refresh) — 8개 통과
- [x] 포트폴리오 CRUD API 통합 테스트 — 9개 통과
- [x] 종목 검색 서비스 단위 테스트 (KRX + ETF 파싱) — 8개 통과
- [x] reconciliation 서비스 단위 테스트 — 4개 통과
- [x] vitest + React Testing Library 설정 (frontend)
- [x] 인증 플로우 컴포넌트 테스트 (login, register) — 8개 통과

## UI 개선
- [x] shadcn/ui Dialog, Input, Card, Table 설치 및 인라인 HTML 교체
- [ ] 모바일 반응형: 사이드바 → 햄버거 메뉴 or 바텀 내비게이션
- [ ] 프론트엔드 전역 에러 바운더리 + toast 알림 통합
- [ ] 다크 모드 색상 점검 및 조정
- [ ] 로딩 스켈레톤 UI (대시보드, 포트폴리오 목록)

## 현재가 안정성
- [ ] Redis에 마지막 조회 가격 캐싱 (TTL 1h) — KIS API 폴백
- [ ] 가격 조회 실패 시 "마지막 업데이트: N분 전" 표시
- [ ] 서버 시작 시 종목 리스트 백그라운드 프리로딩 (첫 검색 지연 제거)
