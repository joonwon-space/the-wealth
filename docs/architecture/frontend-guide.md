# Frontend Guide

## 1. Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| Next.js | 16.2.0 | App Router, SSR, middleware/proxy |
| React | 19.2.4 | UI rendering |
| TypeScript | 5 | Type safety |
| Tailwind CSS | 4.2.2 | Utility-first styling |
| shadcn/ui | 4.1.0 | UI components (base-nova / neutral) |
| TanStack Table | 8.21.3 | Holdings data table |
| TanStack Query | 5.91.0 | Server state management (cache, refetch, SSE integration) |
| Recharts | 3.8.0 | Donut chart, heatmap, line charts |
| lightweight-charts | 5.1.0 | Candlestick chart |
| @dnd-kit | 6.3.1+ | Drag-and-drop (portfolio reorder) |
| @sentry/nextjs | 10.45.0 | Error tracking and performance monitoring |
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
| `/dashboard/compare` | `app/dashboard/compare/page.tsx` | Portfolio comparison page |
| `/dashboard/journal` | `app/dashboard/journal/page.tsx` | Investment journal: transaction memos across all portfolios |
| `/dashboard/portfolios` | `app/dashboard/portfolios/page.tsx` | Portfolio list with real-time P&L (evaluation value, P&L amount/rate via `/portfolios/with-prices`; red=profit blue=loss Korean convention; `—` fallback) |
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
| `TopHoldingsWidget.tsx` | Top holdings summary widget |
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

### Trading
| Component | Description |
|-----------|-------------|
| `OrderDialog.tsx` | Buy/sell order dialog orchestrator — delegates to `orders/OrderForm.tsx` and `orders/OrderConfirmation.tsx` |
| `orders/OrderForm.tsx` | Order input form (limit/market toggle, quick ratio buttons 10%/25%/50%/100%, cash balance) |
| `orders/OrderConfirmation.tsx` | Order confirmation step before submission |
| `PendingOrdersPanel.tsx` | Pending (unfilled) orders table with cancel action and auto-detect filled orders via toast notification |

### Notifications
| Component | Description |
|-----------|-------------|
| `NotificationBell.tsx` | Bell icon with unread badge, dropdown panel, mark-read actions |

### Infrastructure
| Component | Description |
|-----------|-------------|
| `dashboard/DashboardMetrics.tsx` | Dashboard metrics cards (total assets, P&L) — extracted from `dashboard/page.tsx` |
| `dashboard/PortfolioList.tsx` | Portfolio list widget on main dashboard — extracted from `dashboard/page.tsx` |
| `QueryProvider.tsx` | TanStack Query provider (wraps app with QueryClientProvider) |
| `ErrorBoundary.tsx` | React Error Boundary with fallback UI + Sentry captureException |
| `PageError.tsx` | Page-level error display component |
| `WidgetErrorFallback.tsx` | Inline widget-level error with optional retry button; used inside cards/sections (Sprint 11 CQ-001) |
| `CardSkeleton.tsx` | Card loading skeleton |
| `ChartSkeleton.tsx` | Chart loading skeleton |
| `TableSkeleton.tsx` | Table loading skeleton |
| `ThemeProvider.tsx` | next-themes provider (system/manual theme) |
| `SentryInit.tsx` | Sentry SDK initialization (production only) |
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

### TanStack Query (`QueryProvider.tsx`)

Server state management via `@tanstack/react-query`:
- Dashboard data cached with `refetchInterval: 30_000` (30-second polling)
- Portfolio/holdings lists use query keys for automatic cache invalidation
- SSE price updates integrated via `queryClient.setQueryData()` for instant UI refresh
- Loading, error, and empty states standardized across pages

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
| `useCountUp` | `hooks/useCountUp.ts` | Animated number count-up hook for dashboard metrics display. |
| `usePriceStream` | `hooks/usePriceStream.ts` | SSE real-time price streaming. Fetches a short-lived ticket via `POST /auth/sse-ticket`, then connects to `GET /prices/stream?ticket={uuid}`. Updates prices every 30s during KST 09:00-15:30. Auto-reconnects on disconnect. |
| `useNotifications` | `hooks/useNotifications.ts` | TanStack Query hook for notification center. Provides `notifications` list, `markRead`, `markAllRead` mutations with optimistic updates. |
| `useOrders` | `hooks/useOrders.ts` | TanStack Query hooks for trading: `usePlaceOrder` (mutation), `useCashBalance` (query, 30s refetch), `usePendingOrders` (query, 5s refetch), `useCancelOrder` (mutation), `useOrderableInfo` (query). |
| `useDebounce` | `hooks/useDebounce.ts` | Generic debounce hook for search input delay. |

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
