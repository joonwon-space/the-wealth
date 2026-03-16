# THE WEALTH — Tasks

Current work items. Read by `/auto-task` and `/next-task`.
Each item should be completable in a single commit.

---

Discovered by `/discover-tasks` — security fixes + DX improvements.

- [x] `filelock` 3.19.1 → 3.25.2 업그레이드 (GHSA-w853-jp5j-5j7f, GHSA-qmgc-5h2g-mvrw)
- [x] `python-jose` → `PyJWT` 마이그레이션 (`ecdsa` 취약점 GHSA-wj6h-64fc-37mp 해소)
- [x] `passlib` → `bcrypt` 직접 사용으로 마이그레이션 (Python 3.13 `crypt` 모듈 제거 대비)
- [x] `backend/.env.example`에 `CORS_ORIGINS` 항목 추가
- [x] KIS 자격증명 등록 시 API 연결 테스트 엔드포인트 (B/E: `/users/kis-accounts/{id}/test`)
- [ ] KIS 자격증명 연결 테스트 UI ("연결 테스트" 버튼 + 성공/실패 피드백)
