"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { PackageOpen, RefreshCw, Search } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useHoldingsInlineEdit } from "./useHoldingsInlineEdit";
import { HoldingsTableRow } from "./HoldingsTableRow";
import { formatKRW, formatRate } from "@/lib/format";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { StockSearchDialog } from "@/components/StockSearchDialog";
import type { ExistingHolding } from "@/components/OrderDialog";
import { TableSkeleton } from "@/components/TableSkeleton";

const OrderDialog = dynamic(
  () => import("@/components/OrderDialog").then((m) => ({ default: m.OrderDialog })),
  { ssr: false }
);
import { PageError } from "@/components/PageError";
import { useCashBalance } from "@/hooks/useOrders";
import { toast } from "sonner";
import { TrendingDown, TrendingUp, Wallet } from "lucide-react";

export interface Holding {
  id: number;
  ticker: string;
  name: string;
  quantity: string;
  avg_price: string;
  current_price: string | null;
  market_value: string | null;
  market_value_krw: string | null;
  pnl_amount: string | null;
  pnl_rate: string | null;
  exchange_rate: string | null;
  currency?: "KRW" | "USD";
}

interface AddForm {
  ticker: string;
  name: string;
  quantity: string;
  avg_price: string;
}

const EMPTY_FORM: AddForm = { ticker: "", name: "", quantity: "", avg_price: "" };


export function holdingsKey(portfolioId: number) {
  return ["portfolios", portfolioId, "holdings"] as const;
}

interface HoldingsSectionProps {
  portfolioId: number;
  isKisConnected: boolean;
}

