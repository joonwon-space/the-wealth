# Phase 4 — Redesign Spec & Claude Code Handoff

> **목적**: Phase 3 하이브리드 리디자인(`redesign.html`)을 Claude Code 가 실제 Next.js 16 + React 19 + Tailwind v4 + shadcn/ui 코드로 옮길 때 필요한 모든 결정·규칙·엣지 케이스를 정리한 단일 문서.
>
> **읽는 순서**
> 1. `README.md` — 브랜드/보이스/비주얼 파운데이션
> 2. `design-system.md` — 토큰/Tailwind/shadcn 설정
> 3. `audit.md` — 현재 데이터 인벤토리 (Portfolio/Holding/Transaction/Order/Alert 스키마)
> 4. **이 문서 (redesign-spec.md)** — 구현 명세
> 5. `redesign.html` — 시각 레퍼런스 (모바일 5화면 + 웹 홈 + 플로우)

---

## 0. 핵심 설계 의사결정 (Why)

1. **Dual-brain 모드 토글**: 장기(📚) / 단타(⚡) 를 앱 전역 세팅으로 둔다. 홈 화면의 hero·hero-chart·기본 정렬·강조 정보가 모드에 따라 바뀐다.
2. **북극성 = "오늘 변동"**: 토스 스타일로 hero에 총자산 + 오늘 변동(KRW + %)을 크게. 밑에 1M 라인차트.
3. **목표 링 (Mission)**: `Portfolio.target_value` 필드가 이미 DB에 있으니 홈 상단 카드에 진척도 링을 바로 표시.
4. **Stream 탭**: 알림·체결·배당·리밸런싱을 하나의 시간순 카드 피드로 통합. 증권사 HTS 의 "홈에 전부 쌓기" 대신 독립된 피드 공간.
5. **Rebalancing 일급화**: 섹터 `pct` vs `target` 초과 시 홈 Todo/Stream 카드로 노출, 상세에서 `target_allocation` 편집.

---

## 1. 구현 범위 (What)

### 1.1 신규 화면

| ID | 경로 | 설명 | Phase 3 레퍼런스 |
|---|---|---|---|
| `home` | `/dashboard` | 홈 (모드 토글 / hero / 1M chart / 목표링 / 벤치마크 / Todo / 섹터 / 배당 / mover) | 📱 ①② / 💻 웹 홈 |
| `portfolio/[id]` | `/dashboard/portfolios/[id]` | 포트폴리오 상세 (요약 / 섹터 vs 목표 / 보유 / 월별 히트맵) | 📱 ③ |
| `stock/[ticker]` | `/dashboard/stocks/[ticker]` | 종목 상세 (hero / big chart / 52w / 지표 / 내 보유 / 매수매도 sticky) | 📱 ④ |
| `stream` | `/dashboard/stream` | 스트림 (알림/체결/배당/리밸런싱 카드 피드 + 필터) | 📱 ⑤ |
| `rebalance` | `/dashboard/rebalance` | 리밸런싱 상세 (Stream 카드에서 진입; 목표 비중 편집 + 제안 주문) | 🆕 플로우 |
| `goal` | `/dashboard/settings/goal` | 목표 설정 (신규) | 🆕 플로우 |
| `onboarding` | `/onboarding/*` | 5-step wizard (KIS 연동→전략→목표→관심종목→완료) | 🆕 플로우 |

### 1.2 기존 화면 정리

- **유지**: `/login` `/register` `/dashboard/settings`
- **통합**: `/dashboard/analytics` 의 개별 탭들(metrics/history/monthly/sector-fx/performance/stock-chart) → 포트폴리오 상세/종목 상세/스트림으로 분산.
- **삭제 검토**: `/dashboard/compare` (용도 불명확, Phase 1에서 지적됨).
- **이동**: `/dashboard/journal` → 체결 후 프롬프트(F6)로 흘러가는 서브 화면. 독립 탭 유지하되 우선순위 낮춤.

### 1.3 신규 백엔드 요구

