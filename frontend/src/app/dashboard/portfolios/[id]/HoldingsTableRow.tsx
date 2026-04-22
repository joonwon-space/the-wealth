"use client";

import { Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { PnLBadge } from "@/components/PnLBadge";
import { formatKRW, formatNumber, formatPrice, formatRate } from "@/lib/format";
import type { Holding } from "./HoldingsSection";
import type { ExistingHolding } from "@/components/OrderDialog";

function formatUSD(value: string | number | null | undefined): string {
  if (value == null) return "—";
  const num = Number(value);
  if (isNaN(num)) return "—";
  return `$${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export interface HoldingsTableRowProps {
  holding: Holding;
  isKisConnected: boolean;
  // Inline edit
  isEditing: boolean;
  editForm: { quantity: string; avg_price: string };
  isEditPending: boolean;
  onStartEdit: (holding: Holding) => void;
  onCancelEdit: () => void;
  onEditFormFieldChange: (field: "quantity" | "avg_price", value: string) => void;
  onSaveEdit: (holdingId: number) => void;
  // Delete
  onRequestDelete: (holdingId: number) => void;
  // Order dialog
  onOpenOrder: (
    ticker: string,
    name: string,
    currentPrice: number | undefined,
    initialTab: "BUY" | "SELL",
    exchangeCode: string | undefined,
    existingHolding: ExistingHolding
  ) => void;
}

export function HoldingsTableRow({
  holding: h,
  isKisConnected,
  isEditing,
  editForm,
  isEditPending,
  onStartEdit,
  onCancelEdit,
  onEditFormFieldChange,
  onSaveEdit,
  onRequestDelete,
  onOpenOrder,
}: HoldingsTableRowProps) {
  const isUSD = h.currency === "USD";

  const handleOpenOrder = (tab: "BUY" | "SELL") => {
    const exchangeCode = isUSD
      ? h.ticker.includes(".")
        ? h.ticker.split(".")[1]
        : "NASD"
      : undefined;
    onOpenOrder(
      h.ticker,
      h.name,
      h.current_price ? Number(h.current_price) : undefined,
      tab,
      exchangeCode,
      { quantity: h.quantity, avg_price: h.avg_price, pnl_amount: h.pnl_amount, pnl_rate: h.pnl_rate }
    );
  };

  return (
    <tr className="border-t hover:bg-muted/20">
      {isEditing ? (
        <>
          <td className="px-4 py-2">
            <div className="font-medium">{h.name}</div>
            <div className="text-xs text-muted-foreground">{h.ticker}</div>
          </td>
          <td className="px-4 py-2">
            <Input
              type="number"
              value={editForm.quantity}
              onChange={(e) => onEditFormFieldChange("quantity", e.target.value)}
              className="w-24 h-8"
            />
          </td>
          <td className="px-4 py-2">
            <Input
              type="number"
              value={editForm.avg_price}
              onChange={(e) => onEditFormFieldChange("avg_price", e.target.value)}
              className="w-28 h-8"
            />
          </td>
          <td className="px-4 py-2">
            <div className="flex gap-2">
              <Button size="sm" onClick={() => onSaveEdit(h.id)} disabled={isEditPending}>저장</Button>
              <Button size="sm" variant="outline" onClick={onCancelEdit}>취소</Button>
            </div>
          </td>
        </>
      ) : (
        <>
          <td className="px-4 py-3">
            <div className="font-medium">{h.name}</div>
            <div className="text-xs text-muted-foreground">
              {h.ticker}
              {isUSD && (
                <span className="ml-1 rounded bg-accent px-1 text-accent-foreground">
                  USD
                </span>
              )}
            </div>
          </td>
          <td className="px-4 py-3 tabular-nums">{formatNumber(h.quantity)}</td>
          <td className="px-4 py-3 tabular-nums">
            {isUSD ? formatUSD(h.avg_price) : formatPrice(h.avg_price, "KRW")}
          </td>
          <td className="px-4 py-3 tabular-nums">
            {h.current_price ? (
              <div>
                <span>{isUSD ? formatUSD(h.current_price) : formatPrice(h.current_price, "KRW")}</span>
                {isUSD && h.exchange_rate && (
                  <div className="text-xs text-muted-foreground">
                    ≈ {formatKRW(String(Number(h.current_price) * Number(h.exchange_rate)))}
                  </div>
                )}
              </div>
            ) : (
              <span className="text-muted-foreground">—</span>
            )}
          </td>
          <td className="px-4 py-3">
            {h.pnl_amount != null ? (
              <div>
                <PnLBadge value={h.pnl_amount} />
                {h.pnl_rate != null && (
                  <div className="text-xs text-muted-foreground">
                    {Number(h.pnl_rate) > 0 ? "+" : ""}{formatRate(h.pnl_rate)}%
                  </div>
                )}
              </div>
            ) : (
              <span className="text-muted-foreground">—</span>
            )}
          </td>
          <td className="px-4 py-3 tabular-nums">
            {h.market_value_krw != null ? (
              <div>
                <span>{formatKRW(h.market_value_krw)}</span>
                {isUSD && h.market_value != null && (
                  <div className="text-xs text-muted-foreground">{formatUSD(h.market_value)}</div>
                )}
              </div>
            ) : (
              <span className="text-muted-foreground">—</span>
            )}
          </td>
          <td className="px-4 py-3">
            <div className="flex gap-1 flex-wrap">
              {isKisConnected && (
                <>
                  <button
                    onClick={() => handleOpenOrder("BUY")}
                    className="rounded border px-2 py-0.5 text-xs font-medium text-rise border-rise/30 hover:bg-rise-soft"
                  >
                    매수
                  </button>
                  <button
                    onClick={() => handleOpenOrder("SELL")}
                    className="rounded border px-2 py-0.5 text-xs font-medium text-fall border-fall/30 hover:bg-fall-soft"
                  >
                    매도
                  </button>
                </>
              )}
              <button
                onClick={() => onStartEdit(h)}
                className="rounded border px-3 py-1 text-xs hover:bg-muted"
              >
                수정
              </button>
              <button
                onClick={() => onRequestDelete(h.id)}
                className="rounded border px-3 py-1 text-xs text-destructive hover:bg-destructive/10"
                aria-label="보유종목 삭제"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          </td>
        </>
      )}
    </tr>
  );
}
