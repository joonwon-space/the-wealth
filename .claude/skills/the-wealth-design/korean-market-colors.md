# Korean Market Color Convention — 한국 증시 색 규칙

> **핵심**: 한국 증시에서는 **상승 = 빨강**, **하락 = 파랑** 입니다. 미국/유럽 증시의 green/red 컨벤션과 **정반대**이므로 주의하세요.

---

## 매핑

| 상황 | 색 토큰 | 라이트 | 다크 (WCAG AA) | Tailwind 유틸리티 |
|---|---|---|---|---|
| 상승 (change > 0) | `--rise` | `#E31F26` | `#FF4D4F` | `text-rise` / `bg-rise` |
| 하락 (change < 0) | `--fall` | `#1A56DB` | `#4B8EF5` | `text-fall` / `bg-fall` |
| 보합 (change = 0) | `--flat` / muted | gray | gray | `text-muted-foreground` |

### 소프트 배경

가격 플래시 / 배지 / 행 강조에 사용:

```css
.bg-rise-soft { background: color-mix(in oklab, var(--rise) 12%, transparent); }
.bg-fall-soft { background: color-mix(in oklab, var(--fall) 12%, transparent); }
```

---

## 사용 원칙

1. **색만으로 방향 전달하지 않기** — 항상 `+` / `-` 부호나 `ArrowUp` / `ArrowDown` 아이콘과 같이 씁니다 (색각 이상자 고려).
2. **하드코딩한 `text-red-500` / `text-blue-500` 쓰지 않기** — 다크 모드에서 가독성이 깨집니다. 반드시 토큰 사용.
3. **`--destructive` 와 `--rise` 는 다른 토큰**. 삭제 버튼은 `--destructive` (generic red), 가격 상승은 `--rise`. 한 화면에서 손실 금액(파랑)과 destructive 버튼(빨강)이 가까이 놓이지 않게 배치.
4. **캔들스틱 차트**: up candle = `--rise`, down candle = `--fall`. lightweight-charts 세팅:

```ts
chart.addCandlestickSeries({
  upColor: getCss("--rise"),
  downColor: getCss("--fall"),
  borderUpColor: getCss("--rise"),
  borderDownColor: getCss("--fall"),
  wickUpColor: getCss("--rise"),
  wickDownColor: getCss("--fall"),
});
```

5. **수익률 / 변동폭 표기 패턴**:

```tsx
const rate = position.changeRate;  // number

const className =
  rate > 0 ? "text-rise" :
  rate < 0 ? "text-fall" :
  "text-muted-foreground";

const sign = rate > 0 ? "+" : rate < 0 ? "" : "";  // 음수는 자체 '-' 사용

return (
  <span className={`${className} tabular-nums font-semibold`}>
    {sign}{rate.toFixed(2)}%
  </span>
);
```

6. **테이블 행 플래시** (가격 업데이트 시): 행에 200ms 동안 `bg-rise-soft` / `bg-fall-soft` 적용 후 fade out.

---

## 예시

보유 종목 행:

```
삼성전자         125주   ₩71,200   +₩1,200  +1.71%    ← text-rise
NAVER            30주    ₩186,500  -₩2,100  -1.11%    ← text-fall
SK하이닉스       40주    ₩158,000   ₩0      0.00%     ← text-muted-foreground
```

알림 배지:

- "목표가 도달 (상한)" — `bg-rise text-white` 캡슐
- "손절선 이탈" — `bg-fall text-white` 캡슐

---

## 국제화 고려

만약 **해외 시장(미국/유럽) 뷰를 추가**하게 되면, 사용자 설정으로 `market-color-mode: "KR" | "INTL"` 를 두고 `--rise`/`--fall` 값을 스왑하는 방식이 자연스럽습니다. 단, 기본은 한국 컨벤션 유지.
