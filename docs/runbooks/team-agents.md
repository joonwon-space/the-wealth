# Team Agents 가이드

## 개요

Team Agent는 여러 전문 에이전트가 병렬로 분석한 뒤, Opus 모델이 결과를 종합하는 멀티 에이전트 시스템이다.

```
[Sub-Agent 1 (Sonnet)] ──┐
[Sub-Agent 2 (Sonnet)] ──┤
[Sub-Agent 3 (Sonnet)] ──┼──→ [Synthesizer (Opus)] ──→ 최종 산출물
[Sub-Agent 4 (Sonnet)] ──┤
[Sub-Agent 5 (Sonnet)] ──┘
```

## Team Agent 목록

| 명령어 | 목적 | 사용 시점 | Sub-Agents |
|--------|------|-----------|------------|
| `/team-discover` | 프로젝트 상태 진단 | 마일스톤 완료 후, 방향 재정립 | 5명 (tech-debt, ux-gap, security, perf, product) |
| `/team-feature` | 새 기능 설계 | 기능 구현 착수 전 | 4명 (product, ux, backend, frontend) |
| `/team-review` | 코드 리뷰 | 큰 PR, 핵심 모듈 변경 시 | 4명 (correctness, security, performance, maintainability) |
| `/team-release` | 릴리스 검증 | 배포/머지 전 최종 체크 | 4명 (build, test, migration, api-contract) |
| `/team-debug` | 버그 진단 | 원인 불명의 복합 버그 | 4명 (error-trace, data-flow, regression, env-config) |

## 각 Team Agent 상세

### `/team-discover` — 프로젝트 상태 진단

**질문**: "지금 프로젝트 상태가 어떤가?"

| Sub-Agent | 분석 관점 |
|-----------|----------|
| tech-debt-analyst | 코드 품질, 의존성, 타입 안전성 |
| ux-gap-analyst | UX 갭, 접근성, 반응형, 에러 상태 |
| security-posture-analyst | OWASP, 인증/인가, 암호화, 취약점 |
| perf-bottleneck-analyst | 번들, API, DB, 캐싱 성능 |
| product-strategy-analyst | 로드맵, 기능 갭, 우선순위 |
| **strategy-synthesizer** | **전체 종합 → 우선순위 태스크 + 로드맵** |

**산출물**: `docs/reviews/team-synthesis.md`, `docs/plan/tasks.md` 업데이트

---

### `/team-feature` — 새 기능 설계

**질문**: "이 기능을 어떻게 만들까?"

| Sub-Agent | 설계 관점 |
|-----------|----------|
| product-analyst | 사용자 니즈, MVP 범위, 경쟁 분석 |
| ux-designer | UI 구조, 사용자 플로우, 접근성 |
| backend-architect | API, DB 스키마, KIS API 연동 |
| frontend-architect | 컴포넌트, 상태관리, 데이터 페칭 |
| **feature-synthesizer** | **통합 PRD + 구현 태스크 리스트** |

**산출물**: `docs/reviews/feature/prd.md`

**사용법**: `/team-feature 환차익 추적 기능 추가`

---

### `/team-review` — 코드 리뷰

**질문**: "이 코드 변경이 안전한가?"

| Sub-Agent | 리뷰 관점 |
|-----------|----------|
| correctness-reviewer | 로직 오류, 엣지 케이스, 데이터 무결성 |
| security-reviewer | 취약점, 인증, 인젝션, 데이터 노출 |
| performance-reviewer | N+1 쿼리, 리렌더, 메모리 누수 |
| maintainability-reviewer | 가독성, 컨벤션, 아키텍처 |
| **review-synthesizer** | **통합 판정 (APPROVE / REQUEST CHANGES / BLOCK)** |

**산출물**: `docs/reviews/review/summary.md`

**판정 기준**:
- 아무 reviewer가 "block" → 전체 **BLOCK**
- 아무 reviewer가 "request-changes" → 전체 **REQUEST CHANGES**
- 모두 "approve" → 전체 **APPROVE**

---

### `/team-release` — 릴리스 검증

**질문**: "배포해도 되는가?"

| Sub-Agent | 검증 관점 |
|-----------|----------|
| build-validator | 프론트/백엔드 빌드, 린트, 번들 크기 |
| test-runner | 전체 테스트, 커버리지 분석 |
| migration-checker | Alembic 마이그레이션 안전성, 되돌림 가능성 |
| api-contract-checker | Breaking change, 프론트-백엔드 계약 일치 |
| **release-synthesizer** | **GO / CONDITIONAL / NO-GO 판정 + 릴리스 노트** |

**산출물**: `docs/reviews/release/summary.md`

**판정 기준**:
- 아무 validator가 "fail" → **NO-GO**
- 2개 이상 "warn" → **CONDITIONAL**
- 1개 "warn", 나머지 "pass" → **GO** (주의사항 포함)
- 모두 "pass" → **GO**

