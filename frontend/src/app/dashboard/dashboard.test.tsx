import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  api: { get: vi.fn() },
}));

vi.mock("@/components/AllocationDonut", () => ({
  AllocationDonut: () => <div data-testid="donut" />,
}));

vi.mock("@/components/HoldingsTable", () => ({
  HoldingsTable: () => <div data-testid="holdings-table" />,
}));

vi.mock("@/components/PnLBadge", () => ({
  PnLBadge: ({ value }: { value: number }) => <span>{value}</span>,
}));

vi.mock("@/components/WatchlistSection", () => ({
  WatchlistSection: () => <div data-testid="watchlist" />,
}));

import DashboardPage from "./page";
import { api } from "@/lib/api";

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows skeleton while loading", () => {
    // api.get never resolves → stays in loading state
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    renderWithQuery(<DashboardPage />);
    // Skeleton elements should be present (the animated rectangles)
    const skeletons = document.querySelectorAll("[data-slot='skeleton']");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows empty state when no portfolios", async () => {
    // Dashboard now fires multiple parallel queries — each satellite endpoint
    // needs its own shape. Route per URL.
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === "/dashboard/summary") {
        return {
          data: {
            total_asset: 0,
            total_invested: 0,
            total_pnl_amount: 0,
            total_pnl_rate: 0,
            holdings: [],
            allocation: [],
            triggered_alerts: [],
          },
        };
      }
      if (url === "/tasks/today") return { data: { count: 0, tasks: [] } };
      if (url.startsWith("/analytics/sector-allocation")) return { data: [] };
      if (url.startsWith("/analytics/benchmark-delta")) {
        return {
          data: {
            index_code: "KOSPI200",
            period: "6M",
            mine_pct: 0,
            benchmark_pct: 0,
            delta_pct_points: 0,
          },
        };
      }
      if (url.startsWith("/dividends/upcoming")) return { data: [] };
      return { data: [] };
    });

    renderWithQuery(<DashboardPage />);
    const text = await screen.findByText("아직 보유 종목이 없습니다");
    expect(text).toBeInTheDocument();
  });

  it("shows error UI when API fails", async () => {
    vi.mocked(api.get).mockRejectedValue(new Error("Network error"));

    renderWithQuery(<DashboardPage />);
    const errorText = await screen.findByText("데이터를 불러올 수 없습니다");
    expect(errorText).toBeInTheDocument();
    expect(screen.getByText("다시 시도")).toBeInTheDocument();
  });
});
