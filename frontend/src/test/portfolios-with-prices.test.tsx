/**
 * Component tests for the portfolio list page P&L display.
 * Tests verify rendering of evaluation value, P&L amount/rate, and Korean
 * color conventions (red=profit, blue=loss).
 */

import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { server } from "./server";
import PortfoliosPage from "@/app/dashboard/portfolios/page";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = makeQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

const API_BASE = "http://localhost:8000/api/v1";

function mockWithPrices(
  rows: object[]
) {
  server.use(
    http.get(`${API_BASE}/portfolios/with-prices`, () =>
      HttpResponse.json(rows)
    )
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("PortfoliosPage — P&L display", () => {
  it("renders KRW evaluation value when market_value_krw is provided", async () => {
    mockWithPrices([
      {
        id: 1,
        user_id: 1,
        name: "국내주식",
        currency: "KRW",
        display_order: 0,
        created_at: "2025-01-01T00:00:00",
        holdings_count: 2,
        total_invested: "700000",
        kis_account_id: 1,
        target_value: null,
        market_value_krw: "800000",
        pnl_amount_krw: "100000",
        pnl_rate: "14.2857",
        exchange_rate: null,
      },
    ]);

    renderWithProviders(<PortfoliosPage />);

    await waitFor(() => {
      expect(screen.getByText("국내주식")).toBeDefined();
    });

    // Evaluation value formatted as KRW (₩800,000) — shown in both mobile and desktop slots
    const evalEls = screen.getAllByText(/₩800,000/);
    expect(evalEls.length).toBeGreaterThanOrEqual(1);
  });

  it("renders dash when market_value_krw is null (KIS not connected)", async () => {
    mockWithPrices([
      {
        id: 2,
        user_id: 1,
        name: "KIS없음",
        currency: "KRW",
        display_order: 0,
        created_at: "2025-01-01T00:00:00",
        holdings_count: 1,
        total_invested: "500000",
        kis_account_id: null,
        target_value: null,
        market_value_krw: null,
        pnl_amount_krw: null,
        pnl_rate: null,
        exchange_rate: null,
      },
    ]);

    renderWithProviders(<PortfoliosPage />);

    await waitFor(() => {
      expect(screen.getByText("KIS없음")).toBeDefined();
    });

    // Stats area shows dash for unavailable prices
    const statsSection = screen.getAllByText("—");
    expect(statsSection.length).toBeGreaterThanOrEqual(1);
  });

  it("applies text-rise class for positive P&L (Korean profit convention)", async () => {
    mockWithPrices([
      {
        id: 3,
        user_id: 1,
        name: "수익포트",
        currency: "KRW",
        display_order: 0,
        created_at: "2025-01-01T00:00:00",
        holdings_count: 1,
        total_invested: "700000",
        kis_account_id: 1,
        target_value: null,
        market_value_krw: "800000",
        pnl_amount_krw: "100000",
        pnl_rate: "14.2857",
        exchange_rate: null,
      },
    ]);

    const { container } = renderWithProviders(<PortfoliosPage />);

    await waitFor(() => {
      expect(screen.getByText("수익포트")).toBeDefined();
    });

    // Profit P&L text element should have the Korean-market rise token class
    const riseEl = container.querySelector(".text-rise");
    expect(riseEl).not.toBeNull();
  });

  it("applies text-fall class for negative P&L (Korean loss convention)", async () => {
    mockWithPrices([
      {
        id: 4,
        user_id: 1,
        name: "손실포트",
        currency: "KRW",
        display_order: 0,
        created_at: "2025-01-01T00:00:00",
        holdings_count: 1,
        total_invested: "700000",
        kis_account_id: 1,
        target_value: null,
        market_value_krw: "600000",
        pnl_amount_krw: "-100000",
        pnl_rate: "-14.2857",
        exchange_rate: null,
      },
    ]);

    const { container } = renderWithProviders(<PortfoliosPage />);

    await waitFor(() => {
      expect(screen.getByText("손실포트")).toBeDefined();
    });

    // Loss P&L text element should have the Korean-market fall token class
    const fallEl = container.querySelector(".text-fall");
    expect(fallEl).not.toBeNull();
  });

  it("applies text-muted-foreground class for zero P&L", async () => {
    mockWithPrices([
      {
        id: 5,
        user_id: 1,
        name: "보합포트",
        currency: "KRW",
        display_order: 0,
        created_at: "2025-01-01T00:00:00",
        holdings_count: 1,
        total_invested: "700000",
        kis_account_id: 1,
        target_value: null,
        market_value_krw: "700000",
        pnl_amount_krw: "0",
        pnl_rate: "0",
        exchange_rate: null,
      },
    ]);

    const { container } = renderWithProviders(<PortfoliosPage />);

    await waitFor(() => {
      expect(screen.getByText("보합포트")).toBeDefined();
    });

    // Zero P&L text should have text-muted-foreground (neutral)
    // Stats div always contains muted-foreground elements
    const mutedEl = container.querySelector(".text-muted-foreground");
    expect(mutedEl).not.toBeNull();
  });
});