| 테이블/컬럼 | 용도 | Migration |
|---|---|---|
| `Portfolio.target_allocation` JSONB | 섹터별 목표 비중 `{IT: 0.30, 소재: 0.20, ...}` | **신규** |
| `dividends` 테이블 | `ticker, ex_date, payment_date, amount, currency` | **신규** (KIS 배당 API 또는 수동 입력) |
| `routine_logs` 테이블 | 월/분기 리밸런싱 체크 완료 기록 | **신규** |
| `User.strategy_tag` ENUM | `long`/`short`/`mixed` | **신규** |
| `User.long_short_ratio` SMALLINT | 혼합 사용자의 기본 비중 (기본 70) | **신규** |
| `Alert.condition` 확장 | `above/below` → `above/below/pct_change/drawdown` 추가 | **수정** |

### 1.4 신규 API

```
GET  /api/portfolios/:id/rebalance-suggestion
     → [{ticker, action:'BUY'|'SELL', qty, reason}]
GET  /api/dividends/upcoming                      # 보유 종목 다음 30일 배당
POST /api/portfolios/:id/target-allocation
GET  /api/analytics/benchmark-delta?period=6M     # 내 YoY vs KOSPI200
GET  /api/stream?filter=all|alert|fill|dividend|rebalance
POST /api/alerts                                  # 조건 확장된 알림 생성
GET  /api/tasks/today                             # "오늘 할 것 N" 집계
```

---

## 2. 컴포넌트 분해 (shadcn/ui 확장)

### 2.1 신규 공용 컴포넌트

| 이름 | 위치 | props | Phase 3 대응 |
|---|---|---|---|
| `ModeToggle` | `components/mode-toggle.tsx` | `mode, onChange, position?: 'inline'\|'header'` | 장기/단타 세그먼트 |
| `HeroValue` | `components/hero-value.tsx` | `label, value, change, changePct, up` | 총자산 블록 |
| `AreaChart` | `components/charts/area-chart.tsx` | `data[], up, height, showGrid, showDot` | recharts or lightweight-charts |
| `MiniArea` | `components/charts/mini-area.tsx` | `data[], up, width=64, height=22` | 스파크 |
| `Donut` | `components/charts/donut.tsx` | `segments[], size, thickness, center` | 섹터 도넛 |
| `ProgressRing` | `components/charts/progress-ring.tsx` | `pct, size, thickness, color, label` | 목표 링 |
| `HeatCell` | `components/charts/heat-cell.tsx` | `pct, size` | 월별 히트맵 셀 |
| `TaskCard` | `components/task-card.tsx` | `icon, color, title, sub, action, onClick` | 오늘 할 것 |
| `StreamCard` | `components/stream/stream-card.tsx` | `kind, title, sub, ts, children, accent?` | 스트림 카드 |
| `SectorBar` | `components/sector-bar.tsx` | `sector, pct, target, color` | 현재 vs 목표 |
| `RangeIndicator` | `components/range-indicator.tsx` | `low, high, current` | 52주 레인지 |
| `TabBar` (mobile) | `components/mobile/tab-bar.tsx` | `items[], active, onChange` | 하단 탭바 |

모두 **shadcn CLI 스타일** — `forwardRef`, `cn()` helper, `cva` 로 variants. 디테일은 `design-system.md` 의 "New component checklist" 참고.

### 2.2 확장

- `Card` — `padding` variant 추가 (`compact` 14px, `default` 16px, `comfortable` 20px)
- `Badge` — `tone="rise"|"fall"|"warn"|"ok"|"primary"|"neutral"` + `solid` 플래그
- `Button` — `loading` 상태, 모바일 sticky 하단 바 variant (`rise`/`fall` 풀블리드)

---

## 3. 화면별 상세 스펙

### 3.1 `/dashboard` — 홈

**라우트**: `app/dashboard/page.tsx` (server component) + `HomeClient.tsx` (client)
**데이터**:
```ts
const [summary, tasks, sectors, dividends, movers] = await Promise.all([
  fetch('/api/dashboard/summary'),
  fetch('/api/tasks/today'),
  fetch('/api/analytics/sector-allocation'),
  fetch('/api/dividends/upcoming'),
  fetch('/api/analytics/movers?limit=5'),
]);
```

**레이아웃 (desktop ≥1280px)**:
```
┌──────────────────────────────┬─────────────┐
│ HeroValue + AreaChart (1M)   │ ProgressRing│
│                              │ Benchmark   │
├──────────────┬───────────────┼─────────────┤
│ TaskCards ×3 │ SectorDonut   │ Dividends   │
├──────────────┴───────────────┼─────────────┤
│ HoldingsTable                │ Movers      │
└──────────────────────────────┴─────────────┘
```
**모바일**: 세로 스택. hero → chart → `grid-cols-2`(목표링 + 벤치) → tasks → sector → movers → dividends. 하단 탭바 83px 고정.

