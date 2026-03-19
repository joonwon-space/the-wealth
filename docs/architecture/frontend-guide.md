# Frontend Guide

## 1. Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| Next.js | 16.1.7 | App Router, SSR, middleware/proxy |
| React | 19.2.4 | UI rendering |
| TypeScript | 5 | Type safety |
| Tailwind CSS | v4 | Utility-first styling |
| shadcn/ui | 4.0.8 | UI components (base-nova / neutral) |
| TanStack Table | 8.21.3 | Holdings data table |
| Recharts | 3.8.0 | Donut chart, heatmap, line charts |
| lightweight-charts | 5.1.0 | Candlestick chart |
| Axios | 1.13.6 | HTTP client (JWT interceptor) |
| Zustand | 5.0.12 | Client-side auth state |
| next-themes | 0.4.6 | Dark/light theme |
| lucide-react | 0.577.0 | Icons |
| sonner | 2.0.7 | Toast notifications |
| Vitest | 4.1.0 | Unit tests |
| Playwright | 1.58.2 | E2E tests |

---

## 2. Page Routing Map

All routes under `/dashboard/` require authentication (checked via Next.js proxy and Zustand auth store).

| Route | File | Description |
|-------|------|-------------|
| `/` | `app/page.tsx` | Root -- redirects to `/login` |
| `/login` | `app/login/page.tsx` | Login form |
| `/register` | `app/register/page.tsx` | Registration form |
| `/dashboard` | `app/dashboard/page.tsx` | Main dashboard: portfolio summary, holdings table, allocation donut |
| `/dashboard/analytics` | `app/dashboard/analytics/page.tsx` | Analytics: monthly heatmap, sector allocation, portfolio history |
| `/dashboard/portfolios` | `app/dashboard/portfolios/page.tsx` | Portfolio list |
| `/dashboard/portfolios/[id]` | `app/dashboard/portfolios/[id]/page.tsx` | Portfolio detail: holdings, transactions |
| `/dashboard/stocks/[ticker]` | `app/dashboard/stocks/[ticker]/page.tsx` | Stock detail: candlestick chart, stock info |
| `/dashboard/settings` | `app/dashboard/settings/page.tsx` | KIS account management, user settings |

### Dashboard Layout

`app/dashboard/layout.tsx` wraps all dashboard pages with:
- `Sidebar` (desktop) -- main navigation
- `BottomNav` (mobile) -- tab-based navigation
- `StockSearchDialog` -- triggered by Cmd+K
- `KeyboardShortcutsDialog` -- triggered by Cmd+?

---

## 3. Key Components

### Navigation
| Component | Description |
|-----------|-------------|
| `Sidebar.tsx` | Desktop sidebar navigation (collapsible) |
| `BottomNav.tsx` | Mobile bottom tab navigation |
| `StockSearchDialog.tsx` | Cmd+K stock search with Korean initial consonant support |
| `KeyboardShortcutsDialog.tsx` | Keyboard shortcut help dialog (Cmd+?) |

### Data Display
| Component | Description |
|-----------|-------------|
| `HoldingsTable.tsx` | TanStack Table v8 -- multi-column sort, live prices, P&L badges |
| `PnLBadge.tsx` | Profit/loss badge (gain=red, loss=blue per Korean convention) |
| `DayChangeBadge.tsx` | Daily change badge (gain=red, loss=blue) |
| `WatchlistSection.tsx` | Watchlist with KRX/NYSE/NASDAQ market tags |

### Charts
| Component | Description |
|-----------|-------------|
| `AllocationDonut.tsx` | Recharts PieChart with center overlay (total assets) |
| `CandlestickChart.tsx` | TradingView lightweight-charts candlestick |
| `MonthlyHeatmap.tsx` | Monthly return heatmap (color intensity) |
| `PortfolioHistoryChart.tsx` | Portfolio value time-series line chart |
| `SectorAllocationChart.tsx` | Sector distribution chart |
| `TransactionChart.tsx` | Monthly buy/sell transaction chart |
| `DynamicCharts.tsx` | Dynamic import wrapper for bundle optimization |

