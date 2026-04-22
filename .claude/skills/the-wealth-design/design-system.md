# Design System — Token & Component Reference

이 파일은 **프로덕션 코드 기준 레퍼런스**입니다. shadcn/ui 설정, Tailwind v4 토큰 맵, 한국 증시 색 규칙, `cn()` helper, forwardRef, 다크 모드 관례를 정리합니다.

---

## 1. shadcn/ui 설정

`frontend/components.json`:

```json
{
  "style": "base-nova",
  "tailwind": {
    "baseColor": "neutral",
    "cssVariables": true,
    "css": "src/app/globals.css"
  },
  "iconLibrary": "lucide",
  "aliases": {
    "ui": "@/components/ui",
    "utils": "@/lib/utils"
  }
}
```

- **style**: `base-nova` (shadcn 의 새로운 둥근/클린 스타일)
- **baseColor**: `neutral`
- **cssVariables**: `true` — 색상을 CSS 변수(`--color-*`)로 정의
- **iconLibrary**: `lucide` (`lucide-react`)

컴포넌트 추가: `cd frontend && npx shadcn@latest add <component>`

설치된 UI 컴포넌트 (`frontend/src/components/ui/`): `alert-dialog`, `button`, `card`, `dialog`, `input`, `skeleton`, `sonner`, `table`, `tabs`.

---

## 2. Tailwind v4 Theme Token 맵

`frontend/src/app/globals.css` 의 `@theme inline` 블록이 CSS 변수를 Tailwind 유틸리티에 매핑:

```css
@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-border: var(--border);
  --color-card: var(--card);
  --color-destructive: var(--destructive);
  /* Korean market */
  --color-rise: var(--rise);
  --color-fall: var(--fall);
  /* charts */
  --color-chart-1: var(--chart-1);
  /* ...chart-2 ~ 8 */
}
```

Tailwind 에서: `text-primary`, `bg-muted`, `text-muted-foreground`, `border-border` 등.

### 라이트/다크 값 요약

| 토큰 | 라이트 | 다크 |
|---|---|---|
| `--background` | `oklch(0.97 0.005 250)` | `oklch(0.12 0.01 250)` |
| `--foreground` | `oklch(0.15 0.01 250)` | `oklch(0.95 0.005 250)` |
| `--primary` | `#1e90ff` | `#1e90ff` |
| `--muted` | `oklch(0.94 0.01 250)` | `oklch(0.20 0.01 250)` |
| `--rise` | `#E31F26` | `#FF4D4F` |
| `--fall` | `#1A56DB` | `#4B8EF5` |

---

## 3. 한국 증시 색 규칙

자세한 내용은 [`korean-market-colors.md`](./korean-market-colors.md) 참조.

| 상황 | 색 | 클래스 |
|---|---|---|
| 상승 (> 0) | 빨강 `--rise` | `text-rise` / `bg-rise` |
| 하락 (< 0) | 파랑 `--fall` | `text-fall` / `bg-fall` |
| 보합 (= 0) | 회색 | `text-muted-foreground` |

```tsx
const colorClass =
  changeRate > 0 ? "text-rise" :
  changeRate < 0 ? "text-fall" :
  "text-muted-foreground";

<span className={colorClass}>
  {changeRate > 0 ? "+" : ""}{changeRate.toFixed(2)}%
</span>
```

---

## 4. cn() Helper

`frontend/src/lib/utils.ts`:

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- `clsx` — 조건부 클래스 결합
- `twMerge` — Tailwind 충돌 해소 (`p-2` + `p-4` → `p-4`)

### 사용 패턴

```tsx
import { cn } from "@/lib/utils";

<div className={cn("rounded border p-4", isActive && "border-primary", className)} />

<button className={cn(
  "px-4 py-2 rounded text-sm",
  variant === "primary" && "bg-primary text-primary-foreground",
  variant === "ghost" && "bg-transparent hover:bg-accent",
)} />
```

**규칙**:
- 외부에서 `className` prop 을 받는 컴포넌트는 항상 `cn(defaultClasses, className)`
- 인라인 `style` 대신 Tailwind 유틸리티 사용
- 중복 클래스는 `twMerge` 가 해소하지만 가독성을 위해 피하기

---

## 5. 다크 모드 (next-themes)

`frontend/src/app/layout.tsx`:

```tsx
import { ThemeProvider } from "@/components/ThemeProvider";

<ThemeProvider attribute="class" defaultTheme="system">
  {children}
</ThemeProvider>
```

`globals.css` 상단:

```css
@custom-variant dark (&:is(.dark *));
```

토글:

```tsx
const { theme, setTheme } = useTheme();
<button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
  {theme === "dark" ? <Sun /> : <Moon />}
</button>
```

**작성 팁**:
- 기본 CSS 변수 토큰(`text-foreground`, `bg-background`)은 자동 전환
- Tailwind 고정 색상(`red-500`, `blue-500`) 직접 사용 금지 — 다크 모드 가독성 깨짐
- 한국 증시 색은 `text-rise`, `text-fall` 변수 사용 → 라이트/다크 자동

---

## 6. 차트 색상 팔레트 (Recharts / lightweight-charts)

| 변수 | 색 | 용도 |
|---|---|---|
| `--chart-1` | `#1e90ff` | 주 차트 (포트폴리오 히스토리) |
| `--chart-2` | `#00ff00` (라이트) / green (다크) | 보조 |
| `--chart-3` | `#F59E0B` amber | 경고/황색 계열 |
| `--chart-4` | `#F43F5E` rose | 위험 / 음수 |
| `--chart-5` | `#8B5CF6` violet | 섹터 |
| `--chart-6` | `#06B6D4` cyan | 섹터 |
| `--chart-7` | `#F97316` orange | 섹터 |
| `--chart-8` | `#22C55E` green | 양수/수익 |

```tsx
<Line stroke="var(--color-chart-1)" />
<Cell fill={`var(--color-chart-${index + 1})`} />
```

**캔들스틱 차트** (lightweight-charts) 의 up/down 색은 반드시 `--rise`/`--fall` 을 사용.

---

## Related

- [`README.md`](./README.md) — 브랜드, 콘텐츠, 비주얼 파운데이션
- [`korean-market-colors.md`](./korean-market-colors.md) — 한국 증시 색 상세
- [`component-checklist.md`](./component-checklist.md) — 새 컴포넌트 작성 체크리스트
- [`colors_and_type.css`](./colors_and_type.css) — 드롭인 토큰 CSS
