"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Plus, Search, Trash2, PackageOpen } from "lucide-react";
import { api } from "@/lib/api";
import { formatKRW, formatNumber } from "@/lib/format";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { StockSearchDialog } from "@/components/StockSearchDialog";
import { PnLBadge } from "@/components/PnLBadge";

interface Holding {
  id: number;
  ticker: string;
  name: string;
  quantity: string;
  avg_price: string;
}

interface AddForm {
  ticker: string;
  name: string;
  quantity: string;
  avg_price: string;
}

const EMPTY_FORM: AddForm = { ticker: "", name: "", quantity: "", avg_price: "" };

export default function PortfolioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const portfolioId = Number(id);

  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchOpen, setSearchOpen] = useState(false);
  const [addForm, setAddForm] = useState<AddForm | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<{ quantity: string; avg_price: string }>({ quantity: "", avg_price: "" });
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const fetchHoldings = async () => {
    try {
      const { data } = await api.get<Holding[]>(`/portfolios/${portfolioId}/holdings`);
      setHoldings(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchHoldings(); }, [portfolioId]);

  const handleStockSelect = (ticker: string, name: string) => {
    setAddForm({ ticker, name, quantity: "", avg_price: "" });
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addForm) return;
    setSaving(true);
    try {
      const { data } = await api.post<Holding>(`/portfolios/${portfolioId}/holdings`, {
        ticker: addForm.ticker,
        name: addForm.name,
        quantity: Number(addForm.quantity),
        avg_price: Number(addForm.avg_price),
      });
      setHoldings((prev) => [...prev, data]);
      setAddForm(null);
    } finally {
      setSaving(false);
    }
  };

  const handleEditSave = async (holdingId: number) => {
    setSaving(true);
    try {
      const { data } = await api.patch<Holding>(`/portfolios/holdings/${holdingId}`, {
        quantity: Number(editForm.quantity),
        avg_price: Number(editForm.avg_price),
      });
      setHoldings((prev) => prev.map((h) => (h.id === holdingId ? data : h)));
      setEditId(null);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (holdingId: number) => {
    await api.delete(`/portfolios/holdings/${holdingId}`);
    setHoldings((prev) => prev.filter((h) => h.id !== holdingId));
    setDeleteConfirmId(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">보유 종목</h1>
        <Button onClick={() => setSearchOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          종목 추가
        </Button>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">불러오는 중...</p>
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
                {["종목", "수량", "평균단가", ""].map((h) => (
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
                          <Button size="sm" onClick={() => handleEditSave(h.id)} disabled={saving}>저장</Button>
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
                      <td className="px-4 py-3 tabular-nums">{formatKRW(h.avg_price)}</td>
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
                      <Button size="sm" onClick={handleAdd} disabled={saving || !addForm.quantity || !addForm.avg_price}>추가</Button>
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
              <Button variant="destructive" className="flex-1" onClick={() => handleDelete(deleteConfirmId)}>삭제</Button>
            </div>
          </div>
        </div>
      )}

      <StockSearchDialog
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelect={handleStockSelect}
      />
    </div>
  );
}
