"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatKRW } from "@/lib/format";
import type { AnnualReturnRow } from "./types";

interface Props {
  rows: AnnualReturnRow[];
}

function formatAxis(value: number): string {
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}억`;
  if (value >= 10_000) return `${(value / 10_000).toFixed(0)}만`;
  return value.toString();
}

interface TooltipPayloadItem {
  dataKey?: string;
  value?: number;
  color?: string;
}

interface TooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string | number;
}

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-md space-y-1">
      <div className="font-semibold">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span
            className="inline-block size-2 rounded-sm"
            style={{ background: p.color }}
          />
          <span className="text-muted-foreground">
            {p.dataKey === "eop_value_krw" ? "연말 평가" : "연간 적립"}
          </span>
          <span className="ml-auto tabular-nums">
            {formatKRW(p.value ?? 0)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function AnnualReturnsChart({ rows }: Props) {
  if (rows.length === 0) return null;
  const data = [...rows].sort((a, b) => a.year - b.year);

  return (
    <div className="rounded-lg border p-3">
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis dataKey="year" tick={{ fontSize: 11 }} />
          <YAxis
            yAxisId="left"
            tickFormatter={formatAxis}
            tick={{ fontSize: 11 }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tickFormatter={formatAxis}
            tick={{ fontSize: 11 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar
            yAxisId="right"
            dataKey="contributions_krw"
            name="연간 적립"
            fill="#94a3b8"
            radius={[3, 3, 0, 0]}
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="eop_value_krw"
            name="연말 평가"
            stroke="#e11d48"
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
