"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatKRW } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { SimulationPoint } from "./types";

interface Props {
  points: SimulationPoint[];
  retirementAge: number;
}

function formatAxis(value: number): string {
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}억`;
  if (value >= 10_000) return `${(value / 10_000).toFixed(0)}만`;
  return value.toString();
}

interface TooltipPayloadItem {
  value?: number;
}

interface TooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string | number;
}

function ChartTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-md">
      <div className="font-semibold">{label}세</div>
      <div className="tabular-nums">{formatKRW(payload[0].value ?? 0)}</div>
    </div>
  );
}

export function SimulationResult({ points, retirementAge }: Props) {
  if (points.length === 0) {
    return (
      <div className="rounded-lg border border-dashed py-8 text-center text-sm text-muted-foreground">
        시뮬레이션을 실행하면 결과가 여기에 표시됩니다.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border p-3">
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={points} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
            <defs>
              <linearGradient id="simFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#e11d48" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#e11d48" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis dataKey="age" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={formatAxis} tick={{ fontSize: 11 }} />
            <Tooltip content={<ChartTooltip />} />
            <ReferenceLine
              x={retirementAge}
              stroke="#64748b"
              strokeDasharray="4 4"
              label={{ value: "은퇴", position: "top", fontSize: 11 }}
            />
            <Area
              type="monotone"
              dataKey="eop_value_krw"
              stroke="#e11d48"
              strokeWidth={2}
              fill="url(#simFill)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-xs">
            <tr>
              <th className="px-3 py-2 text-left">나이</th>
              <th className="px-3 py-2 text-left">연도</th>
              <th className="px-3 py-2 text-right">적립/인출</th>
              <th className="px-3 py-2 text-right">운용 수익</th>
              <th className="px-3 py-2 text-right">연말 평가</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr
                key={p.age}
                className={cn(
                  "border-t",
                  p.age >= retirementAge && "bg-muted/10",
                )}
              >
                <td className="px-3 py-2 font-medium">{p.age}</td>
                <td className="px-3 py-2">{p.year}</td>
                <td
                  className={cn(
                    "px-3 py-2 text-right tabular-nums",
                    p.flow_krw > 0 ? "text-rose-600" : p.flow_krw < 0 ? "text-blue-600" : "",
                  )}
                >
                  {formatKRW(p.flow_krw)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatKRW(p.return_amount_krw)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatKRW(p.eop_value_krw)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
