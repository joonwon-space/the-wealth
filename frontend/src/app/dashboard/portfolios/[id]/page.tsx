"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Plus, Search, Trash2, PackageOpen, Download, History, TrendingUp, TrendingDown, Wallet, Target, Pencil, Check, X, RefreshCw } from "lucide-react";
import { useQuery, useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatKRW, formatNumber, formatPrice } from "@/lib/format";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { StockSearchDialog } from "@/components/StockSearchDialog";
import { PnLBadge } from "@/components/PnLBadge";
import { TransactionChart } from "@/components/DynamicCharts";
import { PageError } from "@/components/PageError";
import { TableSkeleton } from "@/components/TableSkeleton";
import { OrderDialog, ExistingHolding } from "@/components/OrderDialog";
import { PendingOrdersPanel } from "@/components/PendingOrdersPanel";
import { useCashBalance, usePendingOrders } from "@/hooks/useOrders";
import { toast } from "sonner";

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

function formatUSD(value: string | number | null | undefined): string {
  if (value == null) return "—";
  const num = Number(value);
  if (isNaN(num)) return "—";
  return `$${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function PortfolioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const portfolioId = Number(id);
  const queryClient = useQueryClient();

  const [searchOpen, setSearchOpen] = useState(false);
  const [addForm, setAddForm] = useState<AddForm | null>(null);
  const [orderDialogOpen, setOrderDialogOpen] = useState(false);
  const [orderTicker, setOrderTicker] = useState("");
  const [orderName, setOrderName] = useState("");
  const [orderCurrentPrice, setOrderCurrentPrice] = useState<number | undefined>();
  const [orderInitialTab, setOrderInitialTab] = useState<"BUY" | "SELL">("BUY");
  const [orderExchangeCode, setOrderExchangeCode] = useState<string | undefined>();
  const [orderExistingHolding, setOrderExistingHolding] = useState<ExistingHolding | undefined>();
  const [showPendingOrders, setShowPendingOrders] = useState(false);
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
  const { data: cashBalance } = useCashBalance(isKisConnected ? portfolioId : 0);
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
  });

  const deleteHoldingMutation = useMutation({
    mutationFn: (holdingId: number) => api.delete(`/portfolios/holdings/${holdingId}`),
    onSuccess: (_, holdingId) => {
      queryClient.setQueryData<Holding[]>(holdingsKey(portfolioId), (prev) =>
        prev ? prev.filter((h) => h.id !== holdingId) : []
      );
      setDeleteConfirmId(null);
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
  });

  const deleteTxnMutation = useMutation({
    mutationFn: (txnId: number) => api.delete(`/portfolios/transactions/${txnId}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: transactionsKey(portfolioId) });
      setDeleteTxnId(null);
    },
  });

  const updateMemoMutation = useMutation({
    mutationFn: ({ txnId, memo }: { txnId: number; memo: string | null }) =>
      api.patch<TxnRow>(`/portfolios/${portfolioId}/transactions/${txnId}`, { memo }).then((r) => r.data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: transactionsKey(portfolioId) });
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
    const response = await api.get<string>(path, { responseType: "blob" });
    const url = URL.createObjectURL(new Blob([response.data], { type: "text/csv" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
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
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            보유 종목 CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => downloadCsv(`/portfolios/${portfolioId}/transactions/export/csv`, `transactions_portfolio_${portfolioId}.csv`)}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            거래 내역 CSV
          </Button>
          <Button onClick={() => setSearchOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            {isKisConnected ? "신규 매수" : "종목 추가"}
          </Button>
        </div>
      </div>

      {/* KIS 연결 포트폴리오: 예수금 요약 */}
      {isKisConnected && cashBalance && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-lg border p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              <Wallet className="h-3.5 w-3.5" />
              예수금
            </div>
            <div className="font-semibold text-sm">{formatKRW(cashBalance.total_cash)}</div>
            <div className="text-xs text-muted-foreground">사용가능: {formatKRW(cashBalance.available_cash)}</div>
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
              <Button onClick={handleKisSync} disabled={isSyncing} className="mt-4 gap-2">
                <RefreshCw className={`h-4 w-4 ${isSyncing ? "animate-spin" : ""}`} />
                {isSyncing ? "동기화 중..." : "지금 동기화"}
              </Button>
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
        <div className="overflow-x-auto rounded-xl border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                {["종목", "수량", "평균단가", "현재가", "손익 (KRW)", "평가금액 (KRW)", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...holdings]
                .sort((a, b) => Number(b.market_value_krw ?? 0) - Number(a.market_value_krw ?? 0))
                .map((h) => {
                const isUSD = h.currency === "USD";
                return (
                  <tr key={h.id} className="border-t hover:bg-muted/20">
                    {editId === h.id ? (
                      <>
                        <td className="px-4 py-2">
                          <div className="font-medium">{h.name}</div>
                          <div className="text-xs text-muted-foreground">{h.ticker}</div>
                        </td>
                        <td className="px-4 py-2">
                          <Input
                            type="number"
                            value={editForm.quantity}
                            onChange={(e) => setEditForm((f) => ({ ...f, quantity: e.target.value }))}
                            className="w-24 h-8"
                          />
                        </td>
                        <td className="px-4 py-2">
                          <Input
                            type="number"
                            value={editForm.avg_price}
                            onChange={(e) => setEditForm((f) => ({ ...f, avg_price: e.target.value }))}
                            className="w-28 h-8"
                          />
                        </td>
                        <td className="px-4 py-2">
                          <div className="flex gap-2">
                            <Button size="sm" onClick={() => handleEditSave(h.id)} disabled={editHoldingMutation.isPending}>저장</Button>
                            <Button size="sm" variant="outline" onClick={() => setEditId(null)}>취소</Button>
                          </div>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-4 py-3">
                          <div className="font-medium">{h.name}</div>
                          <div className="text-xs text-muted-foreground">
                            {h.ticker}
                            {isUSD && <span className="ml-1 rounded bg-blue-100 px-1 text-blue-700 dark:bg-blue-900 dark:text-blue-300">USD</span>}
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
                                  {Number(h.pnl_rate) >= 0 ? "+" : ""}{Number(h.pnl_rate).toFixed(2)}%
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
                                  onClick={() => {
                                    setOrderTicker(h.ticker);
                                    setOrderName(h.name);
                                    setOrderCurrentPrice(h.current_price ? Number(h.current_price) : undefined);
                                    setOrderInitialTab("BUY");
                                    setOrderExchangeCode(h.currency === "USD" ? (h.ticker.includes(".") ? h.ticker.split(".")[1] : "NASD") : undefined);
                                    setOrderExistingHolding({ quantity: h.quantity, avg_price: h.avg_price, pnl_amount: h.pnl_amount, pnl_rate: h.pnl_rate });
                                    setOrderDialogOpen(true);
                                  }}
                                  className="rounded border px-2 py-0.5 text-xs font-medium text-red-600 border-red-200 hover:bg-red-50"
                                >
                                  매수
                                </button>
                                <button
                                  onClick={() => {
                                    setOrderTicker(h.ticker);
                                    setOrderName(h.name);
                                    setOrderCurrentPrice(h.current_price ? Number(h.current_price) : undefined);
                                    setOrderInitialTab("SELL");
                                    setOrderExchangeCode(h.currency === "USD" ? (h.ticker.includes(".") ? h.ticker.split(".")[1] : "NASD") : undefined);
                                    setOrderExistingHolding({ quantity: h.quantity, avg_price: h.avg_price, pnl_amount: h.pnl_amount, pnl_rate: h.pnl_rate });
                                    setOrderDialogOpen(true);
                                  }}
                                  className="rounded border px-2 py-0.5 text-xs font-medium text-blue-600 border-blue-200 hover:bg-blue-50"
                                >
                                  매도
                                </button>
                              </>
                            )}
                            <button
                              onClick={() => { setEditId(h.id); setEditForm({ quantity: h.quantity, avg_price: h.avg_price }); }}
                              className="rounded border px-3 py-1 text-xs hover:bg-muted"
                            >
                              수정
                            </button>
                            <button
                              onClick={() => setDeleteConfirmId(h.id)}
                              className="rounded border px-3 py-1 text-xs text-destructive hover:bg-destructive/10"
                            >
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </div>
                        </td>
                      </>
                    )}
                  </tr>
                );
              })}

              {/* 종목 추가 폼 행 */}
              {addForm && (
                <tr className="border-t bg-muted/10">
                  <td className="px-4 py-2">
                    <div className="font-medium">{addForm.name}</div>
                    <div className="text-xs text-muted-foreground">{addForm.ticker}</div>
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      placeholder="수량"
                      value={addForm.quantity}
                      onChange={(e) => setAddForm((f) => f ? { ...f, quantity: e.target.value } : f)}
                      className="w-24 h-8"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      placeholder="평균단가"
                      value={addForm.avg_price}
                      onChange={(e) => setAddForm((f) => f ? { ...f, avg_price: e.target.value } : f)}
                      className="w-28 h-8"
                    />
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
                      <Button size="sm" variant="outline" onClick={() => setAddForm(null)}>취소</Button>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* 삭제 확인 모달 */}
      {deleteConfirmId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-xs rounded-xl border bg-background p-6 shadow-lg text-center space-y-4">
            <p className="font-semibold">종목을 삭제하시겠습니까?</p>
            <p className="text-sm text-muted-foreground">이 작업은 되돌릴 수 없습니다.</p>
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => setDeleteConfirmId(null)}>취소</Button>
              <Button
                variant="destructive"
                className="flex-1"
                disabled={deleteHoldingMutation.isPending}
                onClick={() => deleteHoldingMutation.mutate(deleteConfirmId)}
              >
                삭제
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 거래 삭제 확인 */}
      {deleteTxnId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-xs rounded-xl border bg-background p-6 shadow-lg text-center space-y-4">
            <p className="font-semibold">거래를 삭제하시겠습니까?</p>
            <p className="text-sm text-muted-foreground">이 작업은 되돌릴 수 없습니다.</p>
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => setDeleteTxnId(null)}>취소</Button>
              <Button
                variant="destructive"
                className="flex-1"
                disabled={deleteTxnMutation.isPending}
                onClick={() => deleteTxnMutation.mutate(deleteTxnId)}
              >
                삭제
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 수동 거래 이력 (DB) */}
      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">거래 이력</h2>
          <Button size="sm" variant="outline" onClick={() => setShowTxnForm(!showTxnForm)}>
            {showTxnForm ? "취소" : "거래 추가"}
          </Button>
        </div>

        {showTxnForm && (
          <div className="grid grid-cols-2 gap-2 rounded-lg border p-3 sm:flex sm:flex-wrap sm:items-end">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">유형</label>
              <select
                value={txnForm.type}
                onChange={(e) => setTxnForm((f) => ({ ...f, type: e.target.value as "BUY" | "SELL" }))}
                className="h-8 w-full rounded border bg-background px-2 text-sm sm:w-auto"
              >
                <option value="BUY">매수</option>
                <option value="SELL">매도</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">종목코드</label>
              <Input value={txnForm.ticker} onChange={(e) => setTxnForm((f) => ({ ...f, ticker: e.target.value }))} placeholder="005930" className="h-8 w-full sm:w-24" />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">수량</label>
              <Input type="number" value={txnForm.quantity} onChange={(e) => setTxnForm((f) => ({ ...f, quantity: e.target.value }))} placeholder="10" className="h-8 w-full sm:w-20" />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">단가</label>
              <Input type="number" value={txnForm.price} onChange={(e) => setTxnForm((f) => ({ ...f, price: e.target.value }))} placeholder="70000" className="h-8 w-full sm:w-28" />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">날짜</label>
              <Input type="date" value={txnForm.traded_at} onChange={(e) => setTxnForm((f) => ({ ...f, traded_at: e.target.value }))} className="h-8 w-full sm:w-36" />
            </div>
            <Button size="sm" className="col-span-2 sm:col-span-1" onClick={handleTxnSubmit} disabled={addTxnMutation.isPending}>
              {addTxnMutation.isPending ? "저장 중..." : "저장"}
            </Button>
          </div>
        )}

        {transactions.length > 0 && (
          <>
            <TransactionChart transactions={transactions} />
            <div className="overflow-x-auto rounded-xl border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    {["일시", "유형", "종목", "수량", "단가", "메모", ""].map((h) => (
                      <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((t) => (
                    <tr key={t.id} className="border-t">
                      <td className="px-4 py-2 text-xs text-muted-foreground">{new Date(t.traded_at).toLocaleString("ko-KR")}</td>
                      <td className="px-4 py-2">
                        <span className={`text-xs font-semibold ${t.type === "BUY" ? "text-[#e31f26]" : "text-[#1a56db]"}`}>
                          {t.type === "BUY" ? "매수" : "매도"}
                        </span>
                      </td>
                      <td className="px-4 py-2 font-mono text-xs">{t.ticker}</td>
                      <td className="px-4 py-2 tabular-nums">{formatNumber(t.quantity)}</td>
                      <td className="px-4 py-2 tabular-nums">{formatKRW(t.price)}</td>
                      <td className="px-4 py-2 min-w-[140px]">
                        {editMemoId === t.id ? (
                          <input
                            type="text"
                            autoFocus
                            value={editMemoValue}
                            maxLength={500}
                            onChange={(e) => setEditMemoValue(e.target.value)}
                            onBlur={() => {
                              const trimmed = editMemoValue.trim() || null;
                              updateMemoMutation.mutate({ txnId: t.id, memo: trimmed });
                            }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                const trimmed = editMemoValue.trim() || null;
                                updateMemoMutation.mutate({ txnId: t.id, memo: trimmed });
                              }
                              if (e.key === "Escape") {
                                setEditMemoId(null);
                              }
                            }}
                            className="w-full rounded border bg-background px-2 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                            aria-label="메모 편집"
                          />
                        ) : (
                          <button
                            type="button"
                            className="w-full text-left text-xs text-muted-foreground hover:text-foreground hover:underline"
                            onClick={() => {
                              setEditMemoId(t.id);
                              setEditMemoValue(t.memo ?? "");
                            }}
                            aria-label={t.memo ? `메모: ${t.memo}. 클릭하여 편집` : "메모 추가 (클릭하여 편집)"}
                          >
                            {t.memo ?? <span className="opacity-40">메모 추가...</span>}
                          </button>
                        )}
                      </td>
                      <td className="px-4 py-2">
                        <button
                          onClick={() => setDeleteTxnId(t.id)}
                          className="rounded border px-2 py-0.5 text-xs text-destructive hover:bg-destructive/10"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {hasMorTxns && (
              <div className="flex justify-center pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void fetchMoreTxns()}
                  disabled={isFetchingMoreTxns}
                >
                  {isFetchingMoreTxns ? "불러오는 중..." : "더 보기"}
                </Button>
              </div>
            )}
          </>
        )}
      </section>

      {/* KIS API 체결 내역 */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-base font-semibold">KIS 체결 내역</h2>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowKisHistory((v) => !v)}
          >
            {showKisHistory ? "접기" : "불러오기"}
          </Button>
        </div>

        {showKisHistory && (
          <>
            {holdings.some((h) => h.currency === "USD") && (
              <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
                <span className="mt-0.5 shrink-0">⚠️</span>
                <span>
                  <strong>해외주식 체결 내역은 KIS OpenAPI로 주문한 건만 조회됩니다.</strong>
                  {" "}한투 앱/HTS로 거래한 내역은 표시되지 않습니다. 아래 &quot;거래 이력&quot; 섹션에서 직접 입력해주세요.
                </span>
              </div>
            )}
            <div className="flex flex-wrap items-end gap-2 rounded-lg border p-3">
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">시작일</label>
                <Input
                  type="date"
                  value={kisFromDate}
                  onChange={(e) => setKisFromDate(e.target.value)}
                  className="h-8 w-36"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">종료일</label>
                <Input
                  type="date"
                  value={kisToDate}
                  onChange={(e) => setKisToDate(e.target.value)}
                  className="h-8 w-36"
                />
              </div>
              <Button size="sm" onClick={() => kisRefetch()} disabled={kisLoading}>
                {kisLoading ? "조회 중..." : "조회"}
              </Button>
            </div>

            {kisLoading ? (
              <TableSkeleton rows={3} columns={6} />
            ) : !kisTransactions || kisTransactions.length === 0 ? (
              <div className="rounded-lg border border-dashed py-8 text-center text-sm text-muted-foreground">
                해당 기간에 체결 내역이 없습니다.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50">
                    <tr>
                      {["일시", "유형", "종목", "수량", "단가", "거래금액"].map((h) => (
                        <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {kisTransactions.map((t, i) => {
                      const isOverseas = !["domestic"].includes(t.market) && t.market !== "";
                      return (
                        <tr key={i} className="border-t hover:bg-muted/20">
                          <td className="px-4 py-2 text-xs text-muted-foreground">
                            {new Date(t.traded_at).toLocaleString("ko-KR")}
                          </td>
                          <td className="px-4 py-2">
                            <span className={`text-xs font-semibold ${t.type === "BUY" ? "text-[#e31f26]" : "text-[#1a56db]"}`}>
                              {t.type === "BUY" ? "매수" : "매도"}
                            </span>
                          </td>
                          <td className="px-4 py-2">
                            <div className="font-mono text-xs">{t.ticker}</div>
                            {t.name && <div className="text-xs text-muted-foreground">{t.name}</div>}
                          </td>
                          <td className="px-4 py-2 tabular-nums">{formatNumber(t.quantity)}</td>
                          <td className="px-4 py-2 tabular-nums">
                            {isOverseas ? formatUSD(t.price) : formatKRW(t.price)}
                          </td>
                          <td className="px-4 py-2 tabular-nums">
                            {isOverseas ? formatUSD(t.total_amount) : formatKRW(t.total_amount)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>

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
