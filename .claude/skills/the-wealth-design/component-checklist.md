# Component Checklist — 새 컴포넌트 작성 체크리스트

새 컴포넌트를 만들 때 아래 항목을 체크하세요. 프로덕션 코드 기준이지만 목업/프로토타입에서도 일관성을 위해 대부분 적용합니다.

---

## 기본

- [ ] **Props 인터페이스** 정의 — `interface ComponentNameProps`
- [ ] **반환 타입** 명시 — `JSX.Element` 또는 `React.ReactNode`
- [ ] **`className` prop** 수용 — 항상 `cn(defaultClasses, className)` 패턴
- [ ] **`...props` spread** — 필요한 경우 HTML attrs 전달 (`React.HTMLAttributes<HTMLDivElement>` 등 확장)
- [ ] 한국어 UI 레이블

## 상태 처리

- [ ] **Loading** — `Skeleton` 컴포넌트 사용 (shadcn). 스피너는 실시간 새로고침 한정.
- [ ] **Empty** — 한국어 간결 메시지. "데이터가 없습니다." 정도. 과장된 일러스트 지양.
- [ ] **Error** — `--destructive` 톤, 재시도 버튼 제공.
- [ ] **Disabled** — `disabled` prop 전달 시 `opacity-50 pointer-events-none`.

## 접근성

- [ ] `role`, `aria-label`, `aria-describedby` 적절히 사용
- [ ] Keyboard navigation — Tab, Enter, Esc, 화살표 (메뉴/탭 한정)
- [ ] Focus ring — `focus-visible:ring-2 ring-ring ring-offset-2`
- [ ] 색만으로 정보 전달 금지 — 한국 증시 상승/하락에도 부호/아이콘 병기

## 다크 모드

- [ ] CSS 토큰(`bg-background`, `text-foreground`, `border-border`) 사용. `bg-white`, `text-gray-900` 같은 고정 색 금지.
- [ ] 한국 증시 색은 `text-rise`, `text-fall` (토큰이 다크 모드 값을 자동 스왑)
- [ ] 다크 모드에서 직접 확인

## 숫자 표기 (금융 UI 특화)

- [ ] `font-variant-numeric: tabular-nums` — Tailwind `tabular-nums` 클래스
- [ ] 금액: `₩` 접두 또는 "원" 접미, 천 단위 콤마
- [ ] 수익률: 소수점 2자리, 양수는 `+` 명시
- [ ] 등락 색: `text-rise` / `text-fall` / `text-muted-foreground` 삼분
- [ ] 큰 숫자는 축약 고려 — `₩42.2M`, `1.25억원` 등 단, 테이블 정렬에는 풀 숫자 유지

## forwardRef 필요 여부

- **필요**: 외부에서 DOM ref 접근 — shadcn Trigger/Target, focus 제어 input/button, tooltip anchor
- **불필요**: 일반 leaf 컴포넌트 (대부분)

```tsx
import { forwardRef } from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost";
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", className, children, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "px-4 py-2 rounded-md text-sm",
        variant === "primary" && "bg-primary text-primary-foreground",
        variant === "ghost" && "bg-transparent hover:bg-accent",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  ),
);
Button.displayName = "Button";
```

## 테스트 / 검증

- [ ] 라이트 + 다크 양쪽에서 확인
- [ ] 빈 상태 / 로딩 / 에러 / 성공 모두 스토리로 확인
- [ ] 한국어 긴 텍스트, 숫자 오버플로우(₩999,999,999,999) 테스트
- [ ] 키보드만으로 조작 가능한가

## 금지 사항

- ❌ 이모지를 UI chrome 에 사용
- ❌ 핸드드로잉 SVG — Lucide 대신 쓰지 말 것
- ❌ 그라데이션 배경 (특히 보라-파랑 계열)
- ❌ rounded-corner + colored left-border 카드
- ❌ bouncy / overshoot 애니메이션
- ❌ `red-500` / `blue-500` 같은 고정 Tailwind 색상
