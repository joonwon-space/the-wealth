"use client";

import { ResponsiveContainer, Treemap } from "recharts";
import { formatKRW } from "@/lib/format";

export interface HeatmapHolding {
  ticker: string;
  name: string;
  market_value_krw: number | null;
  day_change_rate: number | null;
}

interface HeatmapNode {
  name: string;
  ticker: string;
  fullName: string;
  size: number;
  changeRate: number | null;
  [key: string]: unknown;
}

function getCellColor(rate: number | null): string {
  if (rate == null) return "#52525b";
  const abs = Math.abs(rate);
  if (rate > 0) {
    if (abs >= 3) return "#991b1b";
    if (abs >= 2) return "#b91c1c";
    if (abs >= 1) return "#dc2626";
    return "#ef4444";
  }
  if (rate < 0) {
    if (abs >= 3) return "#1e3a8a";
    if (abs >= 2) return "#1d4ed8";
    if (abs >= 1) return "#2563eb";
    return "#3b82f6";
  }
  return "#52525b";
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function HeatmapCell(props: any) {
  const {
    x = 0,
    y = 0,
    width = 0,
    height = 0,
    depth,
    ticker,
    changeRate,
    value,
  } = props as {
    x: number;
    y: number;
    width: number;
    height: number;
    depth: number;
    ticker?: string;
    changeRate?: number | null;
    value?: number;
  };

  if (depth !== 1 || width < 4 || height < 4) return null;

  const color = getCellColor(changeRate ?? null);
  const isTiny = width < 52 || height < 40;
  const isSmall = width < 90 || height < 65;
  const rx = Math.min(6, width / 20, height / 20);

  const formattedRate =
    changeRate != null
      ? `${changeRate >= 0 ? "+" : ""}${Number(changeRate).toFixed(1)}%`
      : "—";

  const midY = y + height / 2;

  return (
    <g>
      <rect
        x={x + 1}
        y={y + 1}
        width={Math.max(0, width - 2)}
        height={Math.max(0, height - 2)}
        fill={color}
        rx={rx}
        ry={rx}
      />
      {!isTiny && (
        <>
          <text
            x={x + 8}
            y={midY - (isSmall ? 10 : 14)}
            fill="rgba(255,255,255,0.78)"
            fontSize={isSmall ? 9 : 10}
            fontFamily="system-ui, sans-serif"
          >
            {ticker ?? ""}
          </text>
          <text
            x={x + 8}
            y={midY + (isSmall ? 5 : 6)}
            fill="white"
            fontSize={isSmall ? 13 : 16}
            fontWeight="700"
            fontFamily="system-ui, sans-serif"
          >
            {formattedRate}
          </text>
          {!isSmall && value != null && (
            <text
              x={x + 8}
              y={midY + 24}
              fill="rgba(255,255,255,0.58)"
              fontSize={9}
              fontFamily="system-ui, sans-serif"
            >
              {formatKRW(value)}
            </text>
          )}
        </>
      )}
    </g>
  );
}

export interface HoldingsHeatmapProps {
  holdings: HeatmapHolding[];
  height?: number;
}

export function HoldingsHeatmap({ holdings, height = 220 }: HoldingsHeatmapProps) {
  const data: HeatmapNode[] = holdings
    .filter((h) => Number(h.market_value_krw ?? 0) > 0)
    .map((h) => ({
      name: h.ticker,
      ticker: h.ticker,
      fullName: h.name,
      size: Number(h.market_value_krw),
      changeRate: h.day_change_rate != null ? Number(h.day_change_rate) : null,
    }))
    .sort((a, b) => b.size - a.size);

  if (data.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        보유 종목 데이터가 없습니다.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <Treemap
        data={data}
        dataKey="size"
        aspectRatio={16 / 5}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        content={<HeatmapCell /> as any}
      />
    </ResponsiveContainer>
  );
}
