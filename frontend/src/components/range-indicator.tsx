"use client";

import { forwardRef } from "react";
import { cn } from "@/lib/utils";

export interface RangeIndicatorProps extends React.HTMLAttributes<HTMLDivElement> {
  low: number;
  high: number;
  current: number;
  /** 값 포매터 — 기본은 `toLocaleString()`. */
  formatValue?: (value: number) => string;
  /** 라벨 기본값 오버라이드. */
  labels?: {
    low?: string;
    current?: string;
    high?: string;
  };
  /** 배경 그라디언트 끄기 — 단색 트랙이 필요한 경우 */
  plainTrack?: boolean;
}

const defaultFormat = (v: number) => v.toLocaleString();

/**
 * 52주 레인지 같은 저가-고가 범위 인디케이터.
 * `low <= current <= high` 가 아니어도 막지 않고 0..1 로 clamp 해서 렌더.
 */
export const RangeIndicator = forwardRef<HTMLDivElement, RangeIndicatorProps>(
  (
    {
      low,
      high,
      current,
      formatValue = defaultFormat,
      labels,
      plainTrack = false,
      className,
      ...props
    },
    ref,
  ) => {
    const span = high - low;
    const safeSpan = span > 0 ? span : 1;
    const pos = Math.max(0, Math.min(1, (current - low) / safeSpan));

    return (
      <div ref={ref} className={cn("space-y-2", className)} {...props}>
        <div className="relative h-1.5 overflow-visible rounded-full bg-muted">
          <div
            aria-hidden
            className="absolute inset-y-0 left-0 rounded-full"
            style={{
              width: `${pos * 100}%`,
              background: plainTrack
                ? "var(--primary)"
                : "linear-gradient(90deg, var(--fall), var(--muted-foreground), var(--rise))",
              opacity: plainTrack ? 1 : 0.8,
            }}
          />
          <div
            aria-hidden
            className="absolute -top-1 size-4 rounded-full border-[3px] border-card bg-foreground shadow-sm"
            style={{ left: `calc(${pos * 100}% - 8px)` }}
          />
        </div>
        <div className="flex justify-between text-[11px] tabular-nums">
          <div>
            <div className="text-[10px] text-muted-foreground">
              {labels?.low ?? "저가"}
            </div>
            <div className="font-bold text-fall">{formatValue(low)}</div>
          </div>
          <div className="text-center">
            <div className="text-[10px] text-muted-foreground">
              {labels?.current ?? "현재"}
            </div>
            <div className="font-bold text-foreground">{formatValue(current)}</div>
          </div>
          <div className="text-right">
            <div className="text-[10px] text-muted-foreground">
              {labels?.high ?? "고가"}
            </div>
            <div className="font-bold text-rise">{formatValue(high)}</div>
          </div>
        </div>
      </div>
    );
  },
);
RangeIndicator.displayName = "RangeIndicator";
