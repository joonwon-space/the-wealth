"use client";

import { Cell, Pie, PieChart, Tooltip } from "recharts";
import { formatKRW } from "@/lib/format";

interface SectorAllocationItem {
  sector: string;
  value: number;
  weight: number;
}

interface Props {
  data: SectorAllocationItem[];
}

const SECTOR_COLORS: Record<string, string> = {
  "IT": "#1a56db",
  "금융": "#10b981",
  "헬스케어": "#e31f26",
  "에너지/화학": "#f59e0b",
  "자동차": "#8b5cf6",
  "소비재": "#ec4899",
  "통신": "#14b8a6",
  "건설": "#f97316",
  "산업재": "#06b6d4",
  "ETF": "#84cc16",
  "기타": "#9ca3af",
};

const SIZE = 240;

export function SectorAllocationChart({ data }: Props) {
  const numericData = data.map((item) => ({
    ...item,
    value: Number(item.value),
    weight: Number(item.weight),
  }));

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
      <div className="flex-shrink-0">
        <PieChart width={SIZE} height={SIZE}>
          <Pie
            data={numericData}
            cx="50%"
            cy="50%"
            innerRadius={70}
            outerRadius={110}
            paddingAngle={2}
            dataKey="value"
            nameKey="sector"
          >
            {numericData.map((item, index) => (
              <Cell
                key={index}
                fill={SECTOR_COLORS[item.sector] ?? "#9ca3af"}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value, _name, props) => [
              `${formatKRW(value as number)} (${props.payload?.weight?.toFixed(1)}%)`,
              props.payload?.sector ?? "섹터",
            ]}
          />
        </PieChart>
      </div>

      {/* 범례 */}
      <div className="flex flex-wrap content-start gap-x-4 gap-y-2 pt-2">
        {numericData.map((item, i) => (
          <div key={i} className="flex items-center gap-1.5 text-xs">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full flex-shrink-0"
              style={{ background: SECTOR_COLORS[item.sector] ?? "#9ca3af" }}
            />
            <span className="font-medium">{item.sector}</span>
            <span className="text-muted-foreground">{item.weight.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
