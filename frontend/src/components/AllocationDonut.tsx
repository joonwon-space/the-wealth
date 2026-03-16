"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

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

export function AllocationDonut({ data, totalAsset }: Props) {
  return (
    <div className="relative flex items-center justify-center">
      <ResponsiveContainer width={240} height={240}>
        <PieChart>
          <Pie
            data={data}
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
            formatter={(value) => [
              `₩${Number(value).toLocaleString("ko-KR")}`,
              "평가금액",
            ]}
          />
        </PieChart>
      </ResponsiveContainer>

      {/* 중앙 텍스트 오버레이 */}
      <div className="pointer-events-none absolute flex flex-col items-center justify-center">
        <span className="text-xs text-muted-foreground">총 자산</span>
        <span className="text-lg font-bold tabular-nums">
          ₩{totalAsset.toLocaleString("ko-KR")}
        </span>
      </div>
    </div>
  );
}
