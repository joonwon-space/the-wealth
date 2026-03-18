import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { DayChangeBadge } from "./DayChangeBadge";

describe("DayChangeBadge", () => {
  it("renders nothing when pct is null", () => {
    const { container } = render(<DayChangeBadge pct={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when pct is undefined", () => {
    const { container } = render(<DayChangeBadge pct={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it("shows ▲ arrow and red color for positive value", () => {
    render(<DayChangeBadge pct={2.3} />);
    const el = screen.getByText(/▲/);
    expect(el.textContent).toMatch(/▲.*2\.3/);
    expect(el.className).toContain("#e31f26");
  });

  it("shows ▼ arrow and blue color for negative value", () => {
    render(<DayChangeBadge pct={-1.5} />);
    const el = screen.getByText(/▼/);
    expect(el.textContent).toMatch(/▼.*1\.5/);
    expect(el.className).toContain("#1a56db");
  });

  it("shows no arrow and default color for zero", () => {
    render(<DayChangeBadge pct={0} />);
    const el = screen.getByText(/0/);
    expect(el.className).toContain("text-foreground");
  });
});
