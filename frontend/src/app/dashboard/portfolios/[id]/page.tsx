"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Plus, Search, Trash2, PackageOpen, Download } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatKRW, formatNumber, formatPrice } from "@/lib/format";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { StockSearchDialog } from "@/components/StockSearchDialog";
import { PnLBadge } from "@/components/PnLBadge";
import { TransactionChart } from "@/components/DynamicCharts";
import { PageError } from "@/components/PageError";
import { TableSkeleton } from "@/components/TableSkeleton";

interface TxnRow {
  id: number;
  ticker: string;
  type: string;
  quantity: string;
  price: string;
  traded_at: string;
}

interface Holding {
  id: number;
  ticker: string;
  name: string;
  quantity: string;
  avg_price: string;
  current_price: string | null;
  market_value: string | null;
  pnl_amount: string | null;
  pnl_rate: string | null;
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

export default function PortfolioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const portfolioId = Number(id);
  const queryClient = useQueryClient();

  const [searchOpen, setSearchOpen] = useState(false);
  const [addForm, setAddForm] = useState<AddForm | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<{ quantity: string; avg_price: string }>({ quantity: "", avg_price: "" });
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [showTxnForm, setShowTxnForm] = useState(false);
  const [txnForm, setTxnForm] = useState({ ticker: "", type: "BUY" as "BUY" | "SELL", quantity: "", price: "", traded_at: "" });
  const [deleteTxnId, setDeleteTxnId] = useState<number | null>(null);

  const { data: holdings = [], isLoading, isError, error, refetch } = useQuery<Holding[]>({
    queryKey: holdingsKey(portfolioId),
    queryFn: async () => {
      const { data } = await api.get<Holding[]>(`/portfolios/${portfolioId}/holdings/with-prices`);
      return data;
    },
  });

  const { data: transactions = [] } = useQuery<TxnRow[]>({
    queryKey: transactionsKey(portfolioId),
    queryFn: async () => {
      try {
        const { data } = await api.get<TxnRow[]>(`/portfolios/${portfolioId}/transactions`);
        return data;
      } catch {
        return [];
      }
    },
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
      queryClient.invalidateQueries({ queryKey: transactionsKey(portfolioId) });
    },
  });

  const deleteTxnMutation = useMutation({
    mutationFn: (txnId: number) => api.delete(`/portfolios/transactions/${txnId}`),
    onSuccess: (_, txnId) => {
      queryClient.setQueryData<TxnRow[]>(transactionsKey(portfolioId), (prev) =>
        prev ? prev.filter((t) => t.id !== txnId) : []
      );
      setDeleteTxnId(null);
    },
  });

  const handleTxnSubmit = () => {
    if (!txnForm.ticker || !txnForm.quantity || !txnForm.price) return;
    if (Number(txnForm.quantity) <= 0 || Number(txnForm.price) <= 0) return;
    addTxnMutation.mutate();
  };

  const handleStockSelect = (ticker: string, name: string) => {
    setAddForm({ ...EMPTY_FORM, ticker, name });
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
        <div className="flex gap-2">
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
            종목 추가
          </Button>
        </div>
      </div>

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
          <p className="font-medium">보유 종목이 없습니다</p>
          <p className="mt-1 text-sm text-muted-foreground">종목을 검색해서 추가해보세요.</p>
          <Button onClick={() => setSearchOpen(true)} className="mt-4 gap-2">
            <Search className="h-4 w-4" />
            종목 검색
          </Button>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                {["종목", "수량", "평균단가", "현재가", "손익", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {holdings.map((h) => (
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
                        <div className="text-xs text-muted-foreground">{h.ticker}</div>
                      </td>
                      <td className="px-4 py-3 tabular-nums">{formatNumber(h.quantity)}</td>
                      <td className="px-4 py-3 tabular-nums">{formatPrice(h.avg_price, h.currency ?? "KRW")}</td>
                      <td className="px-4 py-3 tabular-nums">{h.current_price ? formatPrice(h.current_price, h.currency ?? "KRW") : <span className="text-muted-foreground">—</span>}</td>
                      <td className="px-4 py-3">{h.pnl_amount != null ? <PnLBadge value={h.pnl_amount} /> : <span className="text-muted-foreground">—</span>}</td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
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
              ))}

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

      {/* Transaction History */}
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
                  {["일시", "유형", "종목", "수량", "단가", ""].map((h) => (
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
        </>
      )}
      </section>

      <StockSearchDialog
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelect={handleStockSelect}
      />
    </div>
  );
}
