"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Plus, Download, TrendingUp, TrendingDown, Wallet, Target, Pencil, Check, X, RefreshCw, Loader2 } from "lucide-react";
import { useQuery, useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatKRW } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { StockSearchDialog } from "@/components/StockSearchDialog";
import { PendingOrdersPanel } from "@/components/PendingOrdersPanel";
import { useCashBalance, usePendingOrders } from "@/hooks/useOrders";
import { toast } from "sonner";
import dynamic from "next/dynamic";
import type { ExistingHolding } from "@/components/OrderDialog";
import { HoldingsSection } from "./HoldingsSection";
import { TransactionSection } from "./TransactionSection";

// Lazy-load OrderDialog: only used when user clicks 매수/매도 button (~20KB deferred)
const OrderDialog = dynamic(
  () => import("@/components/OrderDialog").then((m) => ({ default: m.OrderDialog })),
  { ssr: false }
);

interface PortfolioInfo {
  id: number;
  name: string;
  currency: string;
  kis_account_id: number | null;
  target_value: number | null;
}

interface TxnRow {
  id: number;
  ticker: string;
  type: string;
  quantity: string;
  price: string;
  traded_at: string;
  memo: string | null;
}

interface TxnPage {
  items: TxnRow[];
  next_cursor: number | null;
  has_more: boolean;
}

interface KisTxnRow {
  ticker: string;
  name: string;
  type: string;
  quantity: string;
  price: string;
  total_amount: string;
  traded_at: string;
  market: string;
}

interface Holding {
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

function holdingsKey(portfolioId: number) {
  return ["portfolios", portfolioId, "holdings"] as const;
}

function transactionsKey(portfolioId: number) {
  return ["portfolios", portfolioId, "transactions"] as const;
}

function kisTransactionsKey(portfolioId: number, fromDate: string, toDate: string) {
  return ["portfolios", portfolioId, "kis-transactions", fromDate, toDate] as const;
}

function toYYYYMMDD(date: Date): string {
  return date.toISOString().slice(0, 10).replace(/-/g, "");
}

export default function PortfolioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const portfolioId = Number(id);
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
  const [showPendingOrders, setShowPendingOrders] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<{ quantity: string; avg_price: string }>({ quantity: "", avg_price: "" });
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [showTxnForm, setShowTxnForm] = useState(false);
  const [txnForm, setTxnForm] = useState({ ticker: "", type: "BUY" as "BUY" | "SELL", quantity: "", price: "", traded_at: "" });
  const [deleteTxnId, setDeleteTxnId] = useState<number | null>(null);
  const [editMemoId, setEditMemoId] = useState<number | null>(null);
  const [editMemoValue, setEditMemoValue] = useState<string>("");
  const [editingTarget, setEditingTarget] = useState(false);
  const [targetInputValue, setTargetInputValue] = useState("");
  const [isSyncing, setIsSyncing] = useState(false);

  const handleKisSync = async () => {
    setIsSyncing(true);
    try {
      const { data } = await api.post<{ inserted: number; updated: number; deleted: number }>(
        `/sync/${portfolioId}`
      );
      await queryClient.invalidateQueries({ queryKey: holdingsKey(portfolioId) });
      const total = data.inserted + data.updated + data.deleted;
      toast.success(total > 0 ? `동기화 완료 (+${data.inserted} ~${data.updated} -${data.deleted})` : "이미 최신 상태입니다");
    } catch {
      toast.error("동기화에 실패했습니다. 잠시 후 다시 시도해주세요.");
    } finally {
      setIsSyncing(false);
    }
  };

