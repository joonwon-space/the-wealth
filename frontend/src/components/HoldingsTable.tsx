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
import { formatKRW, formatPrice, formatNumber } from "@/lib/format";

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
}

interface Props {
  holdings: HoldingRow[];
}

const columns: ColumnDef<HoldingRow>[] = [
  {
    accessorKey: "name",
    header: "종목명",
    cell: ({ row }) => (
      <Link href={`/dashboard/stocks/${row.original.ticker}`} className="hover:underline">
        <div className="font-medium">{row.original.name}</div>
        <div className="text-xs text-muted-foreground flex items-center gap-1">
          <span>{row.original.ticker}</span>
          {row.original.currency === "USD" && (
            <span className="rounded bg-blue-100 px-1 text-[10px] font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
              해외
            </span>
          )}
        </div>
      </Link>
    ),
  },
  {
    accessorKey: "quantity",
    header: "수량",
    cell: ({ getValue }) => <span className="tabular-nums">{formatNumber(getValue() as number)}</span>,
  },
  {
    accessorKey: "avg_price",
    header: "평균단가",
    cell: ({ row }) => (
      <span className="tabular-nums">
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
        <span className="tabular-nums">
          {formatPrice(v, (row.original.currency as "KRW" | "USD") || "KRW")}
        </span>
      );
    },
  },
  {
    accessorKey: "market_value_krw",
    header: "평가금액(₩)",
    cell: ({ row }) => {
      const v = row.original.market_value_krw as number | null;
      return <span className="tabular-nums">{formatKRW(v)}</span>;
    },
  },
  {
    accessorKey: "pnl_amount",
    header: "수익금(₩)",
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
      return v != null ? <PnLBadge value={v} suffix="%" /> : <span className="text-muted-foreground">—</span>;
    },
  },
  {
    accessorKey: "day_change_rate",
    header: "전일 대비",
    cell: ({ getValue }) => {
      const v = getValue() as number | null;
      return v != null ? <PnLBadge value={v} suffix="%" /> : <span className="text-muted-foreground">—</span>;
    },
  },
  {
    id: "w52_range",
    header: "52주 범위",
    enableSorting: false,
    cell: ({ row }) => {
      if (row.original.currency === "USD") {
        return <span className="text-muted-foreground">—</span>;
      }
      const high = Number(row.original.w52_high);
      const low = Number(row.original.w52_low);
      const cur = Number(row.original.current_price);
      if (!high || !low || !cur || high <= low) return <span className="text-muted-foreground">—</span>;
      const pct = Math.min(Math.max(((cur - low) / (high - low)) * 100, 0), 100);
      return (
        <div className="w-24 space-y-0.5">
          <div className="relative h-1.5 w-full rounded-full bg-muted overflow-hidden">
            <div className="absolute left-0 top-0 h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
          </div>
          <div className="flex justify-between text-[10px] text-muted-foreground tabular-nums">
            <span>{formatKRW(low)}</span>
            <span>{formatKRW(high)}</span>
          </div>
        </div>
      );
    },
  },
];

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
          return (
            <div key={row.id} className="rounded-lg border p-3 space-y-2">
              <div className="flex items-center justify-between">
                <Link href={`/dashboard/stocks/${h.ticker}`} className="hover:underline">
                  <div className="font-medium text-sm">{h.name}</div>
                  <div className="text-xs text-muted-foreground flex items-center gap-1">
                    <span>{h.ticker}</span>
                    {currency === "USD" && (
                      <span className="rounded bg-blue-100 px-1 text-[10px] font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                        해외
                      </span>
                    )}
                  </div>
                </Link>
                <div className="text-right space-y-0.5">
                  {h.pnl_rate != null ? <PnLBadge value={h.pnl_rate} suffix="%" /> : <span className="text-xs text-muted-foreground">—</span>}
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
                    role="button"
                    tabIndex={0}
                    onClick={header.column.getToggleSortingHandler()}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        header.column.getToggleSortingHandler()?.(e);
                      }
                    }}
                    aria-sort={
                      header.column.getIsSorted() === "asc" ? "ascending" :
                      header.column.getIsSorted() === "desc" ? "descending" : "none"
                    }
                    className="cursor-pointer select-none px-4 py-3 text-left font-medium text-muted-foreground"
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
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-t hover:bg-muted/30 transition-colors">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-4 py-3">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {holdings.length === 0 && (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">보유 종목이 없습니다.</div>
        )}
      </div>
    </>
  );
}
