"use client";

import { useState } from "react";
import { Loader2, AlertCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCashBalance, usePlaceOrder, useOrderableQuantity } from "@/hooks/useOrders";
import { useDebounce } from "@/hooks/useDebounce";
import { formatKRW } from "@/lib/format";

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

const QUICK_RATIOS = [0.1, 0.25, 0.5, 1.0] as const;

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

  const availableCash = cashBalance
    ? parseFloat(cashBalance.available_cash)
    : null;

  const totalCash = cashBalance
    ? parseFloat(cashBalance.total_cash)
    : null;

  // 대기 중 금액 (총 예수금 - 사용가능 예수금)
  const pendingCash =
    totalCash !== null && availableCash !== null
      ? totalCash - availableCash
      : 0;

  // 가격 입력 debounce (500ms) → orderable API 호출 빈도 제한
  const debouncedPrice = useDebounce(parsedPrice, 500);

  // 국내 매수 시 orderable API 호출
  // - 지정가: debouncedPrice > 0 일 때
  // - 시장가: price=0으로 호출 (KIS가 시장가 기준 수량 반환)
  const isDomestic = !exchangeCode;
  const isMarketOrder = orderClass === "market";
  const orderablePrice = isMarketOrder ? 0 : debouncedPrice;
  const orderableEnabled =
    isDomestic && activeTab === "BUY" && (isMarketOrder || debouncedPrice > 0);
  const { data: orderable, isError: orderableError } = useOrderableQuantity(
    portfolioId,
    ticker,
    orderableEnabled ? orderablePrice : -1,
    "BUY"
  );

  // 최대 매수 가능 수량
  // 1순위: orderable API 응답
  // 2순위(fallback): 클라이언트 계산 (API 실패 또는 해외주식)
  const orderableQty = orderable
    ? Math.floor(parseFloat(orderable.orderable_quantity))
    : null;
  const clientFallbackQty =
    availableCash !== null && parsedPrice > 0
      ? Math.floor(availableCash / parsedPrice)
      : null;

  const maxBuyQuantity =
    orderableEnabled && orderableQty !== null && orderableQty > 0
      ? orderableQty
      : orderableEnabled && orderableError && clientFallbackQty !== null
        ? clientFallbackQty
        : !orderableEnabled && clientFallbackQty !== null
          ? clientFallbackQty
          : null;

  // ─── Existing holding data ────────────────────────────────────────────────

  const heldQuantity = existingHolding
    ? parseFloat(existingHolding.quantity)
    : 0;
  const heldAvgPrice = existingHolding
    ? parseFloat(existingHolding.avg_price)
    : 0;
  const heldPnlAmount = existingHolding?.pnl_amount
    ? parseFloat(existingHolding.pnl_amount)
    : null;
  const heldPnlRate = existingHolding?.pnl_rate
    ? parseFloat(existingHolding.pnl_rate)
    : null;

  // ─── 매수: 추가 매수 후 예상 평단가 계산 ─────────────────────────────────

  const effectiveBuyPrice =
    orderClass === "market" ? (currentPrice ?? 0) : parsedPrice;

  const estimatedAvgPrice =
    heldQuantity > 0 && parsedQuantity > 0 && effectiveBuyPrice > 0
      ? (heldQuantity * heldAvgPrice + parsedQuantity * effectiveBuyPrice) /
        (heldQuantity + parsedQuantity)
      : null;

  const avgPriceDiff =
    estimatedAvgPrice !== null
      ? estimatedAvgPrice - heldAvgPrice
      : null;

  // ─── 매도: 실현손익 미리보기 ──────────────────────────────────────────────

  const sellEffectivePrice =
    orderClass === "market" ? (currentPrice ?? 0) : parsedPrice;

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
      const qty = Math.floor(maxBuyQuantity * ratio);
      setQuantity(String(qty));
    } else if (availableCash && parsedPrice) {
      const qty = Math.floor((availableCash * ratio) / parsedPrice);
      setQuantity(String(qty));
    }
  }

  function handleMaxQuantity() {
    if (maxBuyQuantity !== null && maxBuyQuantity > 0) {
      setQuantity(String(maxBuyQuantity));
    }
  }

  function handleSellAll() {
    if (heldQuantity > 0) {
      setQuantity(String(Math.floor(heldQuantity)));
    }
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
      <Dialog open={open} onOpenChange={handleClose}>
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
              onClick={() => setConfirmMode(false)}
              disabled={placeOrderMutation.isPending}
            >
              취소
            </Button>
            <Button
              className={`flex-1 ${actionColor}`}
              onClick={handleSubmit}
              disabled={placeOrderMutation.isPending}
            >
              {placeOrderMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-1" />
              ) : null}
              {isBuy ? "매수 확인" : "매도 확인"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>
            {stockName} <span className="text-muted-foreground text-sm">({ticker})</span>
          </DialogTitle>
        </DialogHeader>

        {/* 현재 보유 정보 */}
        {existingHolding && heldQuantity > 0 && (
          <div className="rounded-md bg-muted/50 px-3 py-2 text-xs space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">현재 보유</span>
              <span className="font-medium">{Math.floor(heldQuantity).toLocaleString()}주 @ {formatKRW(heldAvgPrice)}</span>
            </div>
            {heldPnlAmount !== null && heldPnlRate !== null && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">평가손익</span>
                <span className={heldPnlAmount >= 0 ? "font-medium text-red-600" : "font-medium text-blue-600"}>
                  {heldPnlAmount >= 0 ? "+" : ""}{formatKRW(heldPnlAmount)}
                  {" "}({heldPnlRate >= 0 ? "+" : ""}{heldPnlRate.toFixed(1)}%)
                </span>
              </div>
            )}
          </div>
        )}

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as OrderType)}>
          <TabsList className="w-full">
            <TabsTrigger value="BUY" className="flex-1 data-[state=active]:text-red-600">
              매수
            </TabsTrigger>
            <TabsTrigger value="SELL" className="flex-1 data-[state=active]:text-blue-600">
              매도
            </TabsTrigger>
          </TabsList>

          {(["BUY", "SELL"] as const).map((tab) => (
            <TabsContent key={tab} value={tab} className="space-y-3 mt-3">
              {/* 주문 유형 */}
              <div className="flex gap-2">
                <Button
                  variant={orderClass === "limit" ? "default" : "outline"}
                  size="sm"
                  className="flex-1"
                  onClick={() => setOrderClass("limit")}
                >
                  지정가
                </Button>
                <Button
                  variant={orderClass === "market" ? "default" : "outline"}
                  size="sm"
                  className="flex-1"
                  onClick={() => setOrderClass("market")}
                >
                  시장가
                </Button>
              </div>

              {/* 예수금 표시 */}
              {availableCash !== null && (
                <div className="text-xs text-muted-foreground space-y-0.5">
                  <div className="flex justify-between">
                    <span>사용가능 예수금</span>
                    <span className="font-medium">{formatKRW(availableCash)}</span>
                  </div>
                  {pendingCash > 0 && (
                    <div className="flex justify-between text-amber-600">
                      <span>체결 대기 중</span>
                      <span className="font-medium">{formatKRW(pendingCash)}</span>
                    </div>
                  )}
                  {tab === "BUY" && maxBuyQuantity !== null && maxBuyQuantity > 0 && (
                    <div className="flex justify-between items-center">
                      <span>최대 매수 가능</span>
                      <button
                        type="button"
                        onClick={handleMaxQuantity}
                        className="font-medium text-red-600 hover:text-red-800 underline underline-offset-2"
                      >
                        {maxBuyQuantity.toLocaleString()}주
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* 단가 입력 (지정가만) */}
              {orderClass === "limit" && (
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">
                    단가 (원)
                  </label>
                  <Input
                    type="number"
                    placeholder="주문 단가"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    min={0}
                  />
                </div>
              )}

              {/* 수량 입력 */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs text-muted-foreground">
                    수량 (주)
                  </label>
                  {/* 매수: 최대 수량 버튼 */}
                  {tab === "BUY" && maxBuyQuantity !== null && maxBuyQuantity > 0 && (
                    <button
                      type="button"
                      onClick={handleMaxQuantity}
                      className="text-xs text-red-600 hover:text-red-800 font-medium"
                    >
                      최대 ({maxBuyQuantity.toLocaleString()}주)
                    </button>
                  )}
                  {/* 전량 매도 버튼 (매도 탭 + 보유 있을 때만) */}
                  {tab === "SELL" && heldQuantity > 0 && (
                    <button
                      type="button"
                      onClick={handleSellAll}
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                    >
                      전량 ({Math.floor(heldQuantity).toLocaleString()}주)
                    </button>
                  )}
                </div>
                <Input
                  type="number"
                  placeholder="주문 수량"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  min={1}
                  step={1}
                />
              </div>

              {/* 퀵 수량 버튼 (매수 + 최대 수량 있을 때) */}
              {tab === "BUY" && maxBuyQuantity !== null && maxBuyQuantity > 0 && (
                <div className="flex gap-1">
                  {QUICK_RATIOS.map((ratio) => (
                    <Button
                      key={ratio}
                      variant="outline"
                      size="sm"
                      className="flex-1 text-xs"
                      onClick={() => handleQuickQuantity(ratio)}
                    >
                      {ratio * 100}%
                    </Button>
                  ))}
                </div>
              )}

              {/* 매수: 예상 평단가 미리보기 */}
              {tab === "BUY" && estimatedAvgPrice !== null && heldQuantity > 0 && parsedQuantity > 0 && (
                <div className="flex justify-between text-xs border rounded px-2 py-1.5 bg-muted/30">
                  <span className="text-muted-foreground">추가 매수 후 평단가</span>
                  <span className={avgPriceDiff !== null && avgPriceDiff > 0 ? "text-red-600 font-medium" : "text-blue-600 font-medium"}>
                    {formatKRW(heldAvgPrice)} → {formatKRW(estimatedAvgPrice)}
                    {avgPriceDiff !== null && (
                      <span className="ml-1 text-muted-foreground">
                        ({avgPriceDiff > 0 ? "+" : ""}{formatKRW(Math.abs(avgPriceDiff))})
                      </span>
                    )}
                  </span>
                </div>
              )}

              {/* 매도: 실현손익 미리보기 */}
              {tab === "SELL" && realizedPnl !== null && parsedQuantity > 0 && (
                <div className="flex justify-between text-xs border rounded px-2 py-1.5 bg-muted/30">
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

              {/* 주문금액 표시 */}
              {parsedQuantity > 0 && orderClass === "limit" && parsedPrice > 0 && (
                <div className="flex justify-between text-sm border-t pt-2">
                  <span className="text-muted-foreground">주문금액</span>
                  <span className="font-semibold">{formatKRW(orderAmount)}</span>
                </div>
              )}

              {/* 메모 */}
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">
                  메모 (선택)
                </label>
                <Input
                  type="text"
                  placeholder="거래 메모"
                  value={memo}
                  onChange={(e) => setMemo(e.target.value)}
                  maxLength={500}
                />
              </div>

              {/* 에러 */}
              {placeOrderMutation.isError && (
                <div className="flex items-center gap-2 text-xs text-destructive">
                  <AlertCircle className="h-3 w-3" />
                  <span>{placeOrderMutation.error?.message}</span>
                </div>
              )}

              {/* 주문 버튼 */}
              <Button
                className={`w-full ${actionColor}`}
                onClick={handleConfirm}
                disabled={
                  parsedQuantity <= 0 ||
                  (orderClass === "limit" && parsedPrice <= 0)
                }
              >
                {tab === "BUY" ? "매수" : "매도"} 주문
              </Button>
            </TabsContent>
          ))}
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