export function HoldingsSection({ portfolioId, isKisConnected }: HoldingsSectionProps) {
  const queryClient = useQueryClient();
  const [searchOpen, setSearchOpen] = useState(false);
  const [addForm, setAddForm] = useState<AddForm | null>(null);
  const [addFormErrors, setAddFormErrors] = useState<{ quantity?: string; avg_price?: string }>({});
  const [orderDialogOpen, setOrderDialogOpen] = useState(false);
  const [orderTicker, setOrderTicker] = useState("");
  const [orderName, setOrderName] = useState("");
  const [orderCurrentPrice, setOrderCurrentPrice] = useState<number | undefined>();
  const [orderInitialTab, setOrderInitialTab] = useState<"BUY" | "SELL">("BUY");
  const [orderExchangeCode, setOrderExchangeCode] = useState<string | undefined>();
  const [orderExistingHolding, setOrderExistingHolding] = useState<ExistingHolding | undefined>();
  const { editId, editForm, isEditPending, startEdit, cancelEdit, setEditFormField, saveEdit } = useHoldingsInlineEdit(portfolioId);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  const { data: cashBalance, isError: cashBalanceError, dataUpdatedAt: cashBalanceUpdatedAt, refetch: refetchCashBalance } = useCashBalance(isKisConnected ? portfolioId : 0);

  const { data: holdings = [], isLoading, isError, error, refetch } = useQuery<Holding[]>({
    queryKey: holdingsKey(portfolioId),
    queryFn: async () => {
      const { data } = await api.get<Holding[]>(`/portfolios/${portfolioId}/holdings/with-prices`);
      return data;
    },
  });

  const summary = useMemo(() => {
    let investedKrw = 0;
    let marketValueKrw = 0;
    let pnlKrw = 0;
    let hasPrices = false;
    for (const h of holdings) {
      const qty = Number(h.quantity);
      const avg = Number(h.avg_price);
      const fx = h.currency === "USD" ? Number(h.exchange_rate ?? 0) || 1 : 1;
      investedKrw += qty * avg * fx;
      if (h.market_value_krw != null) {
        marketValueKrw += Number(h.market_value_krw);
        hasPrices = true;
      }
      if (h.pnl_amount != null) {
        pnlKrw += Number(h.pnl_amount);
      }
    }
    const pnlRate = investedKrw > 0 ? (pnlKrw / investedKrw) * 100 : 0;
    return { investedKrw, marketValueKrw, pnlKrw, pnlRate, hasPrices };
  }, [holdings]);

  const addHoldingMutation = useMutation({
    mutationFn: (form: AddForm) =>
      api.post<Holding>(`/portfolios/${portfolioId}/holdings`, {
        ticker: form.ticker,
        name: form.name,
        quantity: Number(form.quantity),
        avg_price: Number(form.avg_price),
      }).then((r) => r.data),
    onSuccess: (data) => {
      queryClient.setQueryData<Holding[]>(holdingsKey(portfolioId), (prev) =>
        prev ? [...prev, data] : [data]
      );
      setAddForm(null);
    },
    onError: () => {
      toast.error("보유종목 추가에 실패했습니다. 입력 내용을 확인해주세요.");
    },
  });

  const deleteHoldingMutation = useMutation({
    mutationFn: (holdingId: number) => api.delete(`/portfolios/holdings/${holdingId}`),
    onSuccess: (_, holdingId) => {
      queryClient.setQueryData<Holding[]>(holdingsKey(portfolioId), (prev) =>
        prev ? prev.filter((h) => h.id !== holdingId) : []
      );
      setDeleteConfirmId(null);
    },
    onError: () => {
      toast.error("보유종목 삭제에 실패했습니다. 잠시 후 다시 시도해주세요.");
    },
  });

  const handleStockSelect = (ticker: string, name: string) => {
    if (isKisConnected) {
      setOrderTicker(ticker);
      setOrderName(name);
      setOrderCurrentPrice(undefined);
      setOrderDialogOpen(true);
    } else {
      setAddForm({ ...EMPTY_FORM, ticker, name });
    }
  };

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!addForm) return;
    const errors: { quantity?: string; avg_price?: string } = {};
    const qty = Number(addForm.quantity);
    const price = Number(addForm.avg_price);
    if (!addForm.quantity || qty <= 0) {
      errors.quantity = "수량은 0보다 커야 합니다";
    }
    if (!addForm.avg_price || price < 0) {
      errors.avg_price = "가격은 0 이상이어야 합니다";
    }
    setAddFormErrors(errors);
    if (Object.keys(errors).length > 0) return;
    addHoldingMutation.mutate(addForm);
  };

  return (
    <>
      {/* KIS 예수금 요약 */}
      {isKisConnected && (cashBalance || cashBalanceError) && (
        <div className="space-y-1.5">
          {cashBalanceError && (
            <div className="flex items-center gap-2 text-xs text-accent-amber">
              <RefreshCw className="h-3 w-3" />
              <span>잔액 조회 실패 — 마지막 데이터 표시 중</span>
              <button onClick={() => void refetchCashBalance()} className="underline hover:no-underline">
                새로고침
              </button>
            </div>
          )}
          {!cashBalanceError && cashBalanceUpdatedAt > 0 && (
            <div className="text-xs text-muted-foreground text-right">
              업데이트: {new Date(cashBalanceUpdatedAt).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
            </div>
          )}
        </div>
      )}
      {!(isKisConnected && cashBalance) && holdings.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="rounded-lg border p-3">
            <div className="text-xs text-muted-foreground mb-1">총 매입원가</div>
            <div className="font-semibold text-sm">{formatKRW(summary.investedKrw)}</div>
          </div>
          <div className="rounded-lg border p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              <TrendingUp className="h-3.5 w-3.5" />
              총 평가금액
            </div>
            <div className="font-semibold text-sm">
              {summary.hasPrices ? formatKRW(summary.marketValueKrw) : "-"}
            </div>
            {!summary.hasPrices && (
              <div className="text-[10px] text-muted-foreground">현재가 미조회</div>
            )}
          </div>
          <div className="rounded-lg border p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              {summary.pnlKrw >= 0 ? (
                <TrendingUp className="h-3.5 w-3.5 text-rise" />
              ) : (
                <TrendingDown className="h-3.5 w-3.5 text-fall" />
              )}
              평가손익
            </div>
            {summary.hasPrices ? (
              <>
                <div className={`font-semibold text-sm ${summary.pnlKrw >= 0 ? "text-rise" : "text-fall"}`}>
                  {summary.pnlKrw >= 0 ? "+" : ""}{formatKRW(summary.pnlKrw)}
                </div>
                <div className={`text-xs ${summary.pnlRate >= 0 ? "text-rise" : "text-fall"}`}>
                  {summary.pnlRate > 0 ? "+" : ""}{formatRate(summary.pnlRate)}%
                </div>
              </>
            ) : (
              <div className="font-semibold text-sm text-muted-foreground">-</div>
            )}
          </div>
        </div>
      )}
      {isKisConnected && cashBalance && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-lg border p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              <Wallet className="h-3.5 w-3.5" />
              예수금
            </div>
            <div className="font-semibold text-sm">{formatKRW(cashBalance.total_cash)}</div>
            <div className="text-xs text-muted-foreground">사용가능: {formatKRW(cashBalance.available_cash)}</div>
            {Number(cashBalance.total_cash) - Number(cashBalance.available_cash) > 0 && (
              <div className="text-xs text-accent-amber">
                대기 중: {formatKRW(String(Number(cashBalance.total_cash) - Number(cashBalance.available_cash)))}
              </div>
            )}
          </div>
          <div className="rounded-lg border p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              <TrendingUp className="h-3.5 w-3.5" />
              총 평가금액
            </div>
            <div className="font-semibold text-sm">{formatKRW(cashBalance.total_evaluation)}</div>
          </div>
          <div className="rounded-lg border p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              {Number(cashBalance.total_profit_loss) >= 0 ? (
                <TrendingUp className="h-3.5 w-3.5 text-rise" />
              ) : (
                <TrendingDown className="h-3.5 w-3.5 text-fall" />
              )}
              평가손익
            </div>
            <div className={`font-semibold text-sm ${Number(cashBalance.total_profit_loss) >= 0 ? "text-rise" : "text-fall"}`}>
              {Number(cashBalance.total_profit_loss) >= 0 ? "+" : ""}{formatKRW(cashBalance.total_profit_loss)}
            </div>
            <div className={`text-xs ${Number(cashBalance.profit_loss_rate) >= 0 ? "text-rise" : "text-fall"}`}>
              {Number(cashBalance.profit_loss_rate) > 0 ? "+" : ""}{formatRate(cashBalance.profit_loss_rate)}%
            </div>
          </div>
          <div className="rounded-lg border p-3">
            <div className="text-xs text-muted-foreground mb-1">총 자산</div>
            <div className="font-semibold text-sm">
              {formatKRW(String(Number(cashBalance.total_cash) + Number(cashBalance.total_evaluation)))}
            </div>
          </div>
        </div>
      )}

      {/* Holdings table */}
      {isLoading ? (
        <TableSkeleton rows={4} columns={6} />
      ) : isError ? (
        <PageError
          message={error instanceof Error ? error.message : "보유 종목을 불러올 수 없습니다"}
          onRetry={() => refetch()}
        />
      ) : holdings.length === 0 && !addForm ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
          <PackageOpen className="mb-3 h-10 w-10 text-muted-foreground/40" />
          {isKisConnected ? (
            <>
              <p className="font-medium">KIS 계좌가 연결됐지만 아직 동기화되지 않았습니다</p>
              <p className="mt-1 text-sm text-muted-foreground">실계좌 보유 종목을 불러오려면 동기화를 실행하세요.</p>
            </>
          ) : (
            <>
              <p className="font-medium">보유 종목이 없습니다</p>
              <p className="mt-1 text-sm text-muted-foreground">종목을 검색해서 추가해보세요.</p>
              <Button onClick={() => setSearchOpen(true)} className="mt-4 gap-2">
                <Search className="h-4 w-4" />
                종목 검색
              </Button>
            </>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex justify-end">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setSearchOpen(true)}
              disabled={!!addForm}
              className="gap-2"
            >
              <Search className="h-4 w-4" />
              종목 추가
            </Button>
          </div>
          <div className="overflow-x-auto rounded-xl border">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="bg-muted/50">
              <tr>
                {["종목", "수량", "평균단가", "현재가", "손익 (KRW)", "평가금액 (KRW)", ""].map((h) => (
                  <th key={h} className="whitespace-nowrap px-4 py-3 text-left font-medium text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...holdings]
                .sort((a, b) => Number(b.market_value_krw ?? 0) - Number(a.market_value_krw ?? 0))
                .map((h) => (
                  <HoldingsTableRow
                    key={h.id}
                    holding={h}
                    isKisConnected={isKisConnected}
                    isEditing={editId === h.id}
                    editForm={editForm}
                    isEditPending={isEditPending}
                    onStartEdit={startEdit}
                    onCancelEdit={cancelEdit}
                    onEditFormFieldChange={setEditFormField}
                    onSaveEdit={saveEdit}
                    onRequestDelete={setDeleteConfirmId}
                    onOpenOrder={(ticker, name, currentPrice, initialTab, exchangeCode, existingHolding) => {
                      setOrderTicker(ticker);
                      setOrderName(name);
                      setOrderCurrentPrice(currentPrice);
                      setOrderInitialTab(initialTab);
                      setOrderExchangeCode(exchangeCode);
                      setOrderExistingHolding(existingHolding);
                      setOrderDialogOpen(true);
                    }}
                  />
                ))}

              {/* 종목 추가 폼 행 */}
              {addForm && (
                <tr className="border-t bg-muted/10">
                  <td className="px-4 py-2">
                    <div className="font-medium">{addForm.name}</div>
                    <div className="text-xs text-muted-foreground">{addForm.ticker}</div>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex flex-col gap-1">
                      <input
                        type="number"
                        inputMode="numeric"
                        placeholder="수량"
                        value={addForm.quantity}
                        onChange={(e) => {
                          setAddForm((f) => f ? { ...f, quantity: e.target.value } : f);
                          setAddFormErrors((prev) => ({ ...prev, quantity: undefined }));
                        }}
                        className="w-24 h-8"
                        aria-invalid={!!addFormErrors.quantity}
                      />
                      {addFormErrors.quantity && (
                        <span className="text-[10px] text-destructive">{addFormErrors.quantity}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex flex-col gap-1">
                      <input
                        type="number"
                        inputMode="decimal"
                        placeholder="평균단가"
                        value={addForm.avg_price}
                        onChange={(e) => {
                          setAddForm((f) => f ? { ...f, avg_price: e.target.value } : f);
                          setAddFormErrors((prev) => ({ ...prev, avg_price: undefined }));
                        }}
                        className="w-28 h-8"
                        aria-invalid={!!addFormErrors.avg_price}
                      />
                      {addFormErrors.avg_price && (
                        <span className="text-[10px] text-destructive">{addFormErrors.avg_price}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={handleAdd}
                        disabled={addHoldingMutation.isPending || !addForm.quantity || !addForm.avg_price}
                      >
                        추가
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => { setAddForm(null); setAddFormErrors({}); }}>취소</Button>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {/* 보유종목 삭제 확인 */}
      <AlertDialog
        open={deleteConfirmId !== null}
        onOpenChange={(open) => { if (!open) setDeleteConfirmId(null); }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>종목을 삭제하시겠습니까?</AlertDialogTitle>
            <AlertDialogDescription>
              이 작업은 되돌릴 수 없습니다. 관련 거래내역도 모두 삭제됩니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                if (deleteConfirmId !== null) {
                  deleteHoldingMutation.mutate(deleteConfirmId);
                }
              }}
            >
              {deleteHoldingMutation.isPending ? "삭제 중..." : "삭제"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Stock search dialog */}
      <StockSearchDialog
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelect={handleStockSelect}
      />

      {/* Order dialog */}
      {isKisConnected && (
        <OrderDialog
          key={`${orderTicker}-${orderInitialTab}`}
          open={orderDialogOpen}
          onOpenChange={setOrderDialogOpen}
          portfolioId={portfolioId}
          ticker={orderTicker}
          stockName={orderName}
          currentPrice={orderCurrentPrice}
          initialTab={orderInitialTab}
          exchangeCode={orderExchangeCode}
          existingHolding={orderExistingHolding}
        />
      )}
    </>
  );
}
