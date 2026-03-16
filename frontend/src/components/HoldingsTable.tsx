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
import { ChevronDown, ChevronUp, ChevronsUpDown } from "lucide-react";
import { PnLBadge } from "@/components/PnLBadge";
import { formatKRW, formatNumber } from "@/lib/format";

interface HoldingRow {
  id: number;
  ticker: string;
  name: string;
  quantity: number | string;
  avg_price: number | string;
  current_price: number | string | null;
  market_value: number | string | null;
  pnl_amount: number | string | null;
  pnl_rate: number | string | null;
}

interface Props {
  holdings: HoldingRow[];
}

const columns: ColumnDef<HoldingRow>[] = [
  {
    accessorKey: "name",
    header: "종목명",
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.name}</div>
        <div className="text-xs text-muted-foreground">{row.original.ticker}</div>
      </div>
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
    cell: ({ getValue }) => <span className="tabular-nums">{formatKRW(getValue() as number)}</span>,
  },
  {
    accessorKey: "current_price",
    header: "현재가",
    cell: ({ getValue }) => {
      const v = getValue() as number | null;
      return <span className="tabular-nums">{formatKRW(v)}</span>;
    },
  },
  {
    accessorKey: "market_value",
    header: "평가금액",
    cell: ({ getValue }) => {
      const v = getValue() as number | null;
      return <span className="tabular-nums">{formatKRW(v)}</span>;
    },
  },
  {
    accessorKey: "pnl_amount",
    header: "수익금",
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
];

export function HoldingsTable({ holdings }: Props) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const table = useReactTable({
    data: holdings,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  onClick={header.column.getToggleSortingHandler()}
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
  );
}