### Infrastructure
| Component | Description |
|-----------|-------------|
| `ErrorBoundary.tsx` | React Error Boundary with fallback UI |
| `ThemeProvider.tsx` | next-themes provider (system/manual theme) |
| `ui/` | shadcn/ui primitives (Button, Card, Table, Dialog, etc.) |

---

## 4. State Management

### Zustand Auth Store (`store/auth.ts`)

```
State:
  accessToken: string | null
  user: User | null
  isAuthenticated: boolean

Persistence:
  localStorage + HttpOnly cookie (dual write)

Actions:
  login(email, password) -> sets tokens
  logout() -> clears tokens
  refreshToken() -> rotates token pair
```

### No Global Data Store

Portfolio data, dashboard summaries, and prices are fetched per-page via Axios calls. There is no global data cache (TanStack Query adoption is planned).

---

## 5. HTTP Client (`lib/api.ts`)

Axios instance configured with:
- **Base URL**: `/api/v1` (proxied to backend via Next.js)
- **Request interceptor**: Attaches `Authorization: Bearer {accessToken}` header
- **Response interceptor**: On 401, attempts token refresh via `/auth/refresh`, then retries the original request. If refresh fails, redirects to `/login`.

---

## 6. Hooks

| Hook | File | Description |
|------|------|-------------|
| `usePriceStream` | `hooks/usePriceStream.ts` | SSE real-time price streaming. Connects to `GET /prices/stream?token={jwt}`. Updates prices every 30s during KST 09:00-15:30. Auto-reconnects on disconnect. |

---

## 7. Utility Libraries (`lib/`)

| File | Description |
|------|-------------|
| `api.ts` | Axios instance with JWT interceptor and auto-refresh |
| `format.ts` | Number/date formatting utilities (Korean won, percentages) |
| `debounce.ts` | Debounce utility for search inputs |
| `utils.ts` | `cn()` utility (clsx + tailwind-merge) |

---

## 8. Type System (`types/`)

| File | Description |
|------|-------------|
| `api.ts` | Auto-generated API types from OpenAPI spec via `openapi-typescript` |
| `index.ts` | Shared type definitions (Portfolio, Holding, Transaction, etc.) |

Regenerate API types:
```bash
cd frontend && npm run generate:types
```

---

## 9. Theming

- **Theme provider**: `next-themes` with system preference detection
- **Style system**: shadcn/ui with `base-nova` style and `neutral` base color
- **Korean color convention**:
  - Gain (positive return): Red
  - Loss (negative return): Blue
  - Neutral (0%): Gray
- **Dark mode**: Full support via CSS variables and Tailwind dark: variants

---

## 10. Testing

### Unit Tests (Vitest)
```bash
cd frontend && npm test          # watch mode
cd frontend && npm run test:run  # single run
```

Test files are co-located with components (e.g., `PnLBadge.test.tsx`).

### E2E Tests (Playwright)
```bash
cd frontend && npm run e2e       # headless
cd frontend && npm run e2e:ui    # interactive UI
```

### Lint + Type Check
```bash
cd frontend && npm run lint      # ESLint
cd frontend && npx tsc --noEmit  # TypeScript check
```

---

## 11. How to Add a New Page

1. Create `frontend/src/app/dashboard/{route}/page.tsx`
2. The page auto-inherits the dashboard layout (sidebar, bottom nav, Cmd+K)
3. Use `api.ts` Axios instance for data fetching
4. Add navigation link in `Sidebar.tsx` and `BottomNav.tsx`
5. Write tests alongside the component

---

## 12. How to Add a shadcn/ui Component

```bash
cd frontend && npx shadcn@latest add <component-name>
```

Components are installed into `src/components/ui/`. They use the project's Tailwind v4 theme automatically.

---

## 13. Build & Bundle

```bash
npm run build     # production build (Next.js standalone output)
npm run analyze   # bundle analysis with @next/bundle-analyzer
```

Chart libraries (`recharts`, `lightweight-charts`) are loaded via dynamic imports (`DynamicCharts.tsx`) to reduce initial bundle size.
