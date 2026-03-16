"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Trash2, Wallet } from "lucide-react";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

interface Portfolio {
  id: number;
  name: string;
  currency: string;
  created_at: string;
}

export default function PortfoliosPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  const fetchPortfolios = async () => {
    try {
      const { data } = await api.get<Portfolio[]>("/portfolios");
      setPortfolios(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchPortfolios(); }, []);

  const handleDelete = async (id: number) => {
    if (!confirm("포트폴리오를 삭제하시겠습니까?")) return;
    await api.delete(`/portfolios/${id}`);
    setPortfolios((prev) => prev.filter((p) => p.id !== id));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">포트폴리오</h1>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          <Plus className="h-4 w-4" />
          새 포트폴리오
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-xl border p-5 space-y-3">
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-3 w-16" />
              <Skeleton className="h-3 w-32" />
            </div>
          ))}
        </div>
      ) : portfolios.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
          <Wallet className="mb-3 h-10 w-10 text-muted-foreground/40" />
          <p className="font-medium">포트폴리오가 없습니다</p>
          <p className="mt-1 text-sm text-muted-foreground">새 포트폴리오를 만들어 종목을 추가하세요.</p>
          <button
            onClick={() => setShowModal(true)}
            className="mt-4 flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            <Plus className="h-4 w-4" />
            새 포트폴리오
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {portfolios.map((p) => (
            <div key={p.id} className="group relative rounded-xl border bg-card p-5 shadow-sm hover:shadow-md transition-shadow">
              <Link href={`/dashboard/portfolios/${p.id}`} className="block">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <Wallet className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-semibold">{p.name}</p>
                    <p className="text-xs text-muted-foreground">{p.currency}</p>
                  </div>
                </div>
              </Link>
              <button
                onClick={() => handleDelete(p.id)}
                className="absolute right-3 top-3 rounded-md p-1.5 text-muted-foreground opacity-0 group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive transition-all"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <CreatePortfolioModal
          onClose={() => setShowModal(false)}
          onCreate={(p) => { setPortfolios((prev) => [...prev, p]); setShowModal(false); }}
        />
      )}
    </div>
  );
}

function CreatePortfolioModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (p: Portfolio) => void;
}) {
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("KRW");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.post<Portfolio>("/portfolios", { name, currency });
      onCreate(data);
    } catch {
      setError("생성에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-sm rounded-xl border bg-background p-6 shadow-lg">
        <h2 className="mb-4 text-lg font-semibold">새 포트폴리오</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="space-y-1">
            <label className="text-sm font-medium">이름</label>
            <input
              autoFocus
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              placeholder="내 포트폴리오"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">기준 통화</label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="KRW">KRW — 한국 원</option>
              <option value="USD">USD — 미국 달러</option>
            </select>
          </div>
          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
            >
              {loading ? "생성 중..." : "생성"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
