import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SectorBar } from "./sector-bar";

describe("SectorBar", () => {
  it("renders sector name and current percent", () => {
    render(<SectorBar sector="IT" pct={0.45} target={0.3} />);
    expect(screen.getByText("IT")).toBeDefined();
    expect(screen.getByText("45%")).toBeDefined();
  });

  it("marks over-threshold diff with rise tone", () => {
    const { container } = render(
      <SectorBar sector="IT" pct={0.45} target={0.3} />,
    );
    const el = container.querySelector(".text-rise");
    expect(el?.textContent).toMatch(/\+15%p/);
  });

  it("marks under-threshold diff with fall tone", () => {
    const { container } = render(
      <SectorBar sector="금융" pct={0.1} target={0.2} />,
    );
    const el = container.querySelector(".text-fall");
    expect(el?.textContent).toMatch(/-10%p/);
  });

  it("omits diff badge when within threshold", () => {
    const { container } = render(
      <SectorBar sector="소재" pct={0.21} target={0.2} />,
    );
    expect(container.querySelector(".text-rise")).toBeNull();
    expect(container.querySelector(".text-fall")).toBeNull();
  });
});
