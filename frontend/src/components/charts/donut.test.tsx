import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Donut } from "./donut";

describe("Donut", () => {
  const segments = [
    { pct: 0.5, color: "var(--chart-1)", label: "IT" },
    { pct: 0.3, color: "var(--chart-3)", label: "소재" },
    { pct: 0.2, color: "var(--chart-5)", label: "금융" },
  ];

  it("renders a track circle + one arc per segment", () => {
    const { container } = render(<Donut segments={segments} />);
    const circles = container.querySelectorAll("circle");
    // 1 track + 3 segment arcs
    expect(circles.length).toBe(4);
  });

  it("renders center slot", () => {
    const { getByText } = render(
      <Donut segments={segments} center={<span>12</span>} />,
    );
    expect(getByText("12")).toBeDefined();
  });

  it("sets a descriptive aria-label", () => {
    const { container } = render(<Donut segments={segments} />);
    const root = container.querySelector('[role="img"]');
    expect(root?.getAttribute("aria-label")).toMatch(/도넛/);
  });
});
