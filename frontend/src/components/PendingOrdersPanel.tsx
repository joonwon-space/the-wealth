"use client";

import { useEffect, useRef } from "react";
import { X, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { usePendingOrders, useCancelOrder, type PendingOrder } from "@/hooks/useOrders";

interface PendingOrdersPanelProps {
  portfolioId: number;
  isOverseas?: boolean;
}

export function PendingOrdersPanel({
  portfolioId,
  isOverseas = false,
}: PendingOrdersPanelProps) {
  const queryClient = useQueryClient();
  const { data: orders = [], isLoading, refetch } = usePendingOrders(
    portfolioId,
    isOverseas
  );
  const cancelMutation = useCancelOrder(portfolioId);

  // Track previously seen order_nos to detect newly filled orders
  const prevOrderNosRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    const currentNos = new Set(orders.map((o) => o.order_no));
    const prevNos = prevOrderNosRef.current;

    // If we had orders before and some have disappeared, they may be filled
    if (prevNos.size > 0) {
      let filledCount = 0;
      for (const prevNo of prevNos) {
        if (!currentNos.has(prevNo)) {
          toast.success(`주문 체결 완료 (주문번호: ${prevNo})`);
          filledCount++;
        }
      }
      // 체결 완료 감지 시 holdings/dashboard 캐시 무효화
      if (filledCount > 0) {
        queryClient.invalidateQueries({ queryKey: ["portfolios", portfolioId, "holdings"] });
        queryClient.invalidateQueries({ queryKey: ["portfolio", portfolioId] });
        queryClient.invalidateQueries({ queryKey: ["dashboard"] });
        queryClient.invalidateQueries({ queryKey: ["cash-balance", portfolioId] });
      }
    }

    prevOrderNosRef.current = currentNos;
  }, [orders, portfolioId, queryClient]);

  function handleCancel(order: PendingOrder) {
    cancelMutation.mutate(
      {
        orderNo: order.order_no,
        ticker: order.ticker,
        quantity: parseInt(order.remaining_quantity, 10),
        price: parseFloat(order.price),
        isOverseas,
      },
      {
        onSuccess: () => {
          toast.success(`주문 취소 완료 (${order.ticker})`);
        },
        onError: (err) => {
          toast.error(`주문 취소 실패: ${err.message}`);
        },
      }
    );
  }

  if (isLoading) {
    return (
      <div className="text-center text-muted-foreground text-sm py-4">
        미체결 주문 로딩 중...
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className="text-center text-muted-foreground text-sm py-4">
        미체결 주문이 없습니다.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">미체결 주문 ({orders.length})</span>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => refetch()}
          className="h-7 w-7 p-0"
          aria-label="새로고침"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </Button>
      </div>
      <div className="rounded-md border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>종목</TableHead>
              <TableHead>구분</TableHead>
              <TableHead className="text-right">수량</TableHead>
              <TableHead className="text-right">단가</TableHead>
              <TableHead className="text-right">체결</TableHead>
              <TableHead className="text-center">취소</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {orders.map((order) => {
              const isBuy = order.order_type === "BUY";
              const typeColor = isBuy ? "text-red-600" : "text-blue-600";
              return (
                <TableRow key={order.order_no}>
                  <TableCell>
                    <div className="font-medium text-sm">{order.name || order.ticker}</div>
                    <div className="text-xs text-muted-foreground">{order.ticker}</div>
                  </TableCell>
                  <TableCell>
                    <span className={`text-sm font-semibold ${typeColor}`}>
                      {isBuy ? "매수" : "매도"}
                    </span>
                    <div className="text-xs text-muted-foreground">
                      {order.order_class === "limit" ? "지정가" : "시장가"}
                    </div>
                  </TableCell>
                  <TableCell className="text-right text-sm">
                    {parseInt(order.quantity, 10).toLocaleString()}주
                  </TableCell>
                  <TableCell className="text-right text-sm">
                    {parseFloat(order.price).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right text-sm">
                    {parseInt(order.filled_quantity, 10).toLocaleString()}주
                  </TableCell>
                  <TableCell className="text-center">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 hover:text-destructive"
                      onClick={() => handleCancel(order)}
                      disabled={cancelMutation.isPending}
                      aria-label="주문 취소"
                    >
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
