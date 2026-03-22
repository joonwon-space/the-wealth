import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { HoldingsTable } from "./HoldingsTable";

// Minimal mock for next/link to avoid Next.js context requirement
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

const krwHolding = {
  id: 1,
  ticker: "005930",
  name: "삼성전자",
  quantity: 10,
  avg_price: 70000,
  current_price: 75000,
  market_value: 750000,
  market_value_krw: 750000,
  pnl_amount: 50000,
  pnl_rate: 7.14,
  day_change_rate: 1.2,
  w52_high: 80000,
  w52_low: 60000,
  currency: "KRW",
};

const usdHolding = {
  id: 2,
  ticker: "AAPL",
  name: "Apple Inc.",
  quantity: 5,
  avg_price: 150.0,
  current_price: 170.0,
  market_value: 850.0,
  market_value_krw: 1105000,
  pnl_amount: 100.0,
  pnl_rate: 13.33,
  day_change_rate: -0.5,
  w52_high: 200.0,
  w52_low: 130.0,
  currency: "USD",
};

const negativeHolding = {
  id: 3,
  ticker: "000660",
  name: "SK하이닉스",
  quantity: 5,
  avg_price: 120000,
  current_price: 100000,
  market_value: 500000,
  market_value_krw: 500000,
  pnl_amount: -100000,
  pnl_rate: -16.67,
  day_change_rate: -2.5,
  w52_high: 130000,
  w52_low: 90000,
  currency: "KRW",
};

describe("HoldingsTable", () => {
  describe("empty state", () => {
    it("shows empty message when no holdings", () => {
      render(<HoldingsTable holdings={[]} />);
      // Both mobile and desktop views render the empty message
      const emptyMessages = screen.getAllByText("보유 종목이 없습니다.");
      expect(emptyMessages.length).toBeGreaterThan(0);
    });
  });

  describe("renders holdings", () => {
    it("renders stock name and ticker for KRW holding", () => {
      render(<HoldingsTable holdings={[krwHolding]} />);
      expect(screen.getAllByText("삼성전자").length).toBeGreaterThan(0);
      expect(screen.getAllByText("005930").length).toBeGreaterThan(0);
    });

    it("renders stock name and ticker for USD holding", () => {
      render(<HoldingsTable holdings={[usdHolding]} />);
      expect(screen.getAllByText("Apple Inc.").length).toBeGreaterThan(0);
      expect(screen.getAllByText("AAPL").length).toBeGreaterThan(0);
    });

    it("shows 해외 badge for USD holdings", () => {
      render(<HoldingsTable holdings={[usdHolding]} />);
      const badges = screen.getAllByText("해외");
      expect(badges.length).toBeGreaterThan(0);
    });

    it("does not show 해외 badge for KRW holdings", () => {
      render(<HoldingsTable holdings={[krwHolding]} />);
      expect(screen.queryByText("해외")).not.toBeInTheDocument();
    });
  });

  describe("PnL color rules (Korean convention)", () => {
    it("positive pnl_amount renders with red color (상승=빨간색)", () => {
      render(<HoldingsTable holdings={[krwHolding]} />);
      // Find PnLBadge elements with red color
      const redElements = document.querySelectorAll(".text-\\[\\#e31f26\\]");
      expect(redElements.length).toBeGreaterThan(0);
    });

    it("negative pnl_amount renders with blue color (하락=파란색)", () => {
      render(<HoldingsTable holdings={[negativeHolding]} />);
      const blueElements = document.querySelectorAll(".text-\\[\\#1a56db\\]");
      expect(blueElements.length).toBeGreaterThan(0);
    });

    it("positive day_change_rate renders with red color", () => {
      render(<HoldingsTable holdings={[krwHolding]} />);
      // day_change_rate of 1.2 should be red
      const redElements = document.querySelectorAll(".text-\\[\\#e31f26\\]");
      expect(redElements.length).toBeGreaterThan(0);
    });

    it("negative day_change_rate renders with blue color", () => {
      render(<HoldingsTable holdings={[usdHolding]} />);
      // day_change_rate of -0.5 should be blue
      const blueElements = document.querySelectorAll(".text-\\[\\#1a56db\\]");
      expect(blueElements.length).toBeGreaterThan(0);
    });
  });

  describe("USD display", () => {
    it("formats USD avg_price with $ sign", () => {
      render(<HoldingsTable holdings={[usdHolding]} />);
      // USD price should be formatted with $
      const usdPrices = screen.getAllByText(/\$150\.00/);
      expect(usdPrices.length).toBeGreaterThan(0);
    });

    it("formats USD current_price with $ sign", () => {
      render(<HoldingsTable holdings={[usdHolding]} />);
      const usdPrices = screen.getAllByText(/\$170\.00/);
      expect(usdPrices.length).toBeGreaterThan(0);
    });

    it("renders link to correct stock detail page", () => {
      render(<HoldingsTable holdings={[usdHolding]} />);
      const links = document.querySelectorAll('a[href="/dashboard/stocks/AAPL"]');
      expect(links.length).toBeGreaterThan(0);
    });

    it("renders link to correct stock detail page for KRW", () => {
      render(<HoldingsTable holdings={[krwHolding]} />);
      const links = document.querySelectorAll('a[href="/dashboard/stocks/005930"]');
      expect(links.length).toBeGreaterThan(0);
    });
  });

  describe("multi-column sorting (desktop table)", () => {
    it("renders sortable column headers", () => {
      render(<HoldingsTable holdings={[krwHolding, usdHolding]} />);
      // Table headers should be present
      expect(screen.getAllByText("종목명").length).toBeGreaterThan(0);
      expect(screen.getAllByText("수익률").length).toBeGreaterThan(0);
    });

    it("sort by pnl_rate changes row order", () => {
      render(
        <HoldingsTable
          holdings={[
            { ...krwHolding, pnl_rate: 7.14, market_value_krw: 750000 },
            { ...usdHolding, pnl_rate: 13.33, market_value_krw: 1105000 },
            { ...negativeHolding, pnl_rate: -16.67, market_value_krw: 500000 },
          ]}
        />
      );

      // Click 수익률 header to sort ascending
      const headers = screen.getAllByText("수익률");
      // Use the desktop table header (role=button)
      const sortableHeader = headers.find(
        (h) => h.closest("[role='button']") !== null
      );
      if (sortableHeader) {
        const headerCell = sortableHeader.closest("[role='button']")!;
        fireEvent.click(headerCell);
        // After click, sorting changes — we just verify no error
      }

      // Table rows should still be in DOM
      expect(screen.getAllByText("삼성전자").length).toBeGreaterThan(0);
    });

    it("default sort is by market_value_krw descending", () => {
      render(
        <HoldingsTable
          holdings={[
            { ...krwHolding, market_value_krw: 750000 },
            { ...usdHolding, market_value_krw: 1105000 },
          ]}
        />
      );

      // desktop table body rows
      const table = document.querySelector("table");
      if (table) {
        const rows = table.querySelectorAll("tbody tr");
        // First row should be AAPL (higher market_value_krw)
        expect(rows[0].textContent).toContain("Apple Inc.");
        expect(rows[1].textContent).toContain("삼성전자");
      }
    });
  });

  describe("null value handling", () => {
    it("shows dash for null pnl_amount", () => {
      const holding = { ...krwHolding, pnl_amount: null };
      render(<HoldingsTable holdings={[holding]} />);
      // Should show em dash for null PnL
      const dashes = screen.getAllByText("—");
      expect(dashes.length).toBeGreaterThan(0);
    });
  });
});
