# Web Dashboard UI Kit

Next.js 16 + React 19 + Tailwind v4 + shadcn/ui 기반 대시보드를 **정적 HTML + React(Babel)** 로 재구성한 UI kit.

## 파일

| 파일 | 용도 |
|---|---|
| `index.html` | 조립된 데모 화면 (대시보드) |
| `styles.css` | UI kit 전용 CSS (디자인 토큰은 `../../colors_and_type.css` 에서) |
| `TopBar.jsx` | 상단 헤더 (로고, 검색, 알림, 테마 토글, 아바타) |
| `SideNav.jsx` | 좌측 내비게이션 |
| `StatRow.jsx` | 최상단 4개 지표 카드 |
| `HoldingsTable.jsx` | 보유 종목 테이블 + CSV / 추가 버튼 |
| `ChartPanel.jsx` | 포트폴리오 히스토리 라인 차트, 섹터 도넛 |
| `Watchlist.jsx` | 관심종목 리스트 |

## 사용

```bash
open ui_kits/web/index.html   # 브라우저에서 바로 열람
```

우측 상단 **해/달 아이콘** 으로 라이트/다크 토글.

## 주의

- 본 UI kit 은 **프로덕션 shadcn/ui 컴포넌트의 시각적 재구성**입니다. 실제 프로젝트에서는 `npx shadcn@latest add <component>` 로 설치된 컴포넌트를 그대로 사용하세요.
- 숫자는 모두 `font-variant-numeric: tabular-nums` 로 고정폭 정렬.
- 상승/하락 색은 **한국 증시 컨벤션** (빨강/파랑) — `text-rise` / `text-fall`. 자세한 규칙은 루트의 `korean-market-colors.md` 참조.
