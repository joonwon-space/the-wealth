---
description: 프로젝트 분석 문서와 코드 상태를 리서치하여 tasks.md(현재 작업)와 todo.md(미래 작업)를 갱신한다.
---

# Discover Tasks

프로젝트의 현재 상태를 분석하고, 해야 할 일을 발견하여 작업 목록을 갱신한다.

## 문서 역할

| 문서 | 역할 | 내용 |
|------|------|------|
| `docs/plan/tasks.md` | **현재 할 일** | 지금 바로 실행 가능한 작업. `/auto-task`, `/next-task`가 여기서 읽는다 |
| `docs/plan/todo.md` | **미래 할 일** | 중장기 백로그, 로드맵. 당장 하지 않지만 언젠가 해야 할 일 |

## 실행 순서

### 1. 분석 문서 읽기

아래 문서를 모두 읽는다:
- `docs/analysis/project-overview.md` — 현재 프로젝트 구조, 기술 스택, API 목록
- `docs/analysis/project-analysis.md` — 강점, 약점, 리스크, 개선 기회, 성능 병목
- `docs/plan/tasks.md` — 현재 작업 목록
- `docs/plan/todo.md` — 미래 작업 백로그
- `docs/plan/manual-tasks.md` — 수동 처리 항목

### 2. 코드베이스 리서치

실제 코드 상태를 조사하여 분석 문서와의 차이를 파악한다:
- **새로 추가된 파일/기능** 중 문서에 반영 안 된 것
- **버그 또는 TODO 주석** (`grep -r "TODO\|FIXME\|HACK\|XXX"`)
- **빌드/린트 에러** (`npm run build`, `ruff check .`)
- **테스트 커버리지 현황** (있다면)
- **의존성 보안 취약점** (`npm audit`, `pip audit`)
- **git log** — 최근 변경사항 중 후속 작업이 필요한 것

### 3. 분석 문서 업데이트

리서치 결과를 바탕으로:
- `docs/analysis/project-overview.md` — 새로운 API, 모델, 페이지, 서비스 반영
- `docs/analysis/project-analysis.md` — 완성도 상태, 강점/약점, 리스크 갱신. 해결된 약점 제거, 새 리스크 추가

### 4. 작업 목록 갱신

발견된 작업을 적절한 문서에 분류한다:

**`docs/plan/tasks.md` (현재 할 일)에 넣는 기준:**
- 버그 수정
- 빌드/린트 에러 수정
- 보안 취약점 패치
- 기존 기능의 품질 개선 (에러 핸들링, 타입 수정 등)
- 테스트 추가
- 사용자가 직접 요청한 기능

**`docs/plan/todo.md` (미래 할 일)에 넣는 기준:**
- 새로운 기능 아이디어
- 대규모 리팩토링
- 배포/인프라 구축
- 성능 최적화
- 장기 로드맵 항목

### 5. tasks.md 작성 규칙

```markdown
# THE WEALTH — Tasks (현재 작업)

## 이 문서의 용도
`/auto-task`와 `/next-task`가 이 문서에서 작업을 읽는다.
각 항목은 하나의 커밋 단위로 완료 가능한 크기여야 한다.

## 현재 작업
- [ ] 작업 1 — 구체적이고 실행 가능한 설명
- [ ] 작업 2
...
```

- 각 항목은 **구체적**이어야 한다 ("UI 개선" ✗, "대시보드 로딩 스켈레톤 추가" ✓)
- 하나의 커밋으로 완료 가능한 크기로 분해한다
- 완료된 항목(`[x]`)은 주기적으로 정리한다 (10개 이상 쌓이면 제거)

### 6. todo.md 작성 규칙

```markdown
# THE WEALTH — TODO (미래 로드맵)

## Milestone N: 제목
- [ ] 항목 1
- [ ] 항목 2
...
```

- 마일스톤 단위로 그룹핑
- 완료된 마일스톤은 접어두거나 별도 섹션으로 이동
- tasks.md로 승격할 준비가 된 항목은 표시해둔다

### 7. 커밋

변경된 문서를 커밋한다:
```
git add docs/
git commit -m "docs: update project analysis and task lists"
```

### 8. 결과 출력

```
📋 리서치 완료!

분석 문서 업데이트:
- project-overview.md: [변경됨/변경없음]
- project-analysis.md: [변경됨/변경없음]

작업 목록:
- tasks.md: N개 현재 작업 (신규 M개 추가)
- todo.md: N개 미래 작업 (신규 M개 추가)
- manual-tasks.md: N개 수동 작업

다음 단계: `/auto-task` 또는 `/next-task`로 현재 작업을 실행하세요.
```
