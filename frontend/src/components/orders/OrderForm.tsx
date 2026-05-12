"use client";

import { AlertCircle } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatKRW } from "@/lib/format";

type OrderType = "BUY" | "SELL";
type OrderClass = "limit" | "market";

const QUICK_RATIOS = [0.1, 0.25, 0.5, 1.0] as const;

interface ExistingHoldingDisplay {
  quantity: number;
  avgPrice: number;
  pnlAmount: number | null;
  pnlRate: number | null;
}

interface OrderFormProps {
  activeTab: OrderType;
  onTabChange: (tab: OrderType) => void;
  orderClass: OrderClass;
  onOrderClassChange: (cls: OrderClass) => void;
  quantity: string;
  onQuantityChange: (v: string) => void;
  price: string;
  onPriceChange: (v: string) => void;
  memo: string;
  onMemoChange: (v: string) => void;

  availableCash: number | null;
  pendingCash: number;
  /**
   * Currency the cash figures are denominated in. KRW for domestic orders,
   * USD for overseas — keeps the displayed amount in the same units as the
   * price the user is entering, so 사용가능 예수금 doesn't show ₩2M when the
   * user only has $1,300 in USD.
   */
  cashCurrency?: "KRW" | "USD";
  maxBuyQuantity: number | null;
  existingHolding: ExistingHoldingDisplay | null;

  parsedQuantity: number;
  parsedPrice: number;
  orderAmount: number;
  estimatedAvgPrice: number | null;
  avgPriceDiff: number | null;
  realizedPnl: number | null;
  realizedPnlRate: number | null;

  actionColor: string;
  isError: boolean;
  errorMessage: string | undefined;

  onConfirm: () => void;
  onMaxQuantity: () => void;
  onSellAll: () => void;
  onQuickQuantity: (ratio: number) => void;
}

export function OrderForm({
  activeTab,
  onTabChange,
  orderClass,
  onOrderClassChange,
  quantity,
  onQuantityChange,
  price,
  onPriceChange,
  memo,
  onMemoChange,
  availableCash,
  pendingCash,
  cashCurrency = "KRW",
  maxBuyQuantity,
  existingHolding,
  parsedQuantity,
  parsedPrice,
  orderAmount,
  estimatedAvgPrice,
  avgPriceDiff,
  realizedPnl,
  realizedPnlRate,
  actionColor,
  isError,
  errorMessage,
  onConfirm,
  onMaxQuantity,
  onSellAll,
  onQuickQuantity,
}: OrderFormProps) {
  const heldQuantity = existingHolding?.quantity ?? 0;
  const heldAvgPrice = existingHolding?.avgPrice ?? 0;
  const heldPnlAmount = existingHolding?.pnlAmount ?? null;
  const heldPnlRate = existingHolding?.pnlRate ?? null;

  const formatCash = (n: number) =>
    cashCurrency === "USD"
      ? `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : formatKRW(n);

  return (
    <>
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
              <span className={heldPnlAmount >= 0 ? "font-medium text-rise" : "font-medium text-fall"}>
                {heldPnlAmount >= 0 ? "+" : ""}{formatKRW(heldPnlAmount)}
                {" "}({heldPnlRate >= 0 ? "+" : ""}{heldPnlRate.toFixed(1)}%)
              </span>
            </div>
          )}
        </div>
      )}

      <Tabs value={activeTab} onValueChange={(v) => onTabChange(v as OrderType)}>
        <TabsList className="w-full">
          <TabsTrigger value="BUY" className="flex-1 data-[state=active]:text-rise">
            매수
          </TabsTrigger>
          <TabsTrigger value="SELL" className="flex-1 data-[state=active]:text-fall">
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
                onClick={() => onOrderClassChange("limit")}
              >
                지정가
              </Button>
              <Button
                variant={orderClass === "market" ? "default" : "outline"}
                size="sm"
                className="flex-1"
                onClick={() => onOrderClassChange("market")}
              >
                시장가
              </Button>
            </div>

            {/* 예수금 표시 */}
            {availableCash !== null && (
              <div className="text-xs text-muted-foreground space-y-0.5">
                <div className="flex justify-between">
                  <span>사용가능 예수금</span>
                  <span className="font-medium">{formatCash(availableCash)}</span>
                </div>
                {pendingCash > 0 && (
                  <div className="flex justify-between text-accent-amber">
                    <span>체결 대기 중</span>
                    <span className="font-medium">{formatCash(pendingCash)}</span>
                  </div>
                )}
                {tab === "BUY" && maxBuyQuantity !== null && maxBuyQuantity > 0 && (
                  <div className="flex justify-between items-center">
                    <span>최대 매수 가능</span>
                    <button
                      type="button"
                      onClick={onMaxQuantity}
                      className="font-medium text-rise hover:opacity-80 underline underline-offset-2"
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
                  단가 ({cashCurrency === "USD" ? "$" : "원"})
                </label>
                <Input
                  type="number"
                  placeholder="주문 단가"
                  value={price}
                  onChange={(e) => onPriceChange(e.target.value)}
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
                {tab === "BUY" && maxBuyQuantity !== null && maxBuyQuantity > 0 && (
                  <button
                    type="button"
                    onClick={onMaxQuantity}
                    className="text-xs text-rise hover:opacity-80 font-medium"
                  >
                    최대 ({maxBuyQuantity.toLocaleString()}주)
                  </button>
                )}
                {tab === "SELL" && heldQuantity > 0 && (
                  <button
                    type="button"
                    onClick={onSellAll}
                    className="text-xs text-fall hover:opacity-80 font-medium"
                  >
                    전량 ({Math.floor(heldQuantity).toLocaleString()}주)
                  </button>
                )}
              </div>
              <Input
                type="number"
                placeholder="주문 수량"
                value={quantity}
                onChange={(e) => onQuantityChange(e.target.value)}
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
                    onClick={() => onQuickQuantity(ratio)}
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
                <span className={avgPriceDiff !== null && avgPriceDiff > 0 ? "text-rise font-medium" : "text-fall font-medium"}>
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
                <span className={realizedPnl >= 0 ? "text-rise font-medium" : "text-fall font-medium"}>
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
                <span className="font-semibold">{formatCash(orderAmount)}</span>
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
                onChange={(e) => onMemoChange(e.target.value)}
                maxLength={500}
              />
            </div>

            {/* 에러 */}
            {isError && (
              <div className="flex items-center gap-2 text-xs text-destructive">
                <AlertCircle className="h-3 w-3" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* 주문 버튼 */}
            <Button
              className={`w-full ${actionColor}`}
              onClick={onConfirm}
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
    </>
  );
}
