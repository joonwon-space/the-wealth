"use client";

import { useTheme } from "next-themes";
import { ResponsiveContainer, Treemap } from "recharts";
import { formatKRW, formatRate } from "@/lib/format";

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

interface ColorPalette {
  rise: [string, string, string, string];
  fall: [string, string, string, string];
  neutral: string;
}

const LIGHT_PALETTE: ColorPalette = {
  rise: ["#ef4444", "#dc2626", "#b91c1c", "#991b1b"],
  fall: ["#3b82f6", "#2563eb", "#1d4ed8", "#1e3a8a"],
  neutral: "#52525b",
};

const DARK_PALETTE: ColorPalette = {
  rise: ["#f87171", "#ef4444", "#dc2626", "#b91c1c"],
  fall: ["#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8"],
  neutral: "#71717a",
};

function pickIntensity(abs: number): 0 | 1 | 2 | 3 {
  if (abs >= 3) return 3;
  if (abs >= 2) return 2;
  if (abs >= 1) return 1;
  return 0;
}

function getCellColor(rate: number | null, palette: ColorPalette): string {
  if (rate == null || rate === 0) return palette.neutral;
  const idx = pickIntensity(Math.abs(rate));
  return rate > 0 ? palette.rise[idx] : palette.fall[idx];
}

interface CellTextProps {
  x: number;
  y: number;
  width: number;
  height: number;
  ticker: string;
  formattedRate: string;
  value: number | undefined;
  isSmall: boolean;
}

function CellText({
  x,
  y,
  width,
  height,
  ticker,
  formattedRate,
  value,
  isSmall,
}: CellTextProps) {
  const midY = y + height / 2;
  return (
    <>
      <text
        x={x + 8}
        y={midY - (isSmall ? 10 : 14)}
        fill="rgba(255,255,255,0.78)"
        fontSize={isSmall ? 9 : 10}
        fontFamily="system-ui, sans-serif"
      >
        {ticker}
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
      {/* Reserve width hint to satisfy unused-var on width */}
      <desc>{`w=${width}`}</desc>
    </>
  );
}

interface RechartsCellProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  depth?: number;
  ticker?: string;
  fullName?: string;
  changeRate?: number | null;
  value?: number;
  palette?: ColorPalette;
}

function HeatmapCell(props: RechartsCellProps) {
  const {
    x = 0,
    y = 0,
    width = 0,
    height = 0,
    depth,
    ticker,
    fullName,
    changeRate,
    value,
    palette = LIGHT_PALETTE,
  } = props;

  if (depth !== 1 || width < 4 || height < 4) return null;

  const color = getCellColor(changeRate ?? null, palette);
  const isTiny = width < 52 || height < 40;
  const isSmall = width < 90 || height < 65;
  const rx = Math.min(6, width / 20, height / 20);
  const formattedRate =
    changeRate != null
      ? `${changeRate >= 0 ? "+" : ""}${Number(changeRate).toFixed(1)}%`
      : "—";

  const titleText = `${fullName ?? ticker ?? ""} · ${formattedRate}${
    value != null ? ` · ${formatKRW(value)}` : ""
  }`;

  return (
    <g>
      <title>{titleText}</title>
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
        <CellText
          x={x}
          y={y}
          width={width}
          height={height}
          ticker={ticker ?? ""}
          formattedRate={formattedRate}
          value={value}
          isSmall={isSmall}
        />
      )}
    </g>
  );
}

export interface HoldingsHeatmapProps {
  holdings: HeatmapHolding[];
  height?: number;
}

export function HoldingsHeatmap({ holdings, height = 220 }: HoldingsHeatmapProps) {
  const { resolvedTheme } = useTheme();
  const palette = resolvedTheme === "dark" ? DARK_PALETTE : LIGHT_PALETTE;

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

  const ariaLabel = `종목 히트맵: ${data
    .slice(0, 8)
    .map(
      (d) =>
        `${d.fullName} ${
          d.changeRate != null ? `${formatRate(d.changeRate)}%` : "변동 없음"
        }`,
    )
    .join(", ")}`;

  return (
    <div role="img" aria-label={ariaLabel} data-testid="holdings-heatmap">
      {/* Screen-reader data table */}
      <table className="sr-only">
        <caption>보유 종목 히트맵 — 시가총액 비례 크기, 당일 등락률 색상</caption>
        <thead>
          <tr>
            <th>종목명</th>
            <th>티커</th>
            <th>당일 등락률</th>
            <th>평가금액</th>
          </tr>
        </thead>
        <tbody>
          {data.map((d) => (
            <tr key={d.ticker}>
              <td>{d.fullName}</td>
              <td>{d.ticker}</td>
              <td>
                {d.changeRate != null ? `${formatRate(d.changeRate)}%` : "—"}
              </td>
              <td>{formatKRW(d.size)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <ResponsiveContainer width="100%" height={height}>
        <Treemap
          data={data}
          dataKey="size"
          aspectRatio={16 / 5}
          // recharts v3 TreemapDataType 호환을 위해 any 캐스트 필요
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          content={<HeatmapCell palette={palette} /> as any}
        />
      </ResponsiveContainer>
    </div>
  );
}
