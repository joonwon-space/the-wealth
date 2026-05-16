import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  Treemap: ({
    data,
    children,
  }: {
    data: Array<{
      ticker: string;
      changeRate: number | null;
      size: number;
      label: string;
      isKorean: boolean;
    }>;
    children?: React.ReactNode;
  }) => (
    <div data-testid="treemap" data-count={data.length}>
      {data.map((d) => (
        <div
          key={d.ticker}
          data-testid={`tm-node-${d.ticker}`}
          data-rate={d.changeRate ?? "null"}
          data-size={d.size}
          data-label={d.label}
          data-korean={String(d.isKorean)}
        />
      ))}
      {children}
    </div>
  ),
  Tooltip: () => <div data-testid="recharts-tooltip" />,
}));

vi.mock("next-themes", () => ({
  useTheme: () => ({ resolvedTheme: "light" }),
}));

import { HoldingsHeatmap, type HeatmapHolding } from "./HoldingsHeatmap";

const SAMPLE: HeatmapHolding[] = [
  { ticker: "AAPL", name: "Apple Inc.", market_value_krw: 5_000_000, day_change_rate: 1.2, currency: "USD" },
  { ticker: "TSLA", name: "Tesla", market_value_krw: 3_000_000, day_change_rate: -4.5, currency: "USD" },
  { ticker: "MSFT", name: "Microsoft", market_value_krw: 8_000_000, day_change_rate: 0.3, currency: "USD" },
  { ticker: "NVDA", name: "Nvidia", market_value_krw: 2_000_000, day_change_rate: null, currency: "USD" },
];

describe("HoldingsHeatmap", () => {
  it("renders treemap with valid holdings", () => {
    render(<HoldingsHeatmap holdings={SAMPLE} />);
    expect(screen.getByTestId("treemap")).toHaveAttribute("data-count", "4");
  });

  it("sorts holdings by market value descending", () => {
    render(<HoldingsHeatmap holdings={SAMPLE} />);
    const treemap = screen.getByTestId("treemap");
    const order = Array.from(treemap.children)
      .map((el) => el.getAttribute("data-testid") ?? "")
      .filter((id) => id.startsWith("tm-node-"))
      .map((id) => id.replace("tm-node-", ""));
    expect(order).toEqual(["MSFT", "AAPL", "TSLA", "NVDA"]);
  });

  it("filters out holdings with zero or null market value", () => {
    const data: HeatmapHolding[] = [
      { ticker: "A", name: "A", market_value_krw: 1000, day_change_rate: 1 },
      { ticker: "B", name: "B", market_value_krw: 0, day_change_rate: 1 },
      { ticker: "C", name: "C", market_value_krw: null, day_change_rate: 1 },
    ];
    render(<HoldingsHeatmap holdings={data} />);
    expect(screen.getByTestId("treemap")).toHaveAttribute("data-count", "1");
  });

  it("shows empty state when no holdings", () => {
    render(<HoldingsHeatmap holdings={[]} />);
    expect(screen.getByText("보유 종목 데이터가 없습니다.")).toBeInTheDocument();
  });

  it("renders role=img with aria-label summarizing holdings", () => {
    render(<HoldingsHeatmap holdings={SAMPLE} />);
    const chart = screen.getByRole("img");
    expect(chart).toBeInTheDocument();
    expect(chart.getAttribute("aria-label")).toContain("종목 히트맵");
    expect(chart.getAttribute("aria-label")).toContain("Apple Inc.");
  });

  it("renders screen-reader table with all rows", () => {
    render(<HoldingsHeatmap holdings={SAMPLE} />);
    const caption = screen.getByText(/시가총액 비례 크기/);
    expect(caption).toBeInTheDocument();
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument();
    expect(screen.getByText("Tesla")).toBeInTheDocument();
    expect(screen.getByText("Microsoft")).toBeInTheDocument();
    expect(screen.getByText("Nvidia")).toBeInTheDocument();
  });

  it("uses name as label for Korean holdings, ticker for foreign", () => {
    const data: HeatmapHolding[] = [
      {
        ticker: "005930",
        name: "삼성전자",
        market_value_krw: 5_000_000,
        day_change_rate: 1.0,
        currency: "KRW",
      },
      {
        ticker: "AAPL",
        name: "Apple Inc.",
        market_value_krw: 4_000_000,
        day_change_rate: -1.0,
        currency: "USD",
      },
    ];
    render(<HoldingsHeatmap holdings={data} />);
    const koreanNode = screen.getByTestId("tm-node-005930");
    expect(koreanNode.getAttribute("data-label")).toBe("삼성전자");
    expect(koreanNode.getAttribute("data-korean")).toBe("true");
    const foreignNode = screen.getByTestId("tm-node-AAPL");
    expect(foreignNode.getAttribute("data-label")).toBe("AAPL");
    expect(foreignNode.getAttribute("data-korean")).toBe("false");
  });

  it("coerces numeric strings safely", () => {
    const data = [
      {
        ticker: "X",
        name: "X Corp",
        market_value_krw: "1500" as unknown as number,
        day_change_rate: "2.5" as unknown as number,
        currency: "USD",
      },
    ];
    render(<HoldingsHeatmap holdings={data} />);
    const node = screen.getByTestId("tm-node-X");
    expect(node.getAttribute("data-size")).toBe("1500");
    expect(node.getAttribute("data-rate")).toBe("2.5");
  });
});
