import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "1" }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("@/components/StockSearchDialog", () => ({
  StockSearchDialog: () => <div data-testid="stock-search" />,
}));

vi.mock("@/components/PnLBadge", () => ({
  PnLBadge: ({ value }: { value: number }) => <span>{value}</span>,
}));

import PortfolioDetailPage from "./page";
import { api } from "@/lib/api";

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe("PortfolioDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows empty state when no holdings", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });

    renderWithQuery(<PortfolioDetailPage />);
    const text = await screen.findByText("보유 종목이 없습니다");
    expect(text).toBeInTheDocument();
  });

  it("shows holdings list when data exists", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: [
        { id: 1, ticker: "005930", name: "삼성전자", quantity: "10", avg_price: "70000" },
      ],
    });

    renderWithQuery(<PortfolioDetailPage />);
    const names = await screen.findAllByText("삼성전자");
    expect(names[0]).toBeInTheDocument();
  });
});
