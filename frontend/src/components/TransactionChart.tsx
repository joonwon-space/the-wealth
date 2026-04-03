"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatKRW } from "@/lib/format";

interface TxnRow {
  type: string;
  quantity: string;
  price: string;
  traded_at: string;
}

interface Props {
  transactions: TxnRow[];
}

interface MonthlyData {
  month: string;
  buy: number;
  sell: number;
}

function aggregateByMonth(txns: TxnRow[]): MonthlyData[] {
  const map = new Map<string, { buy: number; sell: number }>();

  for (const t of txns) {
    const date = new Date(t.traded_at);
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
    const entry = map.get(key) ?? { buy: 0, sell: 0 };
    const amount = Number(t.quantity) * Number(t.price);
    if (t.type === "BUY") {
      entry.buy += amount;
    } else {
      entry.sell += amount;
    }
    map.set(key, entry);
  }

  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, data]) => ({ month, ...data }));
}

export function TransactionChart({ transactions }: Props) {
  const data = aggregateByMonth(transactions);

  if (data.length === 0) return null;

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%" aria-label="거래 내역 차트">
        <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis dataKey="month" tick={{ fontSize: 12 }} className="fill-muted-foreground" />
          <YAxis
            tick={{ fontSize: 11 }}
            tickFormatter={(v) => `${(v / 10000).toFixed(0)}만`}
            className="fill-muted-foreground"
          />
          <Tooltip
            formatter={(value, name) => [
              formatKRW(value as number),
              name === "buy" ? "Buy" : "Sell",
            ]}
          />
          <Legend formatter={(value) => (value === "buy" ? "매수" : "매도")} />
          <Bar dataKey="buy" fill="#e31f26" radius={[4, 4, 0, 0]} />
          <Bar dataKey="sell" fill="#1a56db" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
