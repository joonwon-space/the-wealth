"use client";

import { formatKRW, formatPrice } from "@/lib/format";
import { PnLBadge } from "@/components/PnLBadge";

interface HoldingRow {
  ticker: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number | null;
  market_value: number | null;
  market_value_krw: number | null;
  pnl_amount: number | null;
  pnl_rate: number | null;
  day_change_rate: number | null;
  currency?: "KRW" | "USD";
  portfolio_name?: string | null;
}

interface PerformanceTableProps {
  holdings: HoldingRow[];
  onSelectStock: (ticker: string, name: string) => void;
}

export function PerformanceTable({ holdings, onSelectStock }: PerformanceTableProps) {
  if (holdings.length === 0) return null;

  return (
    <section className="space-y-3">
      <h2 className="text-base font-semibold">종목별 성과</h2>

      {/* Mobile card view */}
      <div className="space-y-3 md:hidden">
        {holdings.map((h, i) => (
          <button
            key={`${h.ticker}-${i}`}
            className="w-full text-left rounded-lg border p-3 space-y-2 active:bg-accent/50 hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            onClick={() => onSelectStock(h.ticker, h.name)}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-sm">{h.name}</div>
                <div className="text-xs text-muted-foreground flex items-center gap-1">
                  <span>{h.ticker}</span>
                  {h.portfolio_name && (
                    <span className="rounded bg-muted px-1 text-[10px] font-medium">
                      {h.portfolio_name}
                    </span>
                  )}
                </div>
              </div>
              <PnLBadge value={h.pnl_rate} suffix="%" />
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">수량</span>
                <span className="tabular-nums">
                  {Number(h.quantity).toLocaleString("ko-KR")}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">현재가</span>
                <span className="tabular-nums">
                  {h.current_price
                    ? formatPrice(h.current_price, h.currency ?? "KRW")
                    : "—"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">평균단가</span>
                <span className="tabular-nums">
                  {formatPrice(h.avg_price, h.currency ?? "KRW")}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">평가금액(₩)</span>
                <span className="tabular-nums">{formatKRW(h.market_value_krw)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">수익금(₩)</span>
                <PnLBadge value={h.pnl_amount} />
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Desktop table view */}
      <div className="hidden md:block overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              {(
                [
                  "종목",
                  "수량",
                  "평균단가",
                  "현재가",
                  "평가금액(₩)",
                  "손익(₩)",
                  "수익률",
                ] as const
              ).map((header) => (
                <th
                  key={header}
                  className="px-4 py-2 text-left font-medium text-muted-foreground"
                >
                  {header}
                </th>
              ))}
              <th className="hidden lg:table-cell px-4 py-2 text-left font-medium text-muted-foreground">
                전일 대비
              </th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h, i) => (
              <tr
                key={`${h.ticker}-${i}`}
                className="border-t cursor-pointer hover:bg-accent/50 focus-visible:outline-none focus-visible:bg-accent/50"
                tabIndex={0}
                onClick={() => onSelectStock(h.ticker, h.name)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectStock(h.ticker, h.name);
                  }
                }}
              >
                <td className="px-4 py-2">
                  <div className="font-medium">{h.name}</div>
                  <div className="text-xs text-muted-foreground flex items-center gap-1">
                    <span>{h.ticker}</span>
                    {h.portfolio_name && (
                      <span className="rounded bg-muted px-1 text-[10px] font-medium">
                        {h.portfolio_name}
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-2 tabular-nums">
                  {Number(h.quantity).toLocaleString("ko-KR")}
                </td>
                <td className="px-4 py-2 tabular-nums">
                  {formatPrice(h.avg_price, h.currency ?? "KRW")}
                </td>
                <td className="px-4 py-2 tabular-nums">
                  {h.current_price
                    ? formatPrice(h.current_price, h.currency ?? "KRW")
                    : "—"}
                </td>
                <td className="px-4 py-2 tabular-nums">{formatKRW(h.market_value_krw)}</td>
                <td className="px-4 py-2">
                  <PnLBadge value={h.pnl_amount} />
                </td>
                <td className="px-4 py-2">
                  <PnLBadge value={h.pnl_rate} suffix="%" />
                </td>
                <td className="hidden lg:table-cell px-4 py-2">
                  {h.day_change_rate != null ? (
                    <PnLBadge value={h.day_change_rate} suffix="%" />
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
