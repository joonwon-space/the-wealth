"use client";

import { forwardRef, useId } from "react";
import { cn } from "@/lib/utils";

export interface AreaChartPoint {
  v: number;
  label?: string;
}

export interface AreaChartProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "children"> {
  data: AreaChartPoint[] | number[];
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

/** Catmull-Rom → cubic bezier 변환으로 부드러운 곡선 생성. */
function smoothPath(xs: number[], ys: number[], tension = 0.4): string {
  const n = xs.length;
  if (n === 0) return "";
  if (n === 1) return `M${xs[0]},${ys[0]}`;

  let d = `M${xs[0].toFixed(2)},${ys[0].toFixed(2)}`;
  for (let i = 0; i < n - 1; i++) {
    const p0 = [xs[Math.max(0, i - 1)], ys[Math.max(0, i - 1)]];
    const p1 = [xs[i], ys[i]];
    const p2 = [xs[i + 1], ys[i + 1]];
    const p3 = [xs[Math.min(n - 1, i + 2)], ys[Math.min(n - 1, i + 2)]];

    const cp1x = p1[0] + (p2[0] - p0[0]) * tension;
    const cp1y = p1[1] + (p2[1] - p0[1]) * tension;
    const cp2x = p2[0] - (p3[0] - p1[0]) * tension;
    const cp2y = p2[1] - (p3[1] - p1[1]) * tension;

    d += ` C${cp1x.toFixed(2)},${cp1y.toFixed(2)} ${cp2x.toFixed(2)},${cp2y.toFixed(2)} ${p2[0].toFixed(2)},${p2[1].toFixed(2)}`;
  }
  return d;
}

export const AreaChart = forwardRef<HTMLDivElement, AreaChartProps>(
  (
    {
      data,
      up,
      width = 360,
      height = 120,
      showGrid = true,
      showDot = true,
      padTop = 16,
      padBottom = 4,
      className,
      ...props
    },
    ref,
  ) => {
    const normalized = normalize(data);
    const gradId = useId();
    const glowId = useId();

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
    const xs = normalized.map((_, i) => (i / Math.max(1, n - 1)) * width);
    const sy = (v: number) => padTop + (1 - v) * (height - padTop - padBottom);
    const ys = normalized.map(sy);

    const linePath = smoothPath(xs, ys);
    const areaPath = `${linePath} L${width},${height} L0,${height} Z`;

    const lastX = xs[n - 1]!;
    const lastY = ys[n - 1]!;

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
            {/* 면 그라디언트 — 위쪽만 살짝 착색 */}
            <linearGradient id={gradId} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.18" />
              <stop offset="60%" stopColor={color} stopOpacity="0.04" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
            {/* 끝점 글로우 필터 */}
            <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* 그리드 */}
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
                  strokeOpacity="0.4"
                  strokeDasharray="3 6"
                  strokeWidth={0.75}
                />
              );
            })}

          {/* 면 채우기 */}
          <path d={areaPath} fill={`url(#${gradId})`} />

          {/* 라인 */}
          <path
            d={linePath}
            fill="none"
            stroke={color}
            strokeWidth={1.75}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* 끝점 도트 */}
          {showDot && (
            <>
              <circle
                cx={lastX}
                cy={lastY}
                r={10}
                fill={color}
                opacity={0.12}
              />
              <circle
                cx={lastX}
                cy={lastY}
                r={4}
                fill={color}
                filter={`url(#${glowId})`}
              />
              <circle cx={lastX} cy={lastY} r={2.5} fill="white" opacity={0.9} />
            </>
          )}
        </svg>
      </div>
    );
  },
);
AreaChart.displayName = "AreaChart";
