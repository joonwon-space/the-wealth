"use client";

import { TrendingUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { formatRate } from "@/lib/format";

interface HoldingRow {
  id: number;
  ticker: string;
  name: string;
  pnl_rate: number | null;
  market_value_krw: number | null;
}

interface TopHoldingsWidgetProps {
  holdings: HoldingRow[];
}

export function TopHoldingsWidget({ holdings }: TopHoldingsWidgetProps) {
  // Sort by pnl_rate descending, take top 3
  const top3 = [...holdings]
    .filter((h) => h.pnl_rate != null)
    .sort((a, b) => (b.pnl_rate ?? 0) - (a.pnl_rate ?? 0))
    .slice(0, 3);

  if (top3.length === 0) return null;

  // Calculate max absolute pnl_rate for bar scaling
  const maxAbs = Math.max(...top3.map((h) => Math.abs(h.pnl_rate ?? 0)), 1);

  return (
    <section className="space-y-1.5">
      <div className="flex items-center gap-1.5">
        <TrendingUp className="h-3 w-3 text-muted-foreground" />
        <h2 className="text-xs font-medium text-muted-foreground">수익 상위 3종목</h2>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {top3.map((h, idx) => {
          const rate = h.pnl_rate ?? 0;
          const isPositive = rate >= 0;
          const barWidth = Math.min(100, (Math.abs(rate) / maxAbs) * 100);

          return (
            <Card key={h.id} className="relative overflow-hidden bg-card/80">
              {/* rank badge */}
              <div className="absolute top-1.5 right-1.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-muted text-[9px] font-bold text-muted-foreground">
                {idx + 1}
              </div>
              <CardContent className="p-2 pr-5">
                <p className="font-medium text-[11px] leading-tight truncate">{h.name}</p>
                <p className="text-[9px] text-muted-foreground tabular-nums mt-0.5">{h.ticker}</p>
                <p
                  className="mt-1 text-sm font-bold tabular-nums"
                  style={{ color: isPositive ? "var(--rise)" : "var(--fall)" }}
                >
                  {isPositive ? "+" : ""}
                  {formatRate(rate)}%
                </p>
                {/* mini bar indicator */}
                <div className="mt-1 h-0.5 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${barWidth}%`,
                      background: isPositive ? "var(--rise)" : "var(--fall)",
                    }}
                  />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
