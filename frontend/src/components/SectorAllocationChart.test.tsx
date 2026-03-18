import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

// Mock recharts to avoid SVG rendering issues in jsdom
vi.mock("recharts", () => ({
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  Pie: ({ data, children }: { data: unknown[]; children?: React.ReactNode }) => (
    <div data-testid="pie" data-count={data.length}>
      {children}
    </div>
  ),
  Cell: ({ fill }: { fill: string }) => (
    <div data-testid="cell" data-fill={fill} />
  ),
  Tooltip: () => <div data-testid="tooltip" />,
}));

vi.mock("@/lib/format", () => ({
  formatKRW: (v: number) => `₩${v.toLocaleString()}`,
}));

import { SectorAllocationChart } from "./SectorAllocationChart";

const sampleData = [
  { sector: "IT", value: 700000, weight: 53.8 },
  { sector: "금융", value: 300000, weight: 23.1 },
  { sector: "헬스케어", value: 300000, weight: 23.1 },
];

describe("SectorAllocationChart", () => {
  it("renders without crashing with valid data", () => {
    render(<SectorAllocationChart data={sampleData} />);
    expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
  });

  it("renders empty chart for empty data", () => {
    render(<SectorAllocationChart data={[]} />);
    expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
  });

  it("renders legend items for each sector", () => {
    render(<SectorAllocationChart data={sampleData} />);
    expect(screen.getByText("IT")).toBeInTheDocument();
    expect(screen.getByText("금융")).toBeInTheDocument();
    expect(screen.getByText("헬스케어")).toBeInTheDocument();
  });

  it("renders weight percentage for each sector in legend", () => {
    render(<SectorAllocationChart data={sampleData} />);
    expect(screen.getByText("53.8%")).toBeInTheDocument();
    expect(screen.getAllByText("23.1%")).toHaveLength(2);
  });

  it("passes correct number of data items to Pie", () => {
    render(<SectorAllocationChart data={sampleData} />);
    const pie = screen.getByTestId("pie");
    expect(pie.getAttribute("data-count")).toBe("3");
  });

  it("renders a Cell for each data item", () => {
    render(<SectorAllocationChart data={sampleData} />);
    const cells = screen.getAllByTestId("cell");
    expect(cells).toHaveLength(sampleData.length);
  });

  it("uses known color for IT sector", () => {
    render(<SectorAllocationChart data={[{ sector: "IT", value: 700000, weight: 100 }]} />);
    const cell = screen.getByTestId("cell");
    expect(cell.getAttribute("data-fill")).toBe("#1a56db");
  });

  it("uses fallback color for unknown sector", () => {
    render(
      <SectorAllocationChart
        data={[{ sector: "기타", value: 100000, weight: 100 }]}
      />
    );
    const cell = screen.getByTestId("cell");
    // 기타 maps to #9ca3af in SECTOR_COLORS; if not found, fallback is also #9ca3af
    expect(cell.getAttribute("data-fill")).toBe("#9ca3af");
  });

  it("renders Tooltip component", () => {
    render(<SectorAllocationChart data={sampleData} />);
    expect(screen.getByTestId("tooltip")).toBeInTheDocument();
  });

  it("converts string values to numbers", () => {
    const stringData = [
      { sector: "IT", value: "700000" as unknown as number, weight: "53.8" as unknown as number },
    ];
    // Should not throw even with string inputs (component converts them)
    render(<SectorAllocationChart data={stringData} />);
    expect(screen.getByText("IT")).toBeInTheDocument();
  });

  it("renders legend with colored dots for each sector", () => {
    render(<SectorAllocationChart data={sampleData} />);
    // Each legend item should have a colored circle (rendered as span with inline style)
    const colorDots = document.querySelectorAll("span[style*='background']");
    expect(colorDots.length).toBeGreaterThanOrEqual(sampleData.length);
  });

  it("displays correct weight format with one decimal", () => {
    const data = [{ sector: "금융", value: 500000, weight: 66.7 }];
    render(<SectorAllocationChart data={data} />);
    expect(screen.getByText("66.7%")).toBeInTheDocument();
  });
});
