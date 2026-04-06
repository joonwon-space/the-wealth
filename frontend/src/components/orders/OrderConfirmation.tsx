"use client";

import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { formatKRW } from "@/lib/format";

interface OrderConfirmationProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  stockName: string;
  ticker: string;
  isBuy: boolean;
  orderClass: "limit" | "market";
  parsedQuantity: number;
  parsedPrice: number;
  orderAmount: number;
  labelColor: string;
  actionColor: string;
  /** 매수: 현재 보유수량 > 0일 때 평단가 변화 표시용 */
  heldAvgPrice: number;
  heldQuantity: number;
  estimatedAvgPrice: number | null;
  avgPriceDiff: number | null;
  /** 매도: 예상 실현손익 */
  realizedPnl: number | null;
  realizedPnlRate: number | null;
  isPending: boolean;
  onSubmit: () => void;
  onCancel: () => void;
}

export function OrderConfirmation({
  open,
  onOpenChange,
  stockName,
  ticker,
  isBuy,
  orderClass,
  parsedQuantity,
  parsedPrice,
  orderAmount,
  labelColor,
  actionColor,
  heldAvgPrice,
  heldQuantity,
  estimatedAvgPrice,
  avgPriceDiff,
  realizedPnl,
  realizedPnlRate,
  isPending,
  onSubmit,
  onCancel,
}: OrderConfirmationProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>주문 확인</DialogTitle>
        </DialogHeader>
        <div className="py-4 space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">종목</span>
            <span className="font-medium">{stockName} ({ticker})</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">구분</span>
            <span className={`font-semibold ${labelColor}`}>
              {isBuy ? "매수" : "매도"} ({orderClass === "limit" ? "지정가" : "시장가"})
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">수량</span>
            <span className="font-medium">{parsedQuantity.toLocaleString()}주</span>
          </div>
          {orderClass === "limit" && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">단가</span>
              <span className="font-medium">{formatKRW(parsedPrice)}</span>
            </div>
          )}
          <div className="flex justify-between border-t pt-2">
            <span className="text-muted-foreground">주문금액</span>
            <span className="font-bold">
              {orderClass === "market" ? "시장가" : formatKRW(orderAmount)}
            </span>
          </div>
          {/* 매수: 예상 평단가 */}
          {isBuy && estimatedAvgPrice !== null && heldQuantity > 0 && (
            <div className="flex justify-between text-xs text-muted-foreground border-t pt-2">
              <span>예상 평단가</span>
              <span className={avgPriceDiff !== null && avgPriceDiff > 0 ? "text-red-600" : "text-blue-600"}>
                {formatKRW(heldAvgPrice)} → {formatKRW(estimatedAvgPrice)}
              </span>
            </div>
          )}
          {/* 매도: 예상 실현손익 */}
          {!isBuy && realizedPnl !== null && (
            <div className="flex justify-between text-xs border-t pt-2">
              <span className="text-muted-foreground">예상 실현손익</span>
              <span className={realizedPnl >= 0 ? "text-red-600 font-medium" : "text-blue-600 font-medium"}>
                {realizedPnl >= 0 ? "+" : ""}{formatKRW(realizedPnl)}
                {realizedPnlRate !== null && (
                  <span className="ml-1">
                    ({realizedPnlRate >= 0 ? "+" : ""}{realizedPnlRate.toFixed(1)}%)
                  </span>
                )}
              </span>
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="flex-1"
            onClick={onCancel}
            disabled={isPending}
          >
            취소
          </Button>
          <Button
            className={`flex-1 ${actionColor}`}
            onClick={onSubmit}
            disabled={isPending}
          >
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : null}
            {isBuy ? "매수 확인" : "매도 확인"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
