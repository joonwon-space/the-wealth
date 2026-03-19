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
    vi.mocked(api.get).mockResolvedValue({
      data: {
        total_asset: 0,
        total_invested: 0,
        total_pnl_amount: 0,
        total_pnl_rate: 0,
        holdings: [],
        allocation: [],
        triggered_alerts: [],
      },
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