**모드 토글 동작**: `mode === 'short'` 이면 hero 금액 대신 **오늘 변동**을 강조(색상 `--rise`), 차트 기간 기본값 1D(intraday), Tasks 대신 미체결 주문 카드 노출, Movers를 4번째 → 2번째로 끌어올림.

### 3.2 `/dashboard/portfolios/[id]` — 포트폴리오 상세

**Tabs** (`shadcn/ui Tabs`): `개요` · `보유` · `거래내역` · `분석`
- 개요: Summary card + SectorBar × 4 + Monthly heatmap 6개월
- 보유: `HoldingsTable` (sortable, 섹터 필터)
- 거래내역: `Transaction` 리스트, memo/tags 편집 인라인
- 분석: PortfolioHistory 라인 + Benchmark delta + FX gain/loss

### 3.3 `/dashboard/stocks/[ticker]`

**Layout**:
- Hero: price + day change + `⭐` `🔔` actions
- Big chart (`AreaChart` height=320 desktop / 180 mobile) + 기간 탭
- `RangeIndicator` 52주
- 6칸 grid(시총/거래량/PER/PBR/배당률/섹터)
- 내 보유 카드 (없으면 "관심종목에 추가" CTA)
- **Sticky 하단** (모바일): `매수` `매도` 버튼 50:50

**주문 Flow (F2)**: `Button` → `Sheet` 모달 (수량·가격·시장가/지정가) → `Dialog` 확인 → POST `/api/orders` → 성공 시 toast + Stream 에 체결 카드 추가 + 투자일지 프롬프트(F6).

### 3.4 `/dashboard/stream`

필터 칩: `전체` `알림` `체결` `리밸런싱` `배당` `루틴`
카드 종류별 `StreamCard`:
- `alert` — 좌 border `--rise`/`--fall`, 액션 2개 (종목보기/매도주문)
- `fill` — tone="ok", 체결 수량·가격 표시
- `dividend` — tone="primary", 배당 예정일/지급일/금액
- `rebalance` — tone="warn", 섹터 bar 미리보기 + "상세 보기" → `/dashboard/rebalance`
- `routine` — dashed border, "체크 시작" CTA

### 3.5 `/dashboard/rebalance`

**입력**: `target_allocation` JSONB (섹터별 목표 비중)
**UI**: SectorBar 편집 가능(슬라이더 또는 직접 입력, 합계 100% 제약), 저장 시 제안 주문 리스트 자동 계산.
**제안 주문 로직** (pseudo):
```ts
for each sector in current:
  diff = current.pct - target.pct
  if abs(diff) < 0.03: skip
  sector_value_to_move = diff * total_value
  candidates = holdings[sector].sort((a,b) => b.weight - a.weight)
  // 큰 포지션부터 축소 / 작은 포지션부터 확대
```

### 3.6 `/onboarding`

5-step wizard, 각 step은 `app/onboarding/[step]/page.tsx`:
1. KIS 연동 (기존 로직 재사용)
2. 전략 선택 (`long` / `short` / `mixed` + 혼합 비율 슬라이더)
3. 목표 금액 + 기간 → `Portfolio.target_value`
4. 관심종목 3개 (검색 + 추가)
5. 완료 + "홈으로" CTA

---

## 4. 모바일 처리 원칙

- **390 × 844 (iPhone 14 base)**. 모든 화면 상단에 44px status bar 공간 + `safe-area-inset-top`.
- **하단 탭바**: 5항목(`홈`/`종목`/`포트폴리오`/`스트림`/`내정보`), 83px + `safe-area-inset-bottom`.
- **Sticky CTA** (매수/매도 등) 은 탭바 **위** 10px, `bg-background/92 backdrop-blur-md border-t`.
- **Tabular nums 필수**: 모든 금액·퍼센트 `font-variant-numeric: tabular-nums`.
- **Pull-to-refresh** (옵션): `framer-motion` + `useSWR` mutator.

---

## 5. 한국 증시 색 규칙 (재확인 · 절대 위반 금지)

