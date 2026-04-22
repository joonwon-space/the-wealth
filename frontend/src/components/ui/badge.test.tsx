import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Badge } from "./badge";

describe("Badge", () => {
  it("renders children", () => {
    render(<Badge>+3.24%</Badge>);
    expect(screen.getByText("+3.24%")).toBeDefined();
  });

  it("applies rise tone class for rise badge", () => {
    render(<Badge tone="rise">상승</Badge>);
    const el = screen.getByText("상승");
    expect(el.className).toMatch(/text-rise/);
  });

  it("applies solid styling when solid is true", () => {
    render(
      <Badge tone="rise" solid>
        경보
      </Badge>,
    );
    const el = screen.getByText("경보");
    // solid rise produces `bg-rise text-white`
    expect(el.className).toMatch(/bg-rise/);
    expect(el.className).toMatch(/text-white/);
  });

  it("merges className prop", () => {
    render(<Badge className="custom-x">x</Badge>);
    const el = screen.getByText("x");
    expect(el.className).toContain("custom-x");
  });
});