---

### `/team-debug` — 버그 진단

**질문**: "이 버그의 근본 원인이 뭔가?"

| Sub-Agent | 진단 관점 |
|-----------|----------|
| error-trace-analyst | 에러 발원지, 스택트레이스, 호출 체인 |
| data-flow-analyst | 데이터 흐름 추적, 변환 이슈 |
| regression-analyst | git 히스토리, 의심 커밋 |
| env-config-analyst | 환경변수, KIS API, Redis, DB 설정 |
| **debug-synthesizer** | **근본 원인 + 수정 계획** |

**산출물**: `docs/reviews/debug/diagnosis.md`

**사용법**: `/team-debug 포트폴리오 수익률이 NaN으로 표시됨`

## 효율적인 워크플로우

### 기능 개발 사이클 (정석 순서)

```
/team-discover        ← 1. 마일스톤 끝, "다음 뭘 할까?"
       ↓
/team-feature         ← 2. "이 기능을 어떻게 만들까?" (PRD 생성)
       ↓
/plan → /tdd          ← 3. PRD 기반 구현 (테스트 먼저)
       ↓
/team-review          ← 4. 구현 완료 후 코드 리뷰
       ↓
/team-release         ← 5. 머지/배포 전 최종 검증
```

### 버그 수정 사이클

```
/team-debug           ← 1. 근본 원인 진단
       ↓
/tdd                  ← 2. 회귀 테스트 작성 + 수정 구현
       ↓
/team-review          ← 3. 수정 코드 리뷰
       ↓
/team-release         ← 4. 배포 전 검증
```

### team-discover vs team-feature 차이

| | `/team-discover` | `/team-feature` |
|---|---|---|
| 비유 | 건강검진 | 건축 설계 |
| 질문 | "프로젝트 상태가 어떤가?" | "이 기능을 어떻게 만들까?" |
| 입력 | 코드베이스 전체 | 특정 기능 요구사항 |
| 산출물 | 우선순위 태스크 + 로드맵 | PRD + 태스크 리스트 |
| 타이밍 | 마일스톤 완료 후 | 기능 구현 착수 전 |

자연스러운 흐름: discover가 "뭘 할지" 정하고, feature가 "어떻게 할지" 설계한다.

## 언제 team-agent를 쓰고, 언제 안 쓰는가

### team-agent가 필요한 상황

- 새 기능 설계가 필요할 때 → `/team-feature`
- 코드 변경량이 많을 때 (10+ 파일) → `/team-review`
- 배포 전 안전성 확인 → `/team-release`
- 원인 불명의 복합 버그 → `/team-debug`
- 방향 재정립이 필요할 때 → `/team-discover`

### 단일 agent로 충분한 상황

| 상황 | 사용할 명령어 |
|------|-------------|
| 작은 버그 수정 | `/tdd` → `/code-review` |
| 단순 리팩토링 | `/code-review` |
| 빌드 에러 | `/build-fix` |
| 문서 업데이트 | `/update-docs` |
| 보안 점검 (특정 파일) | `/code-review` (security-reviewer) |

**원칙**: team-agent는 "복잡한 상황"에서만 사용한다. 단순 작업에는 단일 agent가 더 빠르고 효율적이다.

## 파일 구조

```
.claude/agents/
├── team-discover.md          ← 오케스트레이터
├── team-feature.md
├── team-review.md
├── team-release.md
├── team-debug.md
└── team/
    ├── tech-debt.md           ← discover sub-agents
    ├── ux-gap.md
    ├── security-posture.md
    ├── perf-bottleneck.md
    ├── product-strategy.md
    ├── strategy-synthesizer.md
    ├── feature/               ← feature sub-agents
    │   ├── product-analyst.md
    │   ├── ux-designer.md
    │   ├── backend-architect.md
    │   ├── frontend-architect.md
    │   └── feature-synthesizer.md
    ├── review/                ← review sub-agents
    │   ├── correctness-reviewer.md
    │   ├── security-reviewer.md
    │   ├── performance-reviewer.md
    │   ├── maintainability-reviewer.md
    │   └── review-synthesizer.md
    ├── release/               ← release sub-agents
    │   ├── build-validator.md
    │   ├── test-runner.md
    │   ├── migration-checker.md
    │   ├── api-contract-checker.md
    │   └── release-synthesizer.md
    └── debug/                 ← debug sub-agents
        ├── error-trace-analyst.md
        ├── data-flow-analyst.md
        ├── regression-analyst.md
        ├── env-config-analyst.md
        └── debug-synthesizer.md

.claude/commands/
├── team-discover.md           ← slash commands
├── team-feature.md
├── team-review.md
├── team-release.md
└── team-debug.md
```
