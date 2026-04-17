# Design System

shadcn/ui 설정, Tailwind v4 토큰, 한국 증시 색 규칙, 컴포넌트 작성 가이드.

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

- **style**: `base-nova` — shadcn/ui의 새로운 스타일 (rounded corners, cleaner typography)
- **baseColor**: `neutral` — 회색 기반 neutral 팔레트
- **cssVariables**: `true` — 모든 색상을 CSS 변수(`--color-*`)로 정의
- **iconLibrary**: `lucide` — `lucide-react` 아이콘 사용

새 컴포넌트 추가:
```bash
cd frontend && npx shadcn@latest add <component>
# 예: npx shadcn@latest add dropdown-menu
```

현재 설치된 UI 컴포넌트 (`frontend/src/components/ui/`):
`alert-dialog`, `button`, `card`, `dialog`, `input`, `skeleton`, `sonner`, `table`, `tabs`

---

## 2. Tailwind v4 Theme Token 맵

`frontend/src/app/globals.css`의 `@theme inline` 블록에서 CSS 변수를 Tailwind 유틸리티 클래스에 매핑:

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
  /* 한국 증시 전용 */
  --color-rise: var(--rise);
  --color-fall: var(--fall);
  /* 차트 색상 */
  --color-chart-1: var(--chart-1);  /* dodger blue #1e90ff */
  --color-chart-2: var(--chart-2);
  ...
}
```

Tailwind에서 사용: `text-primary`, `bg-muted`, `text-muted-foreground`, `border-border` 등.

### 라이트/다크 모드 값

| 토큰 | 라이트 | 다크 |
|------|--------|------|
| `--background` | `oklch(0.97 0.005 250)` | `oklch(0.12 0.01 250)` |
| `--foreground` | `oklch(0.15 0.01 250)` | `oklch(0.95 0.005 250)` |
| `--primary` | dodger blue (`#1e90ff` 계열) | 동일 계열 다크 조정 |
| `--muted` | `oklch(0.94 0.01 250)` | 어두운 중립 |
| `--rise` | `#E31F26` (밝은 빨강) | `#FF4D4F` (WCAG AA 대응) |
| `--fall` | `#1A56DB` (진한 파랑) | `#4B8EF5` (WCAG AA 대응) |

---

## 3. 한국 증시 색 규칙

**한국 주식 시장 컨벤션** (더리치 앱 참조):

| 상황 | 색상 | 클래스 |
|------|------|--------|
| 상승 (상승율 > 0) | 빨간색 `--rise` | `text-rise` / `bg-rise` |
| 하락 (상승율 < 0) | 파란색 `--fall` | `text-fall` / `bg-fall` |
| 보합 (0) | 회색 | `text-muted-foreground` |

`globals.css:196-206`에 유틸리티 클래스 정의:
```css
.text-rise { color: var(--rise); }
.text-fall { color: var(--fall); }
.bg-rise { background-color: var(--rise); }
.bg-fall { background-color: var(--fall); }
```

**라이트 모드**: `--rise: #E31F26` (밝은 빨강), `--fall: #1A56DB` (진한 파랑)
**다크 모드**: `--rise: #FF4D4F` (더 밝은 빨강), `--fall: #4B8EF5` (더 밝은 파랑) — WCAG AA 기준

사용 예:
```tsx
// 등락률 표시
const colorClass = changeRate > 0 ? "text-rise" : changeRate < 0 ? "text-fall" : "text-muted-foreground";
<span className={colorClass}>{changeRate > 0 ? "+" : ""}{changeRate.toFixed(2)}%</span>
```

---

## 4. cn() Helper 사용 규칙

`frontend/src/lib/utils.ts`:
```typescript
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- `clsx` — 조건부 클래스 결합
- `twMerge` — Tailwind 충돌 해소 (예: `p-2` + `p-4` → `p-4`만 적용)

사용 패턴:
```tsx
import { cn } from "@/lib/utils";

// 기본 + 조건부
<div className={cn("rounded border p-4", isActive && "border-primary", className)} />

