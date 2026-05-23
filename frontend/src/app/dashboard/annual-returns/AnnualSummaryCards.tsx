"use client";

import { Card, CardContent } from "@/components/ui/card";
import { formatKRW } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AnnualReturnRow } from "./types";

interface Props {
  rows: AnnualReturnRow[];
}

interface Stat {
  label: string;
  value: string;
  tone?: "gain" | "loss" | "neutral";
}

function buildStats(rows: AnnualReturnRow[]): Stat[] {
  if (rows.length === 0) {
    return [
      { label: "누적 IRR", value: "—" },
      { label: "총 적립액", value: "—" },
      { label: "현재 평가액", value: "—" },
      { label: "누적 평가차익", value: "—" },
    ];
  }
  const latest = rows[rows.length - 1];
  const totalContrib = rows.reduce((s, r) => s + r.contributions_krw, 0);
  const totalDividends = rows.reduce((s, r) => s + r.dividends_krw, 0);
  const pnl = latest.eop_value_krw - totalContrib + totalDividends;
  const irrCum = latest.irr_cumulative;

  return [
    {
      label: "누적 IRR",
      value: irrCum == null ? "—" : `${(irrCum * 100).toFixed(2)}%`,
      tone: irrCum == null ? "neutral" : irrCum >= 0 ? "gain" : "loss",
    },
    { label: "총 적립액", value: formatKRW(totalContrib) },
    { label: "현재 평가액", value: formatKRW(latest.eop_value_krw) },
    {
      label: "누적 평가차익",
      value: formatKRW(pnl),
      tone: pnl >= 0 ? "gain" : "loss",
    },
  ];
}

export function AnnualSummaryCards({ rows }: Props) {
  const stats = buildStats(rows);
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {stats.map((s) => (
        <Card key={s.label}>
          <CardContent className="p-4 space-y-1">
            <p className="text-xs text-muted-foreground">{s.label}</p>
            <p
              className={cn(
                "text-lg font-semibold tabular-nums",
                s.tone === "gain" && "text-rose-600",
                s.tone === "loss" && "text-blue-600",
              )}
            >
              {s.value}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
