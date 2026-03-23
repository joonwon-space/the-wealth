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
import { useCashBalance, usePlaceOrder } from "@/hooks/useOrders";
import { formatKRW } from "@/lib/format";

interface OrderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  portfolioId: number;
  ticker: string;
  stockName: string;
  currentPrice?: number;
  /** 해외 거래소 코드 (예: "NASD"). 없으면 국내주식으로 간주. */
  exchangeCode?: string;
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
}: OrderDialogProps) {
  const [activeTab, setActiveTab] = useState<OrderType>("BUY");
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

  function handleQuickQuantity(ratio: number) {
    if (!availableCash || !parsedPrice) return;
    const qty = Math.floor((availableCash * ratio) / parsedPrice);
    setQuantity(String(qty));
  }

  function handleConfirm() {
    if (!parsedQuantity || parsedQuantity <= 0) return;
    if (orderClass === "limit" && (!parsedPrice || parsedPrice <= 0)) return;
    setConfirmMode(true);
  }

  function handleSubmit() {
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
          const msg =
            result.status === "failed"
              ? `주문 실패: ${result.memo ?? "알 수 없는 오류"}`
              : `주문 접수 완료 (주문번호: ${result.order_no ?? "-"})`;
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
          <p className="text-sm py-4">{successMessage}</p>
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
                <div className="text-xs text-muted-foreground flex justify-between">
                  <span>사용가능 예수금</span>
                  <span className="font-medium">{formatKRW(availableCash)}</span>
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
                <label className="text-xs text-muted-foreground mb-1 block">
                  수량 (주)
                </label>
                <Input
                  type="number"
                  placeholder="주문 수량"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  min={1}
                  step={1}
                />
              </div>

              {/* 퀵 수량 버튼 (매수, 지정가, 예수금 있을 때만) */}
              {tab === "BUY" && orderClass === "limit" && availableCash !== null && parsedPrice > 0 && (
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
