"use client";

import { Cell, Pie, PieChart, Tooltip } from "recharts";
import { formatKRW } from "@/lib/format";

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

const COLORS = ["#e31f26", "#1a56db", "#f59e0b", "#10b981", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];
const SIZE = 240;

export function AllocationDonut({ data, totalAsset }: Props) {
  // API may return numeric strings from Decimal fields — coerce to numbers
  const numericData = data.map((item) => ({ ...item, value: Number(item.value), ratio: Number(item.ratio) }));

  return (
    <div className="relative flex items-center justify-center" style={{ width: SIZE, height: SIZE }}>
      <PieChart width={SIZE} height={SIZE}>
        <Pie
          data={numericData}
          cx="50%"
          cy="50%"
          innerRadius={70}
          outerRadius={110}
          paddingAngle={2}
          dataKey="value"
        >
          {data.map((_, index) => (
            <Cell key={index} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value) => [formatKRW(value as number), "평가금액"]}
        />
      </PieChart>

      {/* 중앙 텍스트 오버레이 */}
      <div className="pointer-events-none absolute flex flex-col items-center justify-center">
        <span className="text-xs text-muted-foreground">총 자산</span>
        <span className="text-lg font-bold tabular-nums">
          {formatKRW(totalAsset)}
        </span>
      </div>
    </div>
  );
}
