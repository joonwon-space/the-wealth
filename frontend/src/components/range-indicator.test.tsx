import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { RangeIndicator } from "./range-indicator";

describe("RangeIndicator", () => {
  it("formats values with toLocaleString by default", () => {
    render(<RangeIndicator low={50000} high={100000} current={75000} />);
    expect(screen.getByText("50,000")).toBeDefined();
    expect(screen.getByText("75,000")).toBeDefined();
    expect(screen.getByText("100,000")).toBeDefined();
  });

  it("uses custom formatValue", () => {
    render(
      <RangeIndicator
        low={100}
        high={200}
        current={150}
        formatValue={(v) => `$${v}`}
      />,
    );
    expect(screen.getByText("$100")).toBeDefined();
    expect(screen.getByText("$150")).toBeDefined();
    expect(screen.getByText("$200")).toBeDefined();
  });

  it("handles low==high without dividing by zero", () => {
    const { container } = render(
      <RangeIndicator low={100} high={100} current={100} />,
    );
    // Should not throw; renders all three labels
    expect(container.textContent).toMatch(/100/);
  });

  it("overrides labels", () => {
    render(
      <RangeIndicator
        low={1}
        high={3}
        current={2}
        labels={{ low: "MIN", current: "NOW", high: "MAX" }}
      />,
    );
    expect(screen.getByText("MIN")).toBeDefined();
    expect(screen.getByText("NOW")).toBeDefined();
    expect(screen.getByText("MAX")).toBeDefined();
  });
});
