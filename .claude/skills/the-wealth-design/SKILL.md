---
name: the-wealth-design
description: Use this skill to generate well-branded interfaces and assets for The Wealth (한국투자증권 OpenAPI 기반 개인 자산관리 대시보드), either for production (Next.js 16 + React 19 + Tailwind v4 + shadcn/ui) or throwaway prototypes/mocks/slides. Contains essential design guidelines, colors, type, Korean stock-market color conventions, and UI kit components for prototyping dashboards, portfolio views, charts, and mobile app screens.
user-invocable: true
---

# The Wealth — Design Skill

This skill packages the design system for **The Wealth**, a personal wealth-management dashboard built on the Korea Investment & Securities (한국투자증권, KIS) OpenAPI. It covers a **web dashboard** (Next.js + shadcn/ui) and a **mobile app**.

## How to use this skill

1. **Read `README.md` first** — it has brand context, content/voice rules, and visual foundations. Everything else in the skill supports what's in that file.
2. **Then skim `design-system.md`** — the canonical token map, Tailwind v4 `@theme inline` setup, `cn()` helper rules, forwardRef rules, and dark-mode setup.
3. **Then check `korean-market-colors.md`** — **critical**: 한국 증시에서는 상승=빨강, 하락=파랑 입니다 (global convention과 반대). Never default to red=down / green=up here.
4. **Explore `assets/` and `fonts/`** as needed.
5. **UI kits** live in `ui_kits/<product>/` — copy components out, don't reinvent.

## When invoked without other guidance

Ask the user what they want to build or design. Good opening questions:

- 어떤 서피스? (웹 대시보드 / 모바일 앱 / 슬라이드 / 마케팅 자료)
- 프로덕션 코드인가요, 목업/프로토타입인가요?
- 다크 모드 포함? (기본: 시스템 따라감)
- 어떤 화면/컴포넌트? (포트폴리오, 관심종목, 차트, 알림, 설정 등)

Then act as an expert designer and ship HTML artifacts (for mocks, slides, throwaways) or production code (Next.js + Tailwind v4 + shadcn/ui conventions from `design-system.md`).

## Output guidance

- **Throwaway / mock / slide / prototype** → static HTML artifact, copy assets out of this skill directory.
- **Production code** → follow `design-system.md` exactly: shadcn/ui `base-nova` style, `neutral` base, CSS variables, `lucide-react` icons, `cn()` helper, Tailwind v4 `@theme inline` mapping, Korean market color convention.
- **Slides / decks** → use the visual foundations and real brand colors; never fabricate logos or a different palette.

## Non-negotiables

- 한국어 UI 레이블. Copy is Korean by default.
- 한국 증시 color convention: `text-rise` (red) for up, `text-fall` (blue) for down, `text-muted-foreground` for 보합. See `korean-market-colors.md`.
- Icon library: **Lucide** (`lucide-react`). No emoji. No hand-drawn SVG for UI chrome.
- Base color: `neutral` (not `slate`, not `zinc`). shadcn style: `base-nova`.
- Dark mode must be supported — use CSS variable tokens, never hard-coded Tailwind colors like `red-500`.

## File manifest

```
.
├── SKILL.md                      # this file
├── README.md                     # brand, content, visual foundations
├── design-system.md              # shadcn/Tailwind/token reference
├── korean-market-colors.md       # 한국 증시 색 규칙
├── component-checklist.md        # 새 컴포넌트 작성 체크리스트
├── colors_and_type.css           # drop-in CSS with all tokens + typographic vars
├── assets/                       # logos, icons (copy out; don't redraw)
├── fonts/                        # webfonts (none bundled yet — uses system stack)
├── preview/                      # Design System tab cards
└── ui_kits/
    ├── web/                      # Next.js dashboard UI kit (index.html + components)
    └── mobile/                   # Mobile app UI kit
```

UI kits and preview cards are populated progressively — if a referenced file is missing, it has not been built yet; ask the user whether to generate it.