  // KIS 거래 이력 날짜 범위 (기본: 최근 1개월)
  const today = new Date();
  const oneMonthAgo = new Date(today);
  oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);
  const [kisFromDate, setKisFromDate] = useState(oneMonthAgo.toISOString().slice(0, 10));
  const [kisToDate, setKisToDate] = useState(today.toISOString().slice(0, 10));
  const [showKisHistory, setShowKisHistory] = useState(false);

  const { data: portfolioInfo } = useQuery<PortfolioInfo>({
    queryKey: ["portfolio", portfolioId],
    queryFn: async () => {
      const { data } = await api.get<PortfolioInfo[]>("/portfolios");
      return data.find((p) => p.id === portfolioId) ?? { id: portfolioId, name: "", currency: "KRW", kis_account_id: null, target_value: null };
    },
    staleTime: 60_000,
  });

  const isKisConnected = Boolean(portfolioInfo?.kis_account_id);
  const { data: cashBalance, isError: cashBalanceError, dataUpdatedAt: cashBalanceUpdatedAt, refetch: refetchCashBalance } = useCashBalance(isKisConnected ? portfolioId : 0);
  const { data: pendingOrders = [] } = usePendingOrders(isKisConnected ? portfolioId : 0);

  const { data: holdings = [], isLoading, isError, error, refetch } = useQuery<Holding[]>({
    queryKey: holdingsKey(portfolioId),
    queryFn: async () => {
      const { data } = await api.get<Holding[]>(`/portfolios/${portfolioId}/holdings/with-prices`);
      return data;
    },
  });

  const {
    data: txnPages,
    fetchNextPage: fetchMoreTxns,
    hasNextPage: hasMorTxns,
    isFetchingNextPage: isFetchingMoreTxns,
  } = useInfiniteQuery<TxnPage>({
    queryKey: transactionsKey(portfolioId),
    queryFn: async ({ pageParam }) => {
      const cursor = typeof pageParam === "number" ? pageParam : 0;
      try {
        const { data } = await api.get<TxnPage>(
          `/portfolios/${portfolioId}/transactions/paginated`,
          { params: { cursor, limit: 20 } }
        );
        // Defensive: if API returns array instead of TxnPage envelope, normalize
        if (Array.isArray(data)) {
          return { items: data as unknown as TxnRow[], next_cursor: null, has_more: false };
        }
        return data;
      } catch {
        return { items: [], next_cursor: null, has_more: false };
      }
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) =>
      lastPage.has_more && lastPage.next_cursor != null ? lastPage.next_cursor : undefined,
  });

  const transactions = txnPages?.pages.flatMap((p) => p.items) ?? [];

  const { data: kisTransactions, isLoading: kisLoading, refetch: kisRefetch } = useQuery<KisTxnRow[]>({
    queryKey: kisTransactionsKey(portfolioId, kisFromDate, kisToDate),
    queryFn: async () => {
      const { data } = await api.get<KisTxnRow[]>(`/portfolios/${portfolioId}/kis-transactions`, {
        params: {
          from_date: toYYYYMMDD(new Date(kisFromDate)),
          to_date: toYYYYMMDD(new Date(kisToDate)),
        },
      });
      return data;
    },
    enabled: showKisHistory,
  });

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

  const editHoldingMutation = useMutation({
    mutationFn: ({ holdingId, quantity, avg_price }: { holdingId: number; quantity: number; avg_price: number }) =>
      api.patch<Holding>(`/portfolios/holdings/${holdingId}`, { quantity, avg_price }).then((r) => r.data),
    onSuccess: (data) => {
      queryClient.setQueryData<Holding[]>(holdingsKey(portfolioId), (prev) =>
        prev ? prev.map((h) => (h.id === data.id ? data : h)) : []
      );
      setEditId(null);
    },
    onError: () => {
      toast.error("보유종목 수정에 실패했습니다. 잠시 후 다시 시도해주세요.");
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

  const addTxnMutation = useMutation({
    mutationFn: () =>
      api.post(`/portfolios/${portfolioId}/transactions`, {
        ticker: txnForm.ticker,
        type: txnForm.type,
        quantity: Number(txnForm.quantity),
        price: Number(txnForm.price),
        ...(txnForm.traded_at ? { traded_at: new Date(txnForm.traded_at).toISOString() } : {}),
      }),
    onSuccess: () => {
      setTxnForm({ ticker: "", type: "BUY", quantity: "", price: "", traded_at: "" });
      setShowTxnForm(false);
      void queryClient.invalidateQueries({ queryKey: transactionsKey(portfolioId) });
    },
    onError: () => {
      toast.error("거래내역 추가에 실패했습니다. 입력 내용을 확인해주세요.");
    },
  });

  const deleteTxnMutation = useMutation({
    mutationFn: (txnId: number) => api.delete(`/portfolios/transactions/${txnId}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: transactionsKey(portfolioId) });
      setDeleteTxnId(null);
    },
    onError: () => {
      toast.error("거래내역 삭제에 실패했습니다. 잠시 후 다시 시도해주세요.");
    },
  });

  const updateMemoMutation = useMutation({
    mutationFn: ({ txnId, memo }: { txnId: number; memo: string | null }) =>
      api.patch<TxnRow>(`/portfolios/${portfolioId}/transactions/${txnId}`, { memo }).then((r) => r.data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: transactionsKey(portfolioId) });
    },
    onError: () => {
      toast.error("메모 저장에 실패했습니다. 잠시 후 다시 시도해주세요.");
    },
    onSettled: () => {
      setEditMemoId(null);
    },
  });

  const updateTargetMutation = useMutation({
    mutationFn: (target_value: number | null) =>
      api.patch(`/portfolios/${portfolioId}`, { target_value }).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portfolio", portfolioId] });
      setEditingTarget(false);
    },
    onError: () => {
      toast.error("목표 금액 설정에 실패했습니다. 잠시 후 다시 시도해주세요.");
    },
  });

  const handleTargetSave = () => {
    const raw = targetInputValue.trim().replace(/,/g, "");
    if (raw === "") {
      updateTargetMutation.mutate(null);
    } else {
      const parsed = parseInt(raw, 10);
      if (!isNaN(parsed) && parsed >= 0) {
        updateTargetMutation.mutate(parsed);
      }
    }
  };

  const handleTxnSubmit = () => {
    if (!txnForm.ticker || !txnForm.quantity || !txnForm.price) return;
    if (Number(txnForm.quantity) <= 0 || Number(txnForm.price) <= 0) return;
    addTxnMutation.mutate();
  };

  const handleStockSelect = (ticker: string, name: string) => {
    if (isKisConnected) {
      // KIS 연결 시: OrderDialog로 실시간 주문
      setOrderTicker(ticker);
      setOrderName(name);
      setOrderCurrentPrice(undefined);
      setOrderDialogOpen(true);
    } else {
      // KIS 미연결 시: 수동 종목 추가 폼
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

  const handleEditSave = (holdingId: number) => {
    editHoldingMutation.mutate({
      holdingId,
      quantity: Number(editForm.quantity),
      avg_price: Number(editForm.avg_price),
    });
  };

  const downloadCsv = async (path: string, filename: string) => {
    if (isExporting) return;
    setIsExporting(true);
    try {
      const response = await api.get<string>(path, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([response.data], { type: "text/csv" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("파일 내보내기에 실패했습니다");
    } finally {
      setIsExporting(false);
    }
  };

  const downloadXlsx = async () => {
    if (isExporting) return;
    setIsExporting(true);
    try {
      const response = await api.get<Blob>(`/portfolios/${portfolioId}/export/xlsx`, {
        responseType: "blob",
      });
      const mimeType =
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
      const today = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      const url = URL.createObjectURL(new Blob([response.data], { type: mimeType }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `portfolio_${portfolioId}_${today}.xlsx`;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("엑셀 내보내기에 실패했습니다");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">보유 종목</h1>
        <div className="flex gap-2 flex-wrap justify-end">
          {isKisConnected && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowPendingOrders((v) => !v)}
              className="gap-2"
            >
              미체결 주문
              {pendingOrders.length > 0 && (
                <span className="ml-1 rounded-full bg-red-500 px-1.5 text-[10px] text-white">
                  {pendingOrders.length}
                </span>
              )}
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => downloadCsv(`/portfolios/${portfolioId}/export/csv`, `holdings_portfolio_${portfolioId}.csv`)}
            disabled={isExporting}
            className="gap-2"
          >
            {isExporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            보유 종목 CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => downloadCsv(`/portfolios/${portfolioId}/transactions/export/csv`, `transactions_portfolio_${portfolioId}.csv`)}
            disabled={isExporting}
            className="gap-2"
          >
            {isExporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            거래 내역 CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={downloadXlsx}
            disabled={isExporting}
            className="gap-2"
          >
            {isExporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            Excel
          </Button>
          <Button onClick={() => setSearchOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            {isKisConnected ? "신규 매수" : "종목 추가"}
          </Button>
        </div>
      </div>

      {/* KIS 연결 포트폴리오: 예수금 요약 */}
      {isKisConnected && (cashBalance || cashBalanceError) && (
        <div className="space-y-1.5">
          {cashBalanceError && (
            <div className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
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
              <div className="text-xs text-amber-600">
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
                <TrendingUp className="h-3.5 w-3.5 text-red-500" />
              ) : (
                <TrendingDown className="h-3.5 w-3.5 text-blue-500" />
              )}
              평가손익
            </div>
            <div className={`font-semibold text-sm ${Number(cashBalance.total_profit_loss) >= 0 ? "text-red-600" : "text-blue-600"}`}>
              {Number(cashBalance.total_profit_loss) >= 0 ? "+" : ""}{formatKRW(cashBalance.total_profit_loss)}
            </div>
            <div className={`text-xs ${Number(cashBalance.profit_loss_rate) >= 0 ? "text-red-500" : "text-blue-500"}`}>
              {Number(cashBalance.profit_loss_rate) >= 0 ? "+" : ""}{Number(cashBalance.profit_loss_rate).toFixed(2)}%
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

      {/* 목표 금액 달성률 위젯 */}
      {(() => {
        const totalCurrentKrw = holdings.reduce(
          (sum, h) => sum + Number(h.market_value_krw ?? 0),
          0
        );
        const targetValue = portfolioInfo?.target_value ?? null;
        if (!targetValue && !editingTarget) {
          return (
            <button
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => { setTargetInputValue(""); setEditingTarget(true); }}
            >
              <Target className="h-3.5 w-3.5" />
              목표 금액 설정
            </button>
          );
        }
        const progress = targetValue && targetValue > 0
          ? Math.min((totalCurrentKrw / targetValue) * 100, 100)
          : 0;
        const isAchieved = targetValue != null && totalCurrentKrw >= targetValue;
        return (
          <div className="rounded-lg border p-4 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Target className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">목표 달성률</span>
                {isAchieved && (
                  <span className="text-xs bg-green-100 text-green-700 rounded-full px-2 py-0.5 dark:bg-green-900/30 dark:text-green-400">
                    달성!
                  </span>
                )}
              </div>
              {editingTarget ? (
                <div className="flex items-center gap-1">
                  <input
                    type="text"
                    className="h-7 w-36 rounded border px-2 text-xs tabular-nums"
                    placeholder="목표 금액 (원)"
                    value={targetInputValue}
                    onChange={(e) => setTargetInputValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleTargetSave();
                      if (e.key === "Escape") setEditingTarget(false);
                    }}
                    autoFocus
                  />
                  <button
                    onClick={handleTargetSave}
                    disabled={updateTargetMutation.isPending}
                    className="p-1 text-green-600 hover:text-green-700"
                  >
                    <Check className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => setEditingTarget(false)}
                    className="p-1 text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => {
                    setTargetInputValue(targetValue ? String(targetValue) : "");
                    setEditingTarget(true);
                  }}
                  className="p-1 text-muted-foreground hover:text-foreground"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
            {targetValue != null && (
              <>
                <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${progress}%`,
                      background: isAchieved ? "var(--color-green-500, #22c55e)" : "var(--accent-indigo, #6366F1)",
                    }}
                  />
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span className="tabular-nums">{formatKRW(totalCurrentKrw)}</span>
                  <span className="tabular-nums font-medium" style={{ color: isAchieved ? "#22c55e" : undefined }}>
                    {progress.toFixed(1)}% / {formatKRW(targetValue)}
                  </span>
                </div>
              </>
            )}
          </div>
        );
      })()}

      {/* 미체결 주문 패널 */}
      {isKisConnected && showPendingOrders && (
        <div className="rounded-lg border p-4">
          <PendingOrdersPanel portfolioId={portfolioId} />
        </div>
      )}

      <HoldingsSection
        holdings={holdings}
        isLoading={isLoading}
        isError={isError}
        error={error instanceof Error ? error : null}
        onRetry={() => refetch()}
        isKisConnected={isKisConnected}
        isSyncing={isSyncing}
        onKisSync={handleKisSync}
        onSearchOpen={() => setSearchOpen(true)}
        addForm={addForm}
        addFormErrors={addFormErrors}
        addHoldingPending={addHoldingMutation.isPending}
        onSetAddForm={setAddForm}
        onSetAddFormErrors={setAddFormErrors}
        onHandleAdd={() => handleAdd({ preventDefault: () => {} } as React.FormEvent)}
        editId={editId}
        editForm={editForm}
        editHoldingPending={editHoldingMutation.isPending}
        onSetEditId={setEditId}
        onSetEditForm={setEditForm}
        onEditSave={handleEditSave}
        deleteConfirmId={deleteConfirmId}
        deleteHoldingPending={deleteHoldingMutation.isPending}
        onSetDeleteConfirmId={setDeleteConfirmId}
        onDeleteHolding={(id) => deleteHoldingMutation.mutate(id)}
        onOpenOrder={(ticker, name, currentPrice, tab, exchangeCode, existingHolding) => {
          setOrderTicker(ticker);
          setOrderName(name);
          setOrderCurrentPrice(currentPrice);
          setOrderInitialTab(tab);
          setOrderExchangeCode(exchangeCode);
          setOrderExistingHolding(existingHolding);
          setOrderDialogOpen(true);
        }}
      />


      <TransactionSection
        transactions={transactions}
        holdings={holdings}
        hasMorTxns={hasMorTxns ?? false}
        isFetchingMoreTxns={isFetchingMoreTxns}
        onFetchMoreTxns={() => void fetchMoreTxns()}
        showTxnForm={showTxnForm}
        txnForm={txnForm}
        addTxnPending={addTxnMutation.isPending}
        onSetShowTxnForm={setShowTxnForm}
        onSetTxnForm={setTxnForm}
        onTxnSubmit={handleTxnSubmit}
        editMemoId={editMemoId}
        editMemoValue={editMemoValue}
        onSetEditMemoId={setEditMemoId}
        onSetEditMemoValue={setEditMemoValue}
        onUpdateMemo={(txnId, memo) => updateMemoMutation.mutate({ txnId, memo })}
        deleteTxnId={deleteTxnId}
        deleteTxnPending={deleteTxnMutation.isPending}
        onSetDeleteTxnId={setDeleteTxnId}
        onDeleteTxn={(id) => deleteTxnMutation.mutate(id)}
        isKisConnected={isKisConnected}
        kisTransactions={kisTransactions}
        kisLoading={kisLoading}
        kisFromDate={kisFromDate}
        kisToDate={kisToDate}
        showKisHistory={showKisHistory}
        onSetKisFromDate={setKisFromDate}
        onSetKisToDate={setKisToDate}
        onSetShowKisHistory={setShowKisHistory}
        onKisRefetch={() => void kisRefetch()}
        hasOverseas={holdings.some((h) => h.currency === "USD")}
      />
      <StockSearchDialog
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelect={handleStockSelect}
      />

      {/* KIS 주문 다이얼로그 — key로 ticker+tab 변경 시 강제 리마운트 */}
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
    </div>
  );
}
