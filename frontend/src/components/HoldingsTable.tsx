"use client";

import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronUp, ChevronsUpDown } from "lucide-react";
import { PnLBadge } from "@/components/PnLBadge";
import { formatKRW, formatUSD, formatPrice, formatNumber } from "@/lib/format";

interface HoldingRow {
  id: number;
  ticker: string;
  name: string;
  quantity: number | string;
  avg_price: number | string;
  current_price: number | string | null;
  market_value: number | string | null;
  market_value_krw: number | string | null;
  pnl_amount: number | string | null;
  pnl_rate: number | string | null;
  day_change_rate: number | string | null;
  w52_high: number | string | null;
  w52_low: number | string | null;
  currency?: string;
  portfolio_name?: string | null;
}

interface Props {
  holdings: HoldingRow[];
}

// Mini bar indicator for pnl_rate — 0% as center baseline
function PnLBar({ rate }: { rate: number | null }) {
  if (rate == null) return null;
  // Clamp to ±30% for visual scaling
  const clamp = Math.min(Math.max(rate, -30), 30);
  const pct = (Math.abs(clamp) / 30) * 50; // max 50% width from center
  const isPositive = rate >= 0;

  return (
    <div className="relative flex h-1.5 w-15 items-center overflow-hidden rounded-full bg-muted">
      {/* Center divider */}
      <div className="absolute left-1/2 h-full w-px bg-border" />
      {/* Bar fills from center */}
      <div
        className="absolute h-full rounded-full transition-all duration-300"
        style={{
          width: `${pct}%`,
          [isPositive ? "left" : "right"]: "50%",
          background: isPositive ? "var(--rise)" : "var(--fall)",
        }}
      />
    </div>
  );
}

const columns: ColumnDef<HoldingRow>[] = [
  {
    accessorKey: "name",
    header: "종목명",
    cell: ({ row }) => (
      <Link href={`/dashboard/stocks/${row.original.ticker}`} className="hover:underline">
        <div className="font-semibold text-sm leading-tight">{row.original.name}</div>
        <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
          <span>{row.original.ticker}</span>
          {row.original.currency === "USD" && (
            <span className="rounded bg-blue-100 px-1 text-[10px] font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
              해외
            </span>
          )}
          {row.original.portfolio_name && (
            <span className="rounded bg-muted px-1 text-[10px] font-medium text-muted-foreground">
              {row.original.portfolio_name}
            </span>
          )}
        </div>
      </Link>
    ),
  },
  {
    accessorKey: "avg_price",
    header: "평균단가",
    meta: { className: "hidden sm:table-cell" },
    cell: ({ row }) => (
      <span className="tabular-nums text-sm">
        {formatPrice(row.original.avg_price, (row.original.currency as "KRW" | "USD") || "KRW")}
      </span>
    ),
  },
  {
    accessorKey: "current_price",
    header: "현재가",
    cell: ({ row }) => {
      const v = row.original.current_price as number | null;
      return (
        <span className="tabular-nums text-sm">
          {formatPrice(v, (row.original.currency as "KRW" | "USD") || "KRW")}
        </span>
      );
    },
  },
  {
    accessorKey: "market_value_krw",
    header: "평가금액(₩)",
    meta: { className: "hidden md:table-cell" },
    cell: ({ row }) => {
      const v = row.original.market_value_krw as number | null;
      return <span className="tabular-nums text-sm">{formatKRW(v)}</span>;
    },
  },
  {
    accessorKey: "pnl_amount",
    header: "수익금(₩)",
    meta: { className: "hidden md:table-cell" },
    cell: ({ getValue }) => {
      const v = getValue() as number | null;
      return v != null ? <PnLBadge value={v} /> : <span className="text-muted-foreground">—</span>;
    },
  },
  {
    accessorKey: "pnl_rate",
    header: "수익률",
    cell: ({ getValue }) => {
      const v = getValue() as number | null;
      return (
        <div className="flex flex-col gap-1">
          {v != null ? <PnLBadge value={v} suffix="%" /> : <span className="text-muted-foreground">—</span>}
          <PnLBar rate={v} />
        </div>
      );
    },
  },
  {
    accessorKey: "day_change_rate",
    header: "전일 대비",
    meta: { className: "hidden lg:table-cell" },
    cell: ({ getValue }) => {
      const v = getValue() as number | null;
      return v != null ? <PnLBadge value={v} suffix="%" /> : <span className="text-muted-foreground">—</span>;
    },
  },
  {
    id: "w52_range",
    header: "52주 범위",
    enableSorting: false,
    meta: { className: "hidden lg:table-cell" },
    cell: ({ row }) => {
      const isUSD = row.original.currency === "USD";
      const high = Number(row.original.w52_high);
      const low = Number(row.original.w52_low);
      const cur = Number(row.original.current_price);
      const avg = Number(row.original.avg_price);
      if (!high || !low || !cur || high <= low) return <span className="text-muted-foreground">—</span>;
      const curPct = Math.min(Math.max(((cur - low) / (high - low)) * 100, 0), 100);
      // avg_price marker: only show if within the 52-week range
      const avgPct = avg > 0 && avg >= low && avg <= high
        ? ((avg - low) / (high - low)) * 100
        : null;
      const fmt = isUSD ? formatUSD : formatKRW;
      return (
        <div className="w-24 space-y-0.5">
          <div className="relative h-1.5 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="absolute left-0 top-0 h-full rounded-full"
              style={{ width: `${curPct}%`, background: "var(--accent-indigo)" }}
            />
            {avgPct != null && (
              <div
                className="absolute top-0 h-full w-px bg-white/90"
                style={{ left: `${avgPct}%` }}
                title={`평균매입가: ${fmt(avg)}`}
              />
            )}
          </div>
          <div className="flex justify-between text-[10px] text-muted-foreground tabular-nums">
            <span>{fmt(low)}</span>
            <span>{fmt(high)}</span>
          </div>
        </div>
      );
    },
  },
];