// variant별 스타일
<button className={cn(
  "px-4 py-2 rounded text-sm",
  variant === "primary" && "bg-primary text-primary-foreground",
  variant === "ghost" && "bg-transparent hover:bg-accent",
)} />
```

**규칙**:
- 외부에서 `className` prop을 받는 컴포넌트는 항상 `cn(defaultClasses, className)` 패턴
- 인라인 `style` 대신 Tailwind 유틸리티 사용
- 중복 클래스 주의 — `twMerge`가 해소하지만 명확성을 위해 피하기

---

## 5. 컴포넌트 작성 체크리스트

새 컴포넌트 작성 시:

```
[ ] Props 인터페이스 정의 (interface ComponentProps)
[ ] 반환 타입 명시 (JSX.Element 또는 React.ReactNode)
[ ] className prop 수용 (cn() 패턴)
[ ] 에러/로딩/빈 상태 처리
[ ] 접근성: ARIA role, aria-label, keyboard navigation
[ ] 한국어 레이블 — UI 텍스트는 한국어
```

### forwardRef 필요 케이스

외부에서 DOM ref를 접근해야 하는 경우:
- shadcn/ui 컴포넌트 내부에 사용하는 Trigger/Target 요소
- Focus 제어가 필요한 input, button

```typescript
import { forwardRef } from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost";
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", className, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn("px-4 py-2", variant === "ghost" && "bg-transparent", className)}
        {...props}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
```

일반적인 leaf 컴포넌트는 `forwardRef` 불필요.

---

## 6. 다크 모드 (next-themes)

`frontend/src/app/layout.tsx`:
```tsx
import { ThemeProvider } from "@/components/ThemeProvider";

// ThemeProvider로 앱 전체 감싸기
<ThemeProvider attribute="class" defaultTheme="system">
  {children}
</ThemeProvider>
```

`globals.css:5`:
```css
@custom-variant dark (&:is(.dark *));
```

Tailwind에서 다크 모드 클래스: `dark:bg-gray-900`, `dark:text-white` 등.

토글 UI (`settings/AccountSection.tsx:341`):
```tsx
const { theme, setTheme } = useTheme();
<button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
  {theme === "dark" ? <Sun /> : <Moon />}
</button>
```

다크 모드 작성 팁:
- 기본 CSS 변수 토큰(`text-foreground`, `bg-background`)은 자동으로 다크 조정됨
- Tailwind 고정 색상(`red-500`, `blue-500`)을 직접 쓰면 다크 모드에서 가독성 문제 발생
- 한국 증시 색은 `--rise`, `--fall` 변수를 사용하면 라이트/다크 자동 전환

---

## 7. 차트 색상 팔레트

Recharts 컴포넌트에서 사용하는 8색 팔레트 (`globals.css:85-92`):

| 변수 | 색상 | 용도 |
|------|------|------|
| `--chart-1` | `#1e90ff` (dodger blue) | 주 차트 색 (포트폴리오 히스토리) |
| `--chart-2` | `#00ff00` (neon green, 라이트) / green (다크) | 보조 |
| `--chart-3` | amber `#F59E0B` | 경고/황색 계열 |
| `--chart-4` | rose `#F43F5E` | 위험/음수 계열 |
| `--chart-5` | violet `#8B5CF6` | 섹터 차트 |
| `--chart-6` | cyan `#06B6D4` | 섹터 차트 |
| `--chart-7` | orange `#F97316` | 섹터 차트 |
| `--chart-8` | green `#22C55E` | 양수/수익 계열 |

Recharts에서 CSS 변수 참조:
```tsx
<Line stroke="var(--color-chart-1)" />
<Cell fill={`var(--color-chart-${index + 1})`} />
```

---

## Related

- [`docs/architecture/frontend-guide.md`](./frontend-guide.md) — 페이지 라우팅, 컴포넌트 트리, 공유 훅
- [`docs/architecture/overview.md`](./overview.md) — 기술 스택 요약