- `--rise` = **빨강 #E31F26** = 상승 / 매수
- `--fall` = **파랑 #1A56DB** = 하락 / 매도
- 다크 모드 전환: `#FF4D4F` / `#4B8EF5`
- `destructive` 버튼은 별도 토큰. "삭제"에만 씀; 손실 퍼센트 옆에 붙이지 않는다.

자세한 내용은 `korean-market-colors.md` 참조.

---

## 6. 데이터 매핑 (프론트 ↔ API 필드)

| UI 레이블 | Source | 포매팅 |
|---|---|---|
| 총 평가금액 | `summary.total_value` | `₩{n.toLocaleString('ko-KR')}` |
| 오늘 변동 | `summary.day_change_amount`, `summary.day_change_pct` | `+₩{n}` `+{p.toFixed(2)}%` |
| 목표 진척도 | `portfolio.current_value / portfolio.target_value` | `0..1` clamp |
| 벤치마크 delta | `/analytics/benchmark?period=6M` → `mine_pct - benchmark_pct` | `+{d.toFixed(1)}%p` |
| 섹터 pct | `/analytics/sector-allocation` | 배열 `{sector, value, pct, target}` |
| 월별 수익률 | `/analytics/monthly-returns?months=6` | `{ym, pct}[]` |
| 52주 high/low | `/stocks/:ticker/overview` | `w52_high`, `w52_low` |
| Mover | `/analytics/movers?limit=5&sort=abs_pct` | 정렬 |

---

## 7. 상태 관리

- **Zustand** (이미 쓰고 있다고 가정) 스토어 추가:
  ```ts
  interface UiStore {
    mode: 'long' | 'short';
    setMode: (m) => void;
    density: 'compact' | 'comfortable' | 'spacious';
    // ...
  }
  ```
  모드는 `localStorage` persist. 서버 컴포넌트에서는 cookie로도 읽어 SSR 시 동일 UI.
- **SWR / React Query** — 대시보드 summary 는 15초 staleTime, stream 은 실시간(SSE).
- **SSE stream**: 기존 `usePriceStream` 재사용. Stream 탭에서는 새 카드가 최상단에 200ms flash.

---

## 8. 접근성 / i18n

- 모든 색 정보는 **색+텍스트+아이콘** 3중으로 전달 (색각이상 고려). e.g. 상승 = 빨강 + `▲` + `+3.24%`.
- `role="table"` 에 키보드 네비 + `aria-sort`.
- 한국어 줄바꿈 `word-break: keep-all`.
- 숫자 `<output>` 시맨틱 사용.

---

## 9. 성능 목표

- LCP < 2.5s (홈, 3G fast).
- 홈 JS bundle < 180KB gzip (모드 토글 + 차트 지연 로드).
- 차트 코드는 `dynamic(() => import('recharts/AreaChart'), { ssr: false })`.

---

## 10. 마이그레이션 순서 (권장)

1. **토큰/컴포넌트** — 신규 shadcn 컴포넌트 7개 추가, 기존 토큰 검증.
2. **DB 마이그레이션** — `Portfolio.target_allocation`, `dividends`, `routine_logs`, `User.strategy_tag`.
3. **API 엔드포인트** — `/api/tasks/today`, `/api/dividends/upcoming`, `/api/analytics/benchmark-delta`, `/api/stream`.
4. **홈 리디자인** — 기존 `/dashboard` 를 새 레이아웃으로 교체, 모드 토글 도입.
5. **Stream 탭** — 신규 라우트.
6. **종목 상세 개편** — 기존 분석 페이지에서 떨어져 나와 `/dashboard/stocks/[ticker]`.
7. **포트폴리오 상세 개편** — Tabs 구조로 정리, 기존 분석 탭 항목 흡수.
8. **Rebalance 라우트** — 신규.
9. **Onboarding** — 신규.
10. **모바일 래퍼** — 반응형 점검, 탭바/sticky CTA.

---

## 11. 열린 이슈

- **배당 데이터 소스**: KIS API에 배당 조회가 있는지 재확인. 없으면 DART/증권사 CSV 수동 업로드 경로 필요.
- **Onboarding UX**: "혼합" 사용자의 기본 비율 70:30이 맞나? 사용자 설문 근거?
- **리밸런싱 제안 정확도**: 세금/수수료를 고려할지 여부. 1차 버전은 수수료 무시, 2차에 반영.
- **다크 모드 기본값**: 시스템 따라감 vs 앱 설정. 현재는 시스템 따라감이 default.