// Get row background tinting based on day_change_rate
function getRowTint(dayChangeRate: number | string | null): string {
  if (dayChangeRate == null) return "";
  const v = Number(dayChangeRate);
  if (v > 0) return "bg-red-50/80 dark:bg-red-950/30";
  if (v < 0) return "bg-blue-50/80 dark:bg-blue-950/30";
  return "";
}

export function HoldingsTable({ holdings }: Props) {
  const [sorting, setSorting] = useState<SortingState>([{ id: "market_value_krw", desc: true }]);

  const table = useReactTable({
    data: holdings,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <>
      {/* Mobile card view */}
      <div className="space-y-3 md:hidden">
        {table.getRowModel().rows.map((row) => {
          const h = row.original;
          const currency = (h.currency as "KRW" | "USD") || "KRW";
          const tint = getRowTint(h.day_change_rate);
          return (
            <div key={row.id} className={`rounded-lg border p-3 space-y-2 transition-colors ${tint}`}>
              <div className="flex items-center justify-between">
                <Link href={`/dashboard/stocks/${h.ticker}`} className="hover:underline">
                  <div className="font-semibold text-sm leading-tight">{h.name}</div>
                  <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                    <span>{h.ticker}</span>
                    {currency === "USD" && (
                      <span className="rounded bg-blue-100 px-1 text-[10px] font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                        해외
                      </span>
                    )}
                    {h.portfolio_name && (
                      <span className="rounded bg-muted px-1 text-[10px] font-medium text-muted-foreground">
                        {h.portfolio_name}
                      </span>
                    )}
                  </div>
                </Link>
                <div className="text-right space-y-0.5">
                  {h.pnl_rate != null ? (
                    <div className="flex flex-col items-end gap-1">
                      <PnLBadge value={h.pnl_rate} suffix="%" />
                      <PnLBar rate={Number(h.pnl_rate)} />
                    </div>
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                  {h.day_change_rate != null && (
                    <div className="text-xs text-muted-foreground">
                      전일 <PnLBadge value={Number(h.day_change_rate)} suffix="%" />
                    </div>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">수량</span>
                  <span className="tabular-nums">{formatNumber(h.quantity)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">현재가</span>
                  <span className="tabular-nums">{formatPrice(h.current_price, currency)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">평균단가</span>
                  <span className="tabular-nums">{formatPrice(h.avg_price, currency)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">평가금액(₩)</span>
                  <span className="tabular-nums">{formatKRW(h.market_value_krw)}</span>
                </div>
              </div>
              {h.pnl_amount != null && (
                <div className="flex justify-between text-xs border-t pt-2">
                  <span className="text-muted-foreground">수익금(₩)</span>
                  <PnLBadge value={h.pnl_amount} />
                </div>
              )}
            </div>
          );
        })}
        {holdings.length === 0 && (
          <div className="py-8 text-center text-sm text-muted-foreground">보유 종목이 없습니다.</div>
        )}
      </div>

      {/* Desktop table view */}
      <div className="hidden md:block overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    tabIndex={0}
                    onClick={header.column.getToggleSortingHandler()}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        header.column.getToggleSortingHandler()?.(e);
                      }
                    }}
                    aria-sort={
                      header.column.getIsSorted() === "asc"
                        ? "ascending"
                        : header.column.getIsSorted() === "desc"
                          ? "descending"
                          : "none"
                    }
                    className={`cursor-pointer select-none px-4 py-3 text-left font-medium text-muted-foreground text-section-header ${(header.column.columnDef.meta as { className?: string } | undefined)?.className ?? ""}`}
                  >
                    <div className="flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getCanSort() && (
                        <span className="text-muted-foreground/50">
                          {header.column.getIsSorted() === "asc" ? (
                            <ChevronUp className="h-3 w-3" />
                          ) : header.column.getIsSorted() === "desc" ? (
                            <ChevronDown className="h-3 w-3" />
                          ) : (
                            <ChevronsUpDown className="h-3 w-3" />
                          )}
                        </span>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => {
              const tint = getRowTint(row.original.day_change_rate);
              return (
                <tr
                  key={row.id}
                  className={`border-t transition-colors hover:bg-muted/30 ${tint}`}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className={`px-4 py-3 ${(cell.column.columnDef.meta as { className?: string } | undefined)?.className ?? ""}`}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
        {holdings.length === 0 && (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">보유 종목이 없습니다.</div>
        )}
      </div>
    </>
  );
}
