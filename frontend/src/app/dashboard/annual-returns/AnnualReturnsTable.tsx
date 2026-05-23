"use client";

import { formatKRW } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AnnualReturnRow } from "./types";

interface Props {
  rows: AnnualReturnRow[];
}

function formatPct(rate: number | null): string {
  if (rate == null) return "—";
  return `${(rate * 100).toFixed(2)}%`;
}

function toneClass(value: number): string {
  if (value > 0) return "text-rose-600";
  if (value < 0) return "text-blue-600";
  return "";
}

export function AnnualReturnsTable({ rows }: Props) {
  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-dashed py-8 text-center text-sm text-muted-foreground">
        과거 거래 내역이 없어 연도별 수익률을 계산할 수 없습니다.
      </div>
    );
  }

  const sorted = [...rows].sort((a, b) => b.year - a.year);

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-xs">
          <tr>
            <th className="px-3 py-2 text-left">연도</th>
            <th className="px-3 py-2 text-right">나이</th>
            <th className="px-3 py-2 text-right">연초 평가</th>
            <th className="px-3 py-2 text-right">적립</th>
            <th className="px-3 py-2 text-right">배당</th>
            <th className="px-3 py-2 text-right">연말 평가</th>
            <th className="px-3 py-2 text-right">연간 수익</th>
            <th className="px-3 py-2 text-right">IRR</th>
            <th className="px-3 py-2 text-right">누적 IRR</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.year} className="border-t">
              <td className="px-3 py-2 font-medium">{r.year}</td>
              <td className="px-3 py-2 text-right tabular-nums">
                {r.age ?? "—"}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatKRW(r.bop_value_krw)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatKRW(r.contributions_krw)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatKRW(r.dividends_krw)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatKRW(r.eop_value_krw)}
              </td>
              <td
                className={cn(
                  "px-3 py-2 text-right tabular-nums",
                  toneClass(r.pnl_amount_krw),
                )}
              >
                {formatKRW(r.pnl_amount_krw)}
              </td>
              <td
                className={cn(
                  "px-3 py-2 text-right tabular-nums",
                  r.irr_year != null ? toneClass(r.irr_year) : "",
                )}
              >
                {formatPct(r.irr_year)}
              </td>
              <td
                className={cn(
                  "px-3 py-2 text-right tabular-nums",
                  r.irr_cumulative != null ? toneClass(r.irr_cumulative) : "",
                )}
              >
                {formatPct(r.irr_cumulative)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
