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
import { haptic } from "@/lib/haptic";

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
  // priceInput이 null이면 prop의 currentPrice를 default로 사용한다.
  // 사용자가 input을 수정하는 순간 string으로 전환되어 prop 변경의 영향을 받지 않는다.
  // (Effect 없이 derived state로 "최신 prop 추적 + 사용자 편집 보호" 둘 다 달성)
  const [priceInput, setPriceInput] = useState<string | null>(null);
  const price =
    priceInput ?? (currentPrice && currentPrice > 0 ? String(currentPrice) : "");
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
  // Raw USD foreign cash (not KRW-converted). Used for fallback max-quantity
  // on overseas orders so we don't divide a KRW total by a USD price.
  const foreignCash =
    cashBalance?.foreign_cash != null ? parseFloat(cashBalance.foreign_cash) : null;

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
  // 국내주식: KIS의 orderable_quantity가 가장 정확. raw 잔액 기반 client 계산은
  // 미체결 외의 묶임(출금예약·신용한도·연금정책 등)을 모르므로 절대 KIS 응답을
  // 위로 덮으면 안 된다 (Math.max 금지 — KIS=0주여도 client 계산이 13주면 13주로
  // 잘못 표시되던 버그).
  // 해외주식: KIS가 orderable 엔드포인트를 노출하지 않으므로 client fallback 사용.
  const clientFallbackQty =
    !isDomestic && foreignCash !== null && effectivePrice > 0
      ? Math.floor(foreignCash / effectivePrice)
      : 0;
  let maxBuyQuantity: number | null = null;
  if (activeTab === "BUY") {
    if (isDomestic) {
      // KIS 응답 도착 전엔 null (수치 미표시) → 부풀린 추정 차단
      maxBuyQuantity = orderable !== undefined ? orderableQty : null;
    } else {
      maxBuyQuantity = clientFallbackQty > 0 ? clientFallbackQty : null;
    }
  }

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
    // OrderForm은 maxBuyQuantity > 0 일 때만 quick 버튼을 렌더하므로
    // 여기 도달 시점에는 항상 양수가 보장된다.
    if (maxBuyQuantity !== null && maxBuyQuantity > 0) {
      setQuantity(String(Math.floor(maxBuyQuantity * ratio)));
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

  function getApiErrorMessage(err: unknown): string {
    if (err && typeof err === "object") {
      const e = err as Record<string, unknown>;
      const data = (e.response as Record<string, unknown> | undefined)?.data;
      if (data && typeof data === "object") {
        const d = data as Record<string, unknown>;
        if (d.error && typeof d.error === "object") {
          const msg = (d.error as Record<string, unknown>).message;
          if (typeof msg === "string") return msg;
        }
        if (typeof d.detail === "string") return d.detail;
      }
    }
    return "주문 처리 중 오류가 발생했습니다";
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
          haptic.success();
        },
        onError: (err) => {
          setSuccessMessage(`주문 오류: ${getApiErrorMessage(err)}`);
          setConfirmMode(false);
          haptic.warning();
        },
      }
    );
  }

  function resetForm() {
    setQuantity("");
    setPriceInput(null);
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
  // 한국 컬러 컨벤션: 매수=빨간색(--rise), 매도=파란색(--fall)
  const actionColor = isBuy
    ? "bg-rise hover:bg-rise/90 text-white"
    : "bg-fall hover:bg-fall/90 text-white";
  const labelColor = isBuy ? "text-rise" : "text-fall";

  if (successMessage) {
    return (
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="max-w-md" mobileSheet>
          <DialogHeader>
            <DialogTitle>주문 결과</DialogTitle>
          </DialogHeader>
          <p className="text-sm py-4 whitespace-pre-line">{successMessage}</p>
          {availableCash !== null && (
            <div className="text-xs text-muted-foreground bg-muted/50 rounded px-3 py-2 mb-3">
              잔여 예수금: <span className="font-medium text-foreground">{formatKRW(availableCash)}</span>
              {pendingCash > 0 && (
                <span className="ml-2 text-accent-amber">(대기 중: {formatKRW(pendingCash)})</span>
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
        currency={isDomestic ? "KRW" : "USD"}
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
      <DialogContent className="max-w-sm" mobileSheet>
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
          onPriceChange={setPriceInput}
          memo={memo}
          onMemoChange={setMemo}
          availableCash={isDomestic ? availableCash : foreignCash}
          pendingCash={isDomestic ? pendingCash : 0}
          cashCurrency={isDomestic ? "KRW" : "USD"}
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
          errorMessage={placeOrderMutation.isError ? getApiErrorMessage(placeOrderMutation.error) : undefined}
          onConfirm={handleConfirm}
          onMaxQuantity={handleMaxQuantity}
          onSellAll={handleSellAll}
          onQuickQuantity={handleQuickQuantity}
        />
      </DialogContent>
    </Dialog>
  );
}
