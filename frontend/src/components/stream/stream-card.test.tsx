import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StreamCard } from "./stream-card";

describe("StreamCard", () => {
  it("renders title, sub and default badge label for alert kind", () => {
    render(
      <StreamCard
        kind="alert"
        title="NVIDIA — $145 돌파"
        sub="목표 $140 이상"
        ts="14:32"
      />,
    );
    expect(screen.getByText("NVIDIA — $145 돌파")).toBeDefined();
    expect(screen.getByText("목표 $140 이상")).toBeDefined();
    expect(screen.getByText("목표가 도달")).toBeDefined();
    expect(screen.getByText("14:32")).toBeDefined();
  });

  it("uses fill kind default label", () => {
    render(<StreamCard kind="fill" title="삼성전자 매수" />);
    expect(screen.getByText("체결 완료")).toBeDefined();
  });

  it("uses rebalance kind default label", () => {
    render(<StreamCard kind="rebalance" title="IT 45% 초과" />);
    expect(screen.getByText("리밸런싱 제안")).toBeDefined();
  });

  it("allows custom badgeLabel", () => {
    render(
      <StreamCard kind="alert" title="t" badgeLabel="커스텀" />,
    );
    expect(screen.getByText("커스텀")).toBeDefined();
  });

  it("renders children action slot", () => {
    render(
      <StreamCard kind="alert" title="t">
        <button>매도</button>
      </StreamCard>,
    );
    expect(screen.getByRole("button", { name: "매도" })).toBeDefined();
  });
});
