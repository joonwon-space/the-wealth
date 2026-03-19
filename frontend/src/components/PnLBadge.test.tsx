import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PnLBadge } from "./PnLBadge";

describe("PnLBadge", () => {
  it("shows red for positive values", () => {
    render(<PnLBadge value={1000} />);
    const el = screen.getByText(/1,000/);
    expect(el.closest("span")).toHaveClass("text-[#e31f26]");
  });

  it("shows blue for negative values", () => {
    render(<PnLBadge value={-500} />);
    const el = screen.getByText(/500/);
    expect(el.closest("span")).toHaveClass("text-[#1a56db]");
  });

  it("shows default color for zero", () => {
    render(<PnLBadge value={0} />);
    const el = screen.getByText("0");
    expect(el.closest("span")).toHaveClass("text-foreground");
  });

  it("shows dash for null", () => {
    render(<PnLBadge value={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("appends suffix", () => {
    render(<PnLBadge value={12.34} suffix="%" />);
    expect(screen.getByText(/12\.34%/)).toBeInTheDocument();
  });

  it("shows TrendingUp icon for positive value", () => {
    render(<PnLBadge value={500} />);
    const icon = document.querySelector("[aria-label='상승']");
    expect(icon).toBeTruthy();
  });

  it("shows TrendingDown icon for negative value", () => {
    render(<PnLBadge value={-500} />);
    const icon = document.querySelector("[aria-label='하락']");
    expect(icon).toBeTruthy();
  });

  it("shows Minus icon for zero value", () => {
    render(<PnLBadge value={0} />);
    const icon = document.querySelector("[aria-label='보합']");
    expect(icon).toBeTruthy();
  });
});
