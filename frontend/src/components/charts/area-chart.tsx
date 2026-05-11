"use client";

import { forwardRef, useId } from "react";
import { cn } from "@/lib/utils";

export interface AreaChartPoint {
  v: number;
  /** ISO date string (YYYY-MM-DD). showXAxis 사용 시 필요. */
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
  showXAxis?: boolean;
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

function getLabels(raw: AreaChartProps["data"]): (string | undefined)[] {
  return raw.map((p) => (typeof p === "number" ? undefined : p.label));
}

/** "YYYY-MM-DD" → "M/D" */
function fmtDate(iso: string): string {
  const parts = iso.split("-");
  if (parts.length < 3) return iso;
  return `${parseInt(parts[1])}/${parseInt(parts[2])}`;
}

/** Catmull-Rom → cubic bezier */
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

/** 균등 간격으로 최대 tickCount개 인덱스 선택 (첫/끝 포함). */
function pickTicks(n: number, tickCount = 5): number[] {
  if (n <= tickCount) return Array.from({ length: n }, (_, i) => i);
  const ticks: number[] = [0];
  const step = (n - 1) / (tickCount - 1);
  for (let i = 1; i < tickCount - 1; i++) {
    ticks.push(Math.round(i * step));
  }
  ticks.push(n - 1);
  return ticks;
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
      showXAxis = false,
      padTop = 16,
      padBottom = 4,
      className,
      ...props
    },
    ref,
  ) => {
    const normalized = normalize(data);
    const labels = getLabels(data);
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
    const sy = (v: number) =>
      padTop + (1 - v) * (height - padTop - padBottom);
    const ys = normalized.map(sy);

    const linePath = smoothPath(xs, ys);
    const areaPath = `${linePath} L${width},${height} L0,${height} Z`;
    const lastX = xs[n - 1]!;
    const lastY = ys[n - 1]!;

    // x축 틱: % 기반 left 값으로 HTML에 렌더링
    const ticks = showXAxis ? pickTicks(n) : [];

    return (
      <div ref={ref} className={cn("w-full", className)} {...props}>
        {/* SVG 차트 — preserveAspectRatio="none" 이라 텍스트는 여기에 넣지 않음 */}
        <div role="img" aria-label="시계열 차트">
          <svg
            viewBox={`0 0 ${width} ${height}`}
            width="100%"
            height={height}
            preserveAspectRatio="none"
          >
            <defs>
              <linearGradient id={gradId} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity="0.18" />
                <stop offset="60%" stopColor={color} stopOpacity="0.04" />
                <stop offset="100%" stopColor={color} stopOpacity="0" />
              </linearGradient>
              <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
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
                    strokeOpacity="0.4"
                    strokeDasharray="3 6"
                    strokeWidth={0.75}
                  />
                );
              })}

            <path d={areaPath} fill={`url(#${gradId})`} />
            <path
              d={linePath}
              fill="none"
              stroke={color}
              strokeWidth={1.75}
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {showDot && (
              <>
                <circle cx={lastX} cy={lastY} r={10} fill={color} opacity={0.12} />
                <circle cx={lastX} cy={lastY} r={4} fill={color} filter={`url(#${glowId})`} />
                <circle cx={lastX} cy={lastY} r={2.5} fill="white" opacity={0.9} />
              </>
            )}
          </svg>
        </div>

        {/* x축 레이블 — SVG 밖 HTML로 렌더링해 글자 찌그러짐 방지 */}
        {showXAxis && ticks.length > 0 && (
          <div className="relative mt-1 h-4 w-full select-none">
            {ticks.map((idx) => {
              const raw = labels[idx];
              if (!raw) return null;
              const pct = (idx / Math.max(1, n - 1)) * 100;
              const isFirst = idx === 0;
              const isLast = idx === n - 1;
              return (
                <span
                  key={idx}
                  className="absolute text-[10px] leading-none text-muted-foreground/60"
                  style={{
                    left: `${pct}%`,
                    transform: isFirst
                      ? "none"
                      : isLast
                        ? "translateX(-100%)"
                        : "translateX(-50%)",
                  }}
                >
                  {fmtDate(raw)}
                </span>
              );
            })}
          </div>
        )}
      </div>
    );
  },
);
AreaChart.displayName = "AreaChart";
