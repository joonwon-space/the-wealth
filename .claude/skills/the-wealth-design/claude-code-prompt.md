# Claude Code Handoff Prompt

> Use this as the single opening message when asking Claude Code to implement the Phase 3 redesign in the production codebase.

---

당신은 The Wealth 프로덕션 코드베이스에서 일하는 시니어 풀스택 개발자입니다. 아래 5개 문서를 이 순서대로 완독하고 작업을 시작합니다:

1. `README.md` — 브랜드, 보이스, 비주얼 파운데이션
2. `design-system.md` — 토큰/Tailwind v4/shadcn 설정
3. `audit.md` — 현재 데이터 인벤토리 (Portfolio/Holding/Transaction/Order/Alert 스키마)
4. `redesign-spec.md` — **개편 명세 (당신이 실행할 계획)**
5. `redesign.html` — 시각 레퍼런스 (모바일 5화면 + 웹 홈 + 플로우)

## 작업 범위

`redesign-spec.md` 의 **§10 마이그레이션 순서**를 그대로 따릅니다. 한 번에 **한 단계**만 구현·PR. 끝나면 체크리스트 업데이트 후 다음 단계.

## 비협상 규칙

- **한국어 UI 레이블 기본**. 영어는 약어/고유명사만.
- **한국 증시 색**: `text-rise`(빨강)=상승, `text-fall`(파랑)=하락. 반대로 쓰지 않음. `korean-market-colors.md` 참조.
- **Lucide 아이콘만**. 이모지·커스텀 SVG 금지 (로고 제외).
- **shadcn base**: `base-nova`, `neutral`. `slate`/`zinc` 금지.
- **cn() helper** 로 클래스 합성. 직접 string concat 금지.
- **Tabular nums** 로 모든 금액·퍼센트 표기.
- **Dark mode** 동시 지원. 하드코딩 Tailwind 색(`red-500` 등) 금지 — CSS 변수 토큰만.
- 새 컴포넌트는 `component-checklist.md` 체크리스트 통과.

## 작업 시작 전 확인

시작하기 전에 아래 사항을 확정해주세요. 불명확하면 질문:

1. **DB 마이그레이션 도구**: Alembic 사용 중인가? 마이그레이션 파일 생성 규칙.
2. **배당 데이터 소스**: KIS API가 배당 조회를 지원하는가? 아니면 DART API / 수동 업로드?
3. **기존 `/dashboard/analytics` 제거 범위**: 명세처럼 개별 탭을 전부 분산시킬지, 일부 유지할지.
4. **Onboarding 우선순위**: §10 단계 9인데, 신규 유저 유입 시점과 겹치면 먼저 당길지.
5. **모드 토글 SSR**: 쿠키 기반(명세) vs localStorage only. Next.js 16 RSC 고려.

## 출력 형식

각 단계마다:
- 변경 파일 목록
- DB 마이그레이션 (있으면)
- 새 API 엔드포인트 (있으면) + OpenAPI/Zod 스키마
- 스크린샷 또는 Storybook 링크 (컴포넌트 단계)
- 테스트 — Playwright e2e 1개, 중요 훅은 vitest 유닛
- CHANGELOG 엔트리

## 첫 번째 할 일

§10 단계 1 — **신규 shadcn 컴포넌트 7개 추가**:
- `ModeToggle` · `HeroValue` · `ProgressRing` · `Donut` · `HeatCell` · `TaskCard` · `StreamCard` · `SectorBar` · `RangeIndicator`

레퍼런스는 `redesign.html` 의 `redesign/primitives.jsx` — 로직은 거의 그대로, React 19 + shadcn 컨벤션으로 바꿔 `components/` 아래 배치. 각 컴포넌트 Storybook 스토리 1-2개씩.

시작해주세요.
