"use client";

import { forwardRef } from "react";
import { cn } from "@/lib/utils";

export interface SectorBarProps extends React.HTMLAttributes<HTMLDivElement> {
  sector: string;
  /** 현재 비중 0..1 */
  pct: number;
  /** 목표 비중 0..1 (없으면 눈금/초과 표시 생략) */
  target?: number;
  /** 바 색상 — `var(--chart-1)` 등. 기본은 `--primary`. */
  color?: string;
  /** 목표 대비 임계치(0..1). 초과 시 `onOverBadge` 자리에 "초과" 표시를 넣을 수 있음. */
  threshold?: number;
}

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

/**
 * 포트폴리오 섹터 bar — 현재 비중(채움) + 목표 비중(tick) 을 한 줄에 표현.
 * 초과/미달 뱃지는 호출자가 자유롭게 조립할 수 있도록 컴포넌트 바깥에서 처리.
 */
export const SectorBar = forwardRef<HTMLDivElement, SectorBarProps>(
  (
    { sector, pct, target, color = "var(--primary)", threshold = 0.03, className, ...props },
    ref,
  ) => {
    const currentPct = clamp01(pct);
    const targetPct = target != null ? clamp01(target) : null;
    const diff = targetPct != null ? currentPct - targetPct : null;
    const isOver = diff != null && diff > threshold;
    const isUnder = diff != null && diff < -threshold;

    return (
      <div ref={ref} className={cn("flex flex-col gap-1", className)} {...props}>
        <div className="flex items-baseline justify-between text-xs tabular-nums">
          <span className="font-semibold text-foreground">{sector}</span>
          <span>
            <span className="font-bold">{(currentPct * 100).toFixed(0)}%</span>
            {targetPct != null && (
              <span className="text-muted-foreground">
                {" "}
                / 목표 {(targetPct * 100).toFixed(0)}%
              </span>
            )}
            {diff != null && (isOver || isUnder) && (
              <span
                className={cn(
                  "ml-1.5 text-[10px] font-semibold",
                  isOver ? "text-rise" : "text-fall",
                )}
              >
                {isOver ? "+" : ""}
                {(diff * 100).toFixed(0)}%p
              </span>
            )}
          </span>
        </div>
        <div className="relative h-1.5 overflow-hidden rounded-full bg-muted">
          <div
            className="absolute inset-y-0 left-0 rounded-full"
            style={{ width: `${currentPct * 100}%`, background: color }}
            aria-hidden
          />
          {targetPct != null && (
            <div
              className="absolute -top-0.5 -bottom-0.5 w-px bg-foreground/50"
              style={{ left: `${targetPct * 100}%` }}
              aria-hidden
            />
          )}
        </div>
      </div>
    );
  },
);
SectorBar.displayName = "SectorBar";
