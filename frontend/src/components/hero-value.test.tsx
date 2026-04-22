import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { HeroValue } from "./hero-value";

describe("HeroValue", () => {
  it("renders label and value", () => {
    render(<HeroValue label="총 평가금액" value="₩42,180,500" />);
    expect(screen.getByText("총 평가금액")).toBeDefined();
    expect(screen.getByText("₩42,180,500")).toBeDefined();
  });

  it("marks positive pct with rise tone", () => {
    const { container } = render(
      <HeroValue label="총 평가금액" value="₩1" changePct={1.84} />,
    );
    expect(container.querySelector(".text-rise")).not.toBeNull();
    expect(container.textContent).toMatch(/\+1\.84%/);
  });

  it("marks negative pct with fall tone", () => {
    const { container } = render(
      <HeroValue label="총 평가금액" value="₩1" changePct={-2.1} />,
    );
    expect(container.querySelector(".text-fall")).not.toBeNull();
    expect(container.textContent).toMatch(/-2\.10%/);
  });

  it("shows footnote", () => {
    render(<HeroValue label="label" value="₩1" footnote="USD/KRW 1,380" />);
    expect(screen.getByText("USD/KRW 1,380")).toBeDefined();
  });

  it("renders trailing slot", () => {
    render(<HeroValue label="label" value="₩1" trailing={<span>mini</span>} />);
    expect(screen.getByText("mini")).toBeDefined();
  });
});
