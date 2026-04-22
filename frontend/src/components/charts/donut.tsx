"use client";

import { forwardRef, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface DonutSegment {
  /** 0..1 비중 (전체 합이 1 이하여도 렌더링 됨; 초과분은 잘림) */
  pct: number;
  /** CSS color — `var(--chart-1)` 등 */
  color: string;
  label?: string;
}

export interface DonutProps extends React.HTMLAttributes<HTMLDivElement> {
  segments: DonutSegment[];
  size?: number;
  thickness?: number;
  center?: ReactNode;
  /** 접근성용 — 비중 요약을 screen reader에게 전달 */
  ariaLabel?: string;
}

export const Donut = forwardRef<HTMLDivElement, DonutProps>(
  (
    { segments, size = 96, thickness = 12, center, ariaLabel, className, ...props },
    ref,
  ) => {
    const radius = size / 2 - thickness / 2 - 2;
    const circumference = 2 * Math.PI * radius;

    let offset = 0;
    const arcs = segments.map((segment, i) => {
      const length = Math.max(0, circumference * Math.min(1, segment.pct));
      const dash = `${length} ${circumference - length}`;
      const dashOffset = -offset;
      offset += length;
      return (
        <circle
          key={i}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={segment.color}
          strokeWidth={thickness}
          strokeDasharray={dash}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      );
    });

    return (
      <div
        ref={ref}
        role="img"
        aria-label={
          ariaLabel ??
          `도넛 차트 · ${segments
            .map((s) => `${s.label ?? ""} ${(s.pct * 100).toFixed(0)}%`)
            .join(", ")}`
        }
        className={cn("relative inline-flex shrink-0", className)}
        style={{ width: size, height: size }}
        {...props}
      >
        <svg width={size} height={size} className="block">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--muted)"
            strokeWidth={thickness}
          />
          {arcs}
        </svg>
        {center && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            {center}
          </div>
        )}
      </div>
    );
  },
);
Donut.displayName = "Donut";
