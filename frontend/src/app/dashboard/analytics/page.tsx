"use client";

import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import { api } from "@/lib/api";
import { formatKRW, formatRate } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PnLBadge } from "@/components/PnLBadge";
import { AllocationDonut } from "@/components/AllocationDonut";

const DONUT_COLORS = ["#e31f26", "#1a56db", "#f59e0b", "#10b981", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];

interface HoldingRow {
  ticker: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number | null;
  market_value: number | null;
  pnl_amount: number | null;
  pnl_rate: number | null;
}

interface AllocationItem {
  ticker: string;
  name: string;
  value: number;
  ratio: number;
}

interface Summary {
  total_asset: number;
  total_invested: number;
  total_pnl_amount: number;
  total_pnl_rate: number;
  holdings: HoldingRow[];
  allocation: AllocationItem[];
}

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Summary>("/dashboard/summary")
      .then(({ data }) => setSummary(data))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-8 w-24" />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}><CardContent className="p-4 space-y-2"><Skeleton className="h-3 w-16" /><Skeleton className="h-6 w-24" /></CardContent></Card>
          ))}
        </div>
      </div>
    );
  }

  if (!summary || (summary.holdings.length === 0 && Number(summary.total_invested) === 0)) {
    return (
      <div className="space-y-8">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
          <BarChart3 className="mb-3 h-12 w-12 text-muted-foreground/40" />
          <p className="text-lg font-semibold">No data yet</p>
          <p className="mt-1 text-sm text-muted-foreground">Add holdings to your portfolios to see analytics.</p>
        </div>
      </div>
    );
  }

  const s = summary;
  const sortedByPnl = [...s.holdings]
    .filter((h) => h.pnl_rate != null)
    .sort((a, b) => Number(b.pnl_rate) - Number(a.pnl_rate));

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Analytics</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Total Assets</p><p className="mt-1 text-lg font-bold tabular-nums">{formatKRW(s.total_asset)}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Total Invested</p><p className="mt-1 text-lg font-bold tabular-nums">{formatKRW(s.total_invested)}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Total P&L</p><p className="mt-1 text-lg font-bold"><PnLBadge value={s.total_pnl_amount} /></p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Return Rate</p><p className="mt-1 text-lg font-bold"><PnLBadge value={s.total_pnl_rate} suffix="%" /></p></CardContent></Card>
      </div>

      {/* Allocation chart */}
      {s.allocation.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-base font-semibold">Asset Allocation</h2>
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
            <AllocationDonut data={s.allocation} totalAsset={s.total_asset} />
            <div className="flex flex-wrap gap-2">
              {s.allocation.map((item, i) => (
                <div key={item.ticker} className="flex items-center gap-1.5 text-xs">
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: DONUT_COLORS[i % DONUT_COLORS.length] }} />
                  <span>{item.name}</span>
                  <span className="text-muted-foreground">{formatRate(item.ratio)}%</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Performance table */}
      {sortedByPnl.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-base font-semibold">Holdings Performance</h2>
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  {["Stock", "Quantity", "Avg Price", "Current", "P&L", "Return"].map((h) => (
                    <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedByPnl.map((h) => (
                  <tr key={h.ticker} className="border-t">
                    <td className="px-4 py-2">
                      <div className="font-medium">{h.name}</div>
                      <div className="text-xs text-muted-foreground">{h.ticker}</div>
                    </td>
                    <td className="px-4 py-2 tabular-nums">{Number(h.quantity).toLocaleString("ko-KR")}</td>
                    <td className="px-4 py-2 tabular-nums">{formatKRW(h.avg_price)}</td>
                    <td className="px-4 py-2 tabular-nums">{h.current_price ? formatKRW(h.current_price) : "—"}</td>
                    <td className="px-4 py-2"><PnLBadge value={h.pnl_amount ?? 0} /></td>
                    <td className="px-4 py-2"><PnLBadge value={h.pnl_rate ?? 0} suffix="%" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
