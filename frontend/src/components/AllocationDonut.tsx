"use client";

import { useState } from "react";
import { useTheme } from "next-themes";
import { Cell, Pie, PieChart, Tooltip } from "recharts";
import { formatKRW, formatRate } from "@/lib/format";

interface AllocationItem {
  ticker: string;
  name: string;
  value: number;
  ratio: number;
}

interface Props {
  data: AllocationItem[];
  totalAsset: number;
}

interface TooltipPayloadItem {
  payload: AllocationItem & { value: number };
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
}

// Resolved colors for SVG fill (CSS vars not directly supported in SVG).
// Light mode: blue-first, dark mode: green-first.
const CHART_COLORS_LIGHT = [
  "#1e90ff", // dodger blue
  "#00ff00", // neon green
  "#F59E0B", // amber
  "#F43F5E", // rose
  "#8B5CF6", // violet
  "#06B6D4", // cyan
  "#F97316", // orange
  "#22C55E", // green
];
const CHART_COLORS_DARK = [
  "#00ff00", // neon green
  "#1e90ff", // dodger blue
  "#F59E0B", // amber
  "#F43F5E", // rose
  "#8B5CF6", // violet
  "#06B6D4", // cyan
  "#F97316", // orange
  "#22C55E", // green
];

const SIZE = 240;

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const item = payload[0].payload;
  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="font-semibold">{item.name}</p>
      <p className="text-muted-foreground">{item.ticker}</p>
      <p className="mt-1 tabular-nums">{formatRate(item.ratio)}%</p>
      <p className="tabular-nums text-foreground">{formatKRW(item.value)}</p>
    </div>
  );
}

export function AllocationDonut({ data, totalAsset }: Props) {
  const { resolvedTheme } = useTheme();
  const CHART_COLORS = resolvedTheme === "dark" ? CHART_COLORS_DARK : CHART_COLORS_LIGHT;
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  // API may return numeric strings from Decimal fields — coerce to numbers
  const numericData = data.map((item) => ({
    ...item,
    value: Number(item.value),
    ratio: Number(item.ratio),
  }));

  const activeItem = hoverIndex != null ? numericData[hoverIndex] : null;
  const activeColor = hoverIndex != null ? CHART_COLORS[hoverIndex % CHART_COLORS.length] : null;

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
      {/* Donut chart */}
      <div
        className="relative flex items-center justify-center shrink-0"
        style={{ width: SIZE, height: SIZE }}
        role="img"
        aria-label="자산 배분 도넛 차트"
      >
        <PieChart width={SIZE} height={SIZE}>
          <Pie
            data={numericData}
            cx="50%"
            cy="50%"
            innerRadius={70}
            outerRadius={110}
            paddingAngle={2}
            dataKey="value"
            onMouseEnter={(_, index) => setHoverIndex(index)}
            onMouseLeave={() => setHoverIndex(null)}
          >
            {numericData.map((_, index) => (
              <Cell
                key={index}
                fill={CHART_COLORS[index % CHART_COLORS.length]}
                opacity={hoverIndex != null && hoverIndex !== index ? 0.5 : 1}
                cursor="pointer"
                style={{
                  transform: hoverIndex === index ? "scale(1.04)" : "scale(1)",
                  transformOrigin: "center",
                  transition: "transform 0.15s ease, opacity 0.15s ease",
                }}
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} wrapperStyle={{ zIndex: 10 }} />
        </PieChart>

        {/* 중앙 텍스트 오버레이 — hover 시 TOP 종목명 + 비중%, 기본은 총 자산 */}
        <div
          className="pointer-events-none absolute flex flex-col items-center justify-center text-center px-4"
          style={{ zIndex: 0 }}
        >
          {activeItem && activeColor ? (
            <>
              <span className="text-xs font-semibold leading-tight max-w-[80px] truncate">
                {activeItem.name}
              </span>
              <span className="text-lg font-bold tabular-nums" style={{ color: activeColor }}>
                {formatRate(activeItem.ratio)}%
              </span>
            </>
          ) : (
            <>
              <span className="text-xs text-muted-foreground">총 자산</span>
              <span className="text-base font-bold tabular-nums">
                {formatKRW(totalAsset)}
              </span>
            </>
          )}
        </div>
      </div>

      {/* 범례: 아이콘 원형 12px + 종목명 + 비중% + 금액 3열 구조 */}
      <div className="flex flex-col gap-1.5 pt-2 min-w-0">
        {numericData.map((item, i) => {
          const color = CHART_COLORS[i % CHART_COLORS.length];
          const isActive = hoverIndex === i;
          return (
            <div
              key={`${item.ticker}-${i}`}
              className="grid items-center gap-x-3 text-xs cursor-default"
              style={{ gridTemplateColumns: "12px 1fr auto auto" }}
              onMouseEnter={() => setHoverIndex(i)}
              onMouseLeave={() => setHoverIndex(null)}
            >
              <span
                className="inline-block h-3 w-3 rounded-full shrink-0 transition-all duration-150"
                style={{
                  background: color,
                  outline: isActive ? `2px solid ${color}` : "2px solid transparent",
                  outlineOffset: "1px",
                }}
              />
              <span
                className={`truncate transition-colors duration-150 ${isActive ? "font-medium text-foreground" : "text-foreground/80"}`}
              >
                {item.name}
              </span>
              <span className="tabular-nums text-muted-foreground text-right">
                {formatRate(item.ratio)}%
              </span>
              <span className="tabular-nums text-muted-foreground text-right">
                {formatKRW(item.value)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
