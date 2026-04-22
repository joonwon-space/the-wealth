import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { HeatCell } from "./heat-cell";

describe("HeatCell", () => {
  it("prefixes + for positive values", () => {
    render(<HeatCell pct={2.3} />);
    expect(screen.getByText("+2.3")).toBeDefined();
  });

  it("renders negative values with minus sign only", () => {
    render(<HeatCell pct={-1.5} />);
    expect(screen.getByText("-1.5")).toBeDefined();
  });

  it("clamps values beyond ±5", () => {
    render(<HeatCell pct={9.8} />);
    expect(screen.getByText("+5.0")).toBeDefined();
  });

  it("respects fractionDigits", () => {
    render(<HeatCell pct={2.345} fractionDigits={2} />);
    expect(screen.getByText("+2.35")).toBeDefined();
  });
});
