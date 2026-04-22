"use client";

import { forwardRef, useId } from "react";
import { cn } from "@/lib/utils";

export interface AreaChartPoint {
  /** 0..1 정규화 값. 절대치는 caller가 미리 normalize. */
  v: number;
  /** 옵션 레이블 (tooltip 훗날 연결용) */
  label?: string;
}

export interface AreaChartProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "children"> {
  data: AreaChartPoint[] | number[];
  /** true면 --rise, false면 --fall. 미지정 시 마지막 값으로 자동 판별. */
  up?: boolean;
  width?: number;
  height?: number;
  showGrid?: boolean;
  showDot?: boolean;
  padTop?: number;
  padBottom?: number;
}

function normalize(raw: AreaChartProps["data"]): number[] {
  const nums = raw.map((p) => (typeof p === "number" ? p : p.v));
  if (nums.length === 0) return [];
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  if (max === min) return nums.map(() => 0.5);
  return nums.map((n) => (n - min) / (max - min));
}

/**
 * 간단한 SVG 기반 area + line chart. redesign.html 의 primitives.jsx 버전을
 * React 19 + Tailwind v4 토큰으로 이식. 0..1 정규화 값 배열 또는 `{v}` 객체
 * 배열을 받고, 저-고 기준으로 캔버스에 맞게 스케일.
 */
export const AreaChart = forwardRef<HTMLDivElement, AreaChartProps>(
  (
    {
      data,
      up,
      width = 360,
      height = 120,
      showGrid = true,
      showDot = true,
      padTop = 12,
      padBottom = 8,
      className,
      ...props
    },
    ref,
  ) => {
    const normalized = normalize(data);
    const gradientId = useId();
    if (normalized.length === 0) {
      return (
        <div
          ref={ref}
          className={cn(
            "flex h-full w-full items-center justify-center text-xs text-muted-foreground",
            className,
          )}
          style={{ height }}
          {...props}
        >
          데이터 없음
        </div>
      );
    }

    const direction =
      up !== undefined
        ? up
        : normalized[normalized.length - 1]! >= (normalized[0] ?? 0);
    const color = direction ? "var(--rise)" : "var(--fall)";

    const n = normalized.length;
    const sx = (i: number) => (i / Math.max(1, n - 1)) * width;
    const sy = (v: number) => padTop + (1 - v) * (height - padTop - padBottom);
    const path = normalized
      .map((v, i) => (i === 0 ? "M" : "L") + sx(i).toFixed(1) + "," + sy(v).toFixed(1))
      .join(" ");
    const area = `${path} L${width},${height} L0,${height} Z`;
    const lastY = sy(normalized[n - 1]!);

    return (
      <div
        ref={ref}
        className={cn("w-full", className)}
        role="img"
        aria-label="시계열 차트"
        {...props}
      >
        <svg
          viewBox={`0 0 ${width} ${height}`}
          width="100%"
          height={height}
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stopColor={color} stopOpacity="0.28" />
              <stop offset="1" stopColor={color} stopOpacity="0" />
            </linearGradient>
          </defs>
          {showGrid &&
            [0.25, 0.5, 0.75].map((f) => {
              const y = padTop + f * (height - padTop - padBottom);
              return (
                <line
                  key={f}
                  x1="0"
                  x2={width}
                  y1={y}
                  y2={y}
                  stroke="var(--border)"
                  strokeDasharray="2 4"
                  strokeWidth={1}
                />
              );
            })}
          <path d={area} fill={`url(#${gradientId})`} />
          <path d={path} fill="none" stroke={color} strokeWidth={2} />
          {showDot && (
            <>
              <circle cx={width - 2} cy={lastY} r={8} fill={color} opacity={0.25} />
              <circle cx={width - 2} cy={lastY} r={3.5} fill={color} />
            </>
          )}
        </svg>
      </div>
    );
  },
);
AreaChart.displayName = "AreaChart";
