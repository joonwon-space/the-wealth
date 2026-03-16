# THE WEALTH — Tasks (현재 작업)

이 문서는 **지금 바로 실행할 작업** 목록이다.
`/auto-task`와 `/next-task`가 이 문서에서 작업을 읽는다.
`/discover-tasks`가 이 문서를 갱신한다.

각 항목은 하나의 커밋 단위로 완료 가능한 크기여야 한다.

---

## 코드 품질
- [x] Pydantic V2 deprecation 수정 — `class Config` → `model_config = ConfigDict(...)` (5개 파일)
- [x] /dashboard/analytics placeholder 페이지 생성 — "준비 중" UI

## 테스트 확장
- [x] 대시보드 summary API 테스트 — 3개 통과
- [ ] sync API 테스트 (KIS 계좌 mock)
- [ ] 대시보드 컴포넌트 테스트 (에러 UI, 스켈레톤 렌더링)
- [ ] 포트폴리오 상세 페이지 컴포넌트 테스트

## UI 완성도
- [ ] 포트폴리오 상세 페이지 — shadcn/ui Input, Button 교체 (종목 추가/수정 폼)
- [ ] 설정 페이지 — shadcn/ui Input, Button 교체 (KIS 자격증명 폼)
- [ ] StockSearchDialog — shadcn/ui Dialog로 교체
- [ ] 포트폴리오 생성 모달 — shadcn/ui Dialog로 교체
