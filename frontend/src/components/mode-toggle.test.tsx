import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ModeToggle } from "./mode-toggle";

describe("ModeToggle", () => {
  it("marks the active mode with aria-selected", () => {
    render(<ModeToggle mode="long" onChange={() => {}} />);
    const longTab = screen.getByRole("tab", { name: /장기/ });
    const shortTab = screen.getByRole("tab", { name: /단타/ });
    expect(longTab.getAttribute("aria-selected")).toBe("true");
    expect(shortTab.getAttribute("aria-selected")).toBe("false");
  });

  it("calls onChange with the new mode", () => {
    const onChange = vi.fn();
    render(<ModeToggle mode="long" onChange={onChange} />);
    fireEvent.click(screen.getByRole("tab", { name: /단타/ }));
    expect(onChange).toHaveBeenCalledWith("short");
  });

  it("shows ratio suffix on inline position", () => {
    render(
      <ModeToggle
        mode="long"
        onChange={() => {}}
        ratio={{ long: 70, short: 30 }}
      />,
    );
    const longTab = screen.getByRole("tab", { name: /장기/ });
    expect(longTab.textContent).toMatch(/70%/);
  });

  it("hides ratio suffix on header position", () => {
    render(
      <ModeToggle
        mode="long"
        onChange={() => {}}
        position="header"
        ratio={{ long: 70, short: 30 }}
      />,
    );
    const longTab = screen.getByRole("tab", { name: /장기/ });
    expect(longTab.textContent).not.toMatch(/70%/);
  });
});
