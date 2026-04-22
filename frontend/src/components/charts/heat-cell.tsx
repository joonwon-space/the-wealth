"use client";

import { forwardRef } from "react";
import { cn } from "@/lib/utils";

export interface HeatCellProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 월별 수익률(%) 등. -5 ~ +5 범위로 clamp. */
  pct: number;
  width?: number;
  height?: number;
  /** 소수점 자리수 — 기본 1. */
  fractionDigits?: number;
}

const CLAMP_LIMIT = 5;

/**
 * 월별 수익률 히트맵 셀. 한국 증시 색: 상승=빨강, 하락=파랑.
 * 강도에 비례해 배경 alpha 를 조절하며, ±3% 초과 시 흰 글자로 대비 확보.
 */
export const HeatCell = forwardRef<HTMLDivElement, HeatCellProps>(
  ({ pct, width = 44, height = 32, fractionDigits = 1, className, ...props }, ref) => {
    const clamped = Math.max(-CLAMP_LIMIT, Math.min(CLAMP_LIMIT, pct));
    const intensity = Math.abs(clamped) / CLAMP_LIMIT;
    const color = clamped >= 0 ? "var(--rise)" : "var(--fall)";
    const alpha = 0.12 + intensity * 0.55;
    const highContrast = Math.abs(clamped) > 3;
    const sign = clamped >= 0 ? "+" : "";

    return (
      <div
        ref={ref}
        role="cell"
        aria-label={`${sign}${clamped.toFixed(fractionDigits)}%`}
        className={cn(
          "flex items-center justify-center rounded-md text-[11px] font-bold tabular-nums",
          className,
        )}
        style={{
          width,
          height,
          background: `color-mix(in oklab, ${color} ${alpha * 100}%, transparent)`,
          color: highContrast ? "#fff" : color,
        }}
        {...props}
      >
        {sign}
        {clamped.toFixed(fractionDigits)}
      </div>
    );
  },
);
HeatCell.displayName = "HeatCell";
