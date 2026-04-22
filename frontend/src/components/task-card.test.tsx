import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { TaskCard } from "./task-card";

describe("TaskCard", () => {
  it("renders title and sub", () => {
    render(
      <TaskCard
        icon={<svg aria-hidden />}
        title="리밸런싱 필요"
        sub="IT 비중 +15%p"
      />,
    );
    expect(screen.getByText("리밸런싱 필요")).toBeDefined();
    expect(screen.getByText("IT 비중 +15%p")).toBeDefined();
  });

  it("fires onClick", () => {
    const onClick = vi.fn();
    render(
      <TaskCard icon={<svg aria-hidden />} title="x" onClick={onClick} />,
    );
    fireEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalled();
  });

  it("disables the button when disabled prop is set", () => {
    render(
      <TaskCard icon={<svg aria-hidden />} title="x" disabled />,
    );
    const btn = screen.getByRole("button");
    expect((btn as HTMLButtonElement).disabled).toBe(true);
  });
});
