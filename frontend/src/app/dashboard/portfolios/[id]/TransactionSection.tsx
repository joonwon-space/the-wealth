"use client";

import { useState } from "react";
import { History, Trash2 } from "lucide-react";
import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatKRW, formatNumber } from "@/lib/format";
import { Input } from "@/components/ui/input";
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
import { TransactionChart } from "@/components/DynamicCharts";
import { TableSkeleton } from "@/components/TableSkeleton";
import { toast } from "sonner";
import type { Holding } from "./HoldingsSection";

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

function formatUSD(value: string | number | null | undefined): string {
  if (value == null) return "—";
  const num = Number(value);
  if (isNaN(num)) return "—";
  return `$${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function toYYYYMMDD(date: Date): string {
  return date.toISOString().slice(0, 10).replace(/-/g, "");
}

function transactionsKey(portfolioId: number) {
  return ["portfolios", portfolioId, "transactions"] as const;
}

function kisTransactionsKey(portfolioId: number, fromDate: string, toDate: string) {
  return ["portfolios", portfolioId, "kis-transactions", fromDate, toDate] as const;
}

interface TransactionSectionProps {
  portfolioId: number;
  holdings: Holding[];
  isKisConnected: boolean;
}

export function TransactionSection({ portfolioId, holdings, isKisConnected }: TransactionSectionProps) {
  const queryClient = useQueryClient();
  const [showTxnForm, setShowTxnForm] = useState(false);
  const [txnForm, setTxnForm] = useState({ ticker: "", type: "BUY" as "BUY" | "SELL", quantity: "", price: "", traded_at: "" });
  const [deleteTxnId, setDeleteTxnId] = useState<number | null>(null);
  const [editMemoId, setEditMemoId] = useState<number | null>(null);
  const [editMemoValue, setEditMemoValue] = useState<string>("");

  const today = new Date();
  const oneMonthAgo = new Date(today);
  oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);
  const [kisFromDate, setKisFromDate] = useState(oneMonthAgo.toISOString().slice(0, 10));
  const [kisToDate, setKisToDate] = useState(today.toISOString().slice(0, 10));
  const [showKisHistory, setShowKisHistory] = useState(false);

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

  const { data: kisTransactions, isLoading: kisLoading, refetch: kisRefetch } = useInfiniteQuery<KisTxnRow[]>({
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
    initialPageParam: 0,
    getNextPageParam: () => undefined,
  });

  const kisTxnList = kisTransactions?.pages.flatMap((p) => p) ?? [];

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

  const handleTxnSubmit = () => {
    if (!txnForm.ticker || !txnForm.quantity || !txnForm.price) return;
    if (Number(txnForm.quantity) <= 0 || Number(txnForm.price) <= 0) return;
    addTxnMutation.mutate();
  };

  return (
    <>
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
                    {["일시", "유형", "종목", "수량", "단가", "거래금액", "메모", ""].map((h) => (
                      <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((t) => {
                    const holdingMatch = holdings.find((h) => h.ticker === t.ticker);
                    const totalAmount = Number(t.quantity) * Number(t.price);
                    return (
                      <tr key={t.id} className="border-t">
                        <td className="px-4 py-2 text-xs text-muted-foreground">{new Date(t.traded_at).toLocaleString("ko-KR")}</td>
                        <td className="px-4 py-2">
                          <span className={`text-xs font-semibold ${t.type === "BUY" ? "text-[#e31f26]" : "text-[#1a56db]"}`}>
                            {t.type === "BUY" ? "매수" : "매도"}
                          </span>
                        </td>
                        <td className="px-4 py-2">
                          <div className="font-mono text-xs">{t.ticker}</div>
                          {holdingMatch && <div className="text-xs text-muted-foreground">{holdingMatch.name}</div>}
                        </td>
                        <td className="px-4 py-2 tabular-nums">{formatNumber(t.quantity)}</td>
                        <td className="px-4 py-2 tabular-nums">{formatKRW(t.price)}</td>
                        <td className="px-4 py-2 tabular-nums">{formatKRW(totalAmount)}</td>
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
                            aria-label="거래내역 삭제"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
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

      {/* 거래내역 삭제 확인 */}
      <AlertDialog
        open={deleteTxnId !== null}
        onOpenChange={(open) => { if (!open) setDeleteTxnId(null); }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>거래를 삭제하시겠습니까?</AlertDialogTitle>
            <AlertDialogDescription>
              이 작업은 되돌릴 수 없습니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                if (deleteTxnId !== null) {
                  deleteTxnMutation.mutate(deleteTxnId);
                }
              }}
            >
              {deleteTxnMutation.isPending ? "삭제 중..." : "삭제"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

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
            ) : !kisTxnList || kisTxnList.length === 0 ? (
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
                    {kisTxnList.map((t, i) => {
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
    </>
  );
}
