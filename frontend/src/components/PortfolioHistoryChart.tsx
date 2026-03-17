"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatKRW } from "@/lib/format";

interface HistoryPoint {
  date: string;
  value: number;
}

interface Props {
  data: HistoryPoint[];
  period: "1M" | "3M" | "6M" | "1Y" | "ALL";
  onPeriodChange: (p: Props["period"]) => void;
}

const PERIODS: Props["period"][] = ["1M", "3M", "6M", "1Y", "ALL"];

function filterByPeriod(data: HistoryPoint[], period: Props["period"]): HistoryPoint[] {
  if (period === "ALL" || data.length === 0) return data;
  const now = new Date();
  const cutoff = new Date(now);
  if (period === "1M") cutoff.setMonth(now.getMonth() - 1);
  else if (period === "3M") cutoff.setMonth(now.getMonth() - 3);
  else if (period === "6M") cutoff.setMonth(now.getMonth() - 6);
  else if (period === "1Y") cutoff.setFullYear(now.getFullYear() - 1);
  return data.filter((d) => new Date(d.date) >= cutoff);
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-background px-3 py-2 text-xs shadow-md">
      <p className="text-muted-foreground">{label}</p>
      <p className="font-semibold tabular-nums">{formatKRW(payload[0].value)}</p>
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
  const lineColor = gain >= 0 ? "#e31f26" : "#1a56db";

  return (
    <div className="space-y-3">
      {/* Period selector */}
      <div className="flex gap-1">
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => onPeriodChange(p)}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
              period === p
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={filtered} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
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
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="value"
            stroke={lineColor}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
