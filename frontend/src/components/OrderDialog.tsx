"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useCashBalance, usePlaceOrder, useOrderableQuantity } from "@/hooks/useOrders";
import { useDebounce } from "@/hooks/useDebounce";
import { formatKRW } from "@/lib/format";
import { OrderForm } from "@/components/orders/OrderForm";
import { OrderConfirmation } from "@/components/orders/OrderConfirmation";

/** 현재 보유 종목 정보 (portfolio page에서 전달). */
export interface ExistingHolding {
  quantity: string; // Decimal as string
  avg_price: string; // Decimal as string
  pnl_amount: string | null;
  pnl_rate: string | null;
}

interface OrderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  portfolioId: number;
  ticker: string;
  stockName: string;
  currentPrice?: number;
  /** 해외 거래소 코드 (예: "NASD"). 없으면 국내주식으로 간주. */
  exchangeCode?: string;
  /** 현재 포트폴리오에서 이 종목의 보유 정보. 없으면 미보유. */
  existingHolding?: ExistingHolding;
  /** 다이얼로그 열릴 때 기본 탭. 기본값: "BUY". */
  initialTab?: OrderType;
}

type OrderType = "BUY" | "SELL";
type OrderClass = "limit" | "market";

export function OrderDialog({
  open,
  onOpenChange,
  portfolioId,
  ticker,
  stockName,
  currentPrice,
  exchangeCode,
  existingHolding,
  initialTab = "BUY",
}: OrderDialogProps) {
  const [activeTab, setActiveTab] = useState<OrderType>(initialTab);
  const [orderClass, setOrderClass] = useState<OrderClass>("limit");
  const [quantity, setQuantity] = useState<string>("");
  const [price, setPrice] = useState<string>(
    currentPrice ? String(currentPrice) : ""
  );
  const [memo, setMemo] = useState<string>("");
  const [confirmMode, setConfirmMode] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { data: cashBalance } = useCashBalance(portfolioId);
  const placeOrderMutation = usePlaceOrder(portfolioId);

  const parsedQuantity = parseInt(quantity, 10) || 0;
  const parsedPrice = parseFloat(price) || 0;
  const orderAmount = parsedQuantity * parsedPrice;

  const availableCash = cashBalance ? parseFloat(cashBalance.available_cash) : null;
  const totalCash = cashBalance ? parseFloat(cashBalance.total_cash) : null;
  const pendingCash =
    totalCash !== null && availableCash !== null ? totalCash - availableCash : 0;

  const debouncedPrice = useDebounce(parsedPrice, 500);

  const isDomestic = !exchangeCode;
  const isMarketOrder = orderClass === "market";
  const orderablePrice = isMarketOrder ? 0 : debouncedPrice;
  const orderableEnabled =
    isDomestic && activeTab === "BUY" && (isMarketOrder || debouncedPrice > 0);
  const { data: orderable } = useOrderableQuantity(
    portfolioId,
    ticker,
    orderableEnabled ? orderablePrice : -1,
    "BUY"
  );

  const effectivePrice = isMarketOrder ? (currentPrice ?? 0) : parsedPrice;
  const orderableQty = orderable ? Math.floor(parseFloat(orderable.orderable_quantity)) : 0;
  const clientFallbackQty =
    availableCash !== null && effectivePrice > 0
      ? Math.floor(availableCash / effectivePrice)
      : 0;
  const maxBuyQuantity =
    activeTab === "BUY" && (orderableQty > 0 || clientFallbackQty > 0)
      ? Math.max(orderableQty, clientFallbackQty)
      : null;

  // ─── Existing holding data ────────────────────────────────────────────────

  const heldQuantity = existingHolding ? parseFloat(existingHolding.quantity) : 0;
  const heldAvgPrice = existingHolding ? parseFloat(existingHolding.avg_price) : 0;
  const heldPnlAmount = existingHolding?.pnl_amount
    ? parseFloat(existingHolding.pnl_amount)
    : null;
  const heldPnlRate = existingHolding?.pnl_rate
    ? parseFloat(existingHolding.pnl_rate)
    : null;

  // ─── 매수: 추가 매수 후 예상 평단가 ──────────────────────────────────────

  const effectiveBuyPrice = orderClass === "market" ? (currentPrice ?? 0) : parsedPrice;
  const estimatedAvgPrice =
    heldQuantity > 0 && parsedQuantity > 0 && effectiveBuyPrice > 0
      ? (heldQuantity * heldAvgPrice + parsedQuantity * effectiveBuyPrice) /
        (heldQuantity + parsedQuantity)
      : null;
  const avgPriceDiff =
    estimatedAvgPrice !== null ? estimatedAvgPrice - heldAvgPrice : null;

  // ─── 매도: 실현손익 미리보기 ──────────────────────────────────────────────

  const sellEffectivePrice = orderClass === "market" ? (currentPrice ?? 0) : parsedPrice;
  const realizedPnl =
    parsedQuantity > 0 && sellEffectivePrice > 0 && heldAvgPrice > 0
      ? (sellEffectivePrice - heldAvgPrice) * parsedQuantity
      : null;
  const realizedPnlRate =
    realizedPnl !== null && heldAvgPrice > 0
      ? ((sellEffectivePrice - heldAvgPrice) / heldAvgPrice) * 100
      : null;

  // ─── Handlers ─────────────────────────────────────────────────────────────

  function handleQuickQuantity(ratio: number) {
    if (maxBuyQuantity !== null && maxBuyQuantity > 0) {
      setQuantity(String(Math.floor(maxBuyQuantity * ratio)));
    } else if (availableCash && parsedPrice) {
      setQuantity(String(Math.floor((availableCash * ratio) / parsedPrice)));
    }
  }

  function handleMaxQuantity() {
    if (maxBuyQuantity !== null && maxBuyQuantity > 0) {
      setQuantity(String(maxBuyQuantity));
    }
  }

  function handleSellAll() {
    if (heldQuantity > 0) setQuantity(String(Math.floor(heldQuantity)));
  }

  function handleConfirm() {
    if (!parsedQuantity || parsedQuantity <= 0) return;
    if (orderClass === "limit" && (!parsedPrice || parsedPrice <= 0)) return;
    setConfirmMode(true);
  }

  function handleSubmit() {
    const isBuyTab = activeTab === "BUY";

    placeOrderMutation.mutate(
      {
        ticker,
        name: stockName,
        order_type: activeTab,
        order_class: orderClass,
        quantity: parsedQuantity,
        price: orderClass === "market" ? undefined : parsedPrice,
        exchange_code: exchangeCode,
        memo: memo || undefined,
      },
      {
        onSuccess: (result) => {
          let msg: string;
          if (result.status === "failed") {
            msg = `주문 실패: ${result.memo ?? "알 수 없는 오류"}`;
          } else if (isBuyTab && estimatedAvgPrice !== null && heldQuantity > 0) {
            const direction = avgPriceDiff !== null && avgPriceDiff > 0 ? "▲" : "▼";
            msg = `주문 접수 완료 (${result.order_no ?? "-"})\n평단가 ${formatKRW(heldAvgPrice)} → ${formatKRW(estimatedAvgPrice)} ${direction}`;
          } else if (!isBuyTab && realizedPnl !== null) {
            const sign = realizedPnl >= 0 ? "+" : "";
            const rateSign = (realizedPnlRate ?? 0) >= 0 ? "+" : "";
            msg = `주문 접수 완료 (${result.order_no ?? "-"})\n예상 실현손익 ${sign}${formatKRW(realizedPnl)} (${rateSign}${(realizedPnlRate ?? 0).toFixed(1)}%)`;
          } else {
            msg = `주문 접수 완료 (주문번호: ${result.order_no ?? "-"})`;
          }
          setSuccessMessage(msg);
          setConfirmMode(false);
          resetForm();
        },
        onError: (err) => {
          setSuccessMessage(`주문 오류: ${err.message}`);
          setConfirmMode(false);
        },
      }
    );
  }

  function resetForm() {
    setQuantity("");
    setPrice(currentPrice ? String(currentPrice) : "");
    setMemo("");
    setOrderClass("limit");
  }

  function handleClose(open: boolean) {
    if (!open) {
      setConfirmMode(false);
      setSuccessMessage(null);
      resetForm();
    }
    onOpenChange(open);
  }

  const isBuy = activeTab === "BUY";
  // 한국 컬러 컨벤션: 매수=빨간색, 매도=파란색
  const actionColor = isBuy
    ? "bg-red-500 hover:bg-red-600 text-white"
    : "bg-blue-600 hover:bg-blue-700 text-white";
  const labelColor = isBuy ? "text-red-600" : "text-blue-600";

  if (successMessage) {
    return (
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>주문 결과</DialogTitle>
          </DialogHeader>
          <p className="text-sm py-4 whitespace-pre-line">{successMessage}</p>
          {availableCash !== null && (
            <div className="text-xs text-muted-foreground bg-muted/50 rounded px-3 py-2 mb-3">
              잔여 예수금: <span className="font-medium text-foreground">{formatKRW(availableCash)}</span>
              {pendingCash > 0 && (
                <span className="ml-2 text-amber-600">(대기 중: {formatKRW(pendingCash)})</span>
              )}
            </div>
          )}
          <Button onClick={() => handleClose(false)} className="w-full">
            닫기
          </Button>
        </DialogContent>
      </Dialog>
    );
  }

  if (confirmMode) {
    return (
      <OrderConfirmation
        open={open}
        onOpenChange={handleClose}
        stockName={stockName}
        ticker={ticker}
        isBuy={isBuy}
        orderClass={orderClass}
        parsedQuantity={parsedQuantity}
        parsedPrice={parsedPrice}
        orderAmount={orderAmount}
        labelColor={labelColor}
        actionColor={actionColor}
        heldAvgPrice={heldAvgPrice}
        heldQuantity={heldQuantity}
        estimatedAvgPrice={estimatedAvgPrice}
        avgPriceDiff={avgPriceDiff}
        realizedPnl={realizedPnl}
        realizedPnlRate={realizedPnlRate}
        isPending={placeOrderMutation.isPending}
        onSubmit={handleSubmit}
        onCancel={() => setConfirmMode(false)}
      />
    );
  }

  const holdingDisplay =
    heldQuantity > 0
      ? {
          quantity: heldQuantity,
          avgPrice: heldAvgPrice,
          pnlAmount: heldPnlAmount,
          pnlRate: heldPnlRate,
        }
      : null;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>
            {stockName} <span className="text-muted-foreground text-sm">({ticker})</span>
          </DialogTitle>
        </DialogHeader>

        <OrderForm
          activeTab={activeTab}
          onTabChange={setActiveTab}
          orderClass={orderClass}
          onOrderClassChange={setOrderClass}
          quantity={quantity}
          onQuantityChange={setQuantity}
          price={price}
          onPriceChange={setPrice}
          memo={memo}
          onMemoChange={setMemo}
          availableCash={availableCash}
          pendingCash={pendingCash}
          maxBuyQuantity={maxBuyQuantity}
          existingHolding={holdingDisplay}
          parsedQuantity={parsedQuantity}
          parsedPrice={parsedPrice}
          orderAmount={orderAmount}
          estimatedAvgPrice={estimatedAvgPrice}
          avgPriceDiff={avgPriceDiff}
          realizedPnl={realizedPnl}
          realizedPnlRate={realizedPnlRate}
          actionColor={actionColor}
          isError={placeOrderMutation.isError}
          errorMessage={placeOrderMutation.error?.message}
          onConfirm={handleConfirm}
          onMaxQuantity={handleMaxQuantity}
          onSellAll={handleSellAll}
          onQuickQuantity={handleQuickQuantity}
        />
      </DialogContent>
    </Dialog>
  );
}
