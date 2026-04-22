"use client";

import { forwardRef, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface ProgressRingProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "children"> {
  /** 0..1 진행률. 범위를 벗어나면 clamp. */
  pct: number;
  size?: number;
  thickness?: number;
  /** CSS color token/value. e.g. `var(--primary)`, `#1e90ff`. */
  color?: string;
  /** 기본은 백분율 문자열. `null`이면 레이블 숨김. ReactNode로 커스텀 가능. */
  label?: ReactNode | null;
  /** 접근성용 텍스트 — 지정하지 않으면 백분율을 읽어줌. */
  ariaLabel?: string;
}

/**
 * 목표 진척도 링. redesign.html / primitives.jsx 포팅 버전.
 * - 트랙은 `--muted`, 진행 호는 `color` (기본 `--primary`).
 * - 라벨 폰트 크기는 링 크기에 비례 (size × 0.21).
 */
export const ProgressRing = forwardRef<HTMLDivElement, ProgressRingProps>(
  (
    {
      pct,
      size = 76,
      thickness = 8,
      color = "var(--primary)",
      label,
      ariaLabel,
      className,
      ...props
    },
    ref,
  ) => {
    const clamped = Math.max(0, Math.min(1, pct));
    const radius = size / 2 - thickness / 2 - 1;
    const circumference = 2 * Math.PI * radius;
    const filled = circumference * clamped;
    const defaultLabel = `${(clamped * 100).toFixed(1)}%`;

    return (
      <div
        ref={ref}
        role="progressbar"
        aria-label={ariaLabel ?? `진척도 ${defaultLabel}`}
        aria-valuenow={Math.round(clamped * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
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
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={thickness}
            strokeLinecap="round"
            strokeDasharray={`${filled} ${circumference}`}
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
          />
        </svg>
        {label !== null && (
          <div
            className="absolute inset-0 flex items-center justify-center font-bold tracking-tight tabular-nums"
            style={{ fontSize: Math.max(10, size * 0.21) }}
          >
            {label ?? defaultLabel}
          </div>
        )}
      </div>
    );
  },
);
ProgressRing.displayName = "ProgressRing";
