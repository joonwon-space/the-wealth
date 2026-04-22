import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ProgressRing } from "./progress-ring";

describe("ProgressRing", () => {
  it("renders default pct label", () => {
    render(<ProgressRing pct={0.37} />);
    expect(screen.getByText("37.0%")).toBeDefined();
  });

  it("clamps pct above 1", () => {
    const { container } = render(<ProgressRing pct={1.5} size={80} thickness={8} />);
    const bar = container.querySelector('[role="progressbar"]');
    expect(bar?.getAttribute("aria-valuenow")).toBe("100");
  });

  it("clamps pct below 0", () => {
    const { container } = render(<ProgressRing pct={-0.5} />);
    const bar = container.querySelector('[role="progressbar"]');
    expect(bar?.getAttribute("aria-valuenow")).toBe("0");
  });

  it("hides label when label is null", () => {
    const { container } = render(<ProgressRing pct={0.5} label={null} />);
    expect(container.textContent).toBe("");
  });

  it("renders custom label ReactNode", () => {
    render(<ProgressRing pct={0.5} label={<span>커스텀</span>} />);
    expect(screen.getByText("커스텀")).toBeDefined();
  });
});
