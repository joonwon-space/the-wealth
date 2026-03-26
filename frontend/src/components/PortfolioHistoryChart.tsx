"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from "recharts";
import { formatKRW } from "@/lib/format";

interface HistoryPoint {
  date: string;
  value: number;
}

interface Props {
  data: HistoryPoint[];
  period: "1W" | "1M" | "3M" | "6M" | "1Y" | "ALL";
  onPeriodChange: (p: Props["period"]) => void;
  /** Optional invested amount at the beginning of the period (for reference line) */
  initialInvested?: number;
}

const PERIODS: Props["period"][] = ["1W", "1M", "3M", "6M", "1Y", "ALL"];

function filterByPeriod(data: HistoryPoint[], period: Props["period"]): HistoryPoint[] {
  if (period === "ALL" || data.length === 0) return data;
  const now = new Date();
  const cutoff = new Date(now);
  if (period === "1W") cutoff.setDate(now.getDate() - 7);
  else if (period === "1M") cutoff.setMonth(now.getMonth() - 1);
  else if (period === "3M") cutoff.setMonth(now.getMonth() - 3);
  else if (period === "6M") cutoff.setMonth(now.getMonth() - 6);
  else if (period === "1Y") cutoff.setFullYear(now.getFullYear() - 1);
  return data.filter((d) => new Date(d.date) >= cutoff);
}

interface CustomTooltipProps {
  active?: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload?: any[];
  label?: string;
  gain: number;
}

function CustomTooltip({ active, payload, label, gain }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const value = payload[0].value as number;
  const gainPct = gain;
  const isPositive = gainPct >= 0;
  return (
    <div className="rounded-lg border bg-popover px-3 py-2.5 text-xs shadow-md space-y-1">
      <p className="text-muted-foreground font-medium">{label}</p>
      <p className="font-bold tabular-nums text-foreground">{formatKRW(value)}</p>
      <p
        className="tabular-nums font-medium"
        style={{ color: isPositive ? "var(--rise)" : "var(--fall)" }}
      >
        {isPositive ? "+" : ""}
        {gainPct.toFixed(2)}%
      </p>
    </div>
  );
}

export function PortfolioHistoryChart({ data, period, onPeriodChange }: Props) {
  const filtered = filterByPeriod(data, period);

  if (data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        스냅샷 데이터가 쌓이면 표시됩니다.
      </p>
    );
  }

  const first = filtered[0]?.value ?? 0;
  const last = filtered[filtered.length - 1]?.value ?? 0;
  const gain = first > 0 ? ((last - first) / first) * 100 : 0;

  // Positive: dodger blue; Negative: fall blue
  const lineColor = gain >= 0 ? "#1e90ff" : "#1A56DB";
  const gradientId = `historyGrad-${gain >= 0 ? "pos" : "neg"}`;

  // Compute per-point gain for tooltip
  function pointGain(value: number): number {
    return first > 0 ? ((value - first) / first) * 100 : 0;
  }

  return (
    <div className="space-y-3">
      {/* Period selector + period gain badge */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => onPeriodChange(p)}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                period === p
                  ? "text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
              style={period === p ? { background: "var(--accent-indigo)" } : undefined}
            >
              {p}
            </button>
          ))}
        </div>
        {filtered.length > 1 && (
          <span
            className="text-xs font-semibold tabular-nums"
            style={{ color: gain >= 0 ? "var(--rise)" : "var(--fall)" }}
          >
            {gain >= 0 ? "+" : ""}
            {gain.toFixed(2)}%
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={filtered} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={lineColor} stopOpacity={0.25} />
              <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="currentColor" strokeOpacity={0.08} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10 }}
            tickFormatter={(v: string) => v.slice(5)}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 10 }}
            tickFormatter={(v: number) =>
              v >= 1_000_000 ? `${(v / 1_000_000).toFixed(0)}M` : `${(v / 1_000).toFixed(0)}K`
            }
            tickLine={false}
            axisLine={false}
            width={48}
          />
          <Tooltip
            content={({ active, payload, label }) => (
              <CustomTooltip
                active={active}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                payload={payload as any[]}
                label={typeof label === "string" ? label : undefined}
                gain={payload?.[0]?.value != null ? pointGain(Number(payload[0].value)) : 0}
              />
            )}
          />
          {/* Reference line at the first point value */}
          {first > 0 && (
            <ReferenceLine
              y={first}
              stroke={lineColor}
              strokeDasharray="4 4"
              strokeOpacity={0.4}
              strokeWidth={1}
            />
          )}
          <Area
            type="monotone"
            dataKey="value"
            stroke={lineColor}
            strokeWidth={2.5}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0, fill: lineColor }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
