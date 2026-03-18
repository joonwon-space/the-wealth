"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Eye, ExternalLink, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { StockSearchDialog } from "@/components/StockSearchDialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

interface WatchlistItem {
  id: number;
  ticker: string;
  name: string;
  market: string;
}

export function WatchlistSection() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    api
      .get<WatchlistItem[]>("/watchlist")
      .then(({ data }) => setItems(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleAdd = async (ticker: string, name: string) => {
    setSearchOpen(false);
    const market = /^[A-Z]+$/.test(ticker) ? "NYSE" : "KRX";
    try {
      const { data } = await api.post<WatchlistItem>("/watchlist", { ticker, name, market });
      setItems((prev) => [data, ...prev]);
      toast.success(`${name || ticker} 관심 종목 추가`);
    } catch (err: unknown) {
      const isConflict =
        err instanceof Error
          ? err.message.includes("409")
          : (err as { response?: { status: number } })?.response?.status === 409;
      toast.error(isConflict ? "이미 추가된 종목입니다" : "추가 실패");
    }
  };

  const handleRemove = async (id: number, ticker: string) => {
    try {
      await api.delete(`/watchlist/${id}`);
      setItems((prev) => prev.filter((i) => i.id !== id));
      toast.success(`${ticker} 관심 종목 삭제`);
    } catch {
      toast.error("삭제 실패");
    }
  };

  if (loading) {
    return (
      <section className="space-y-2">
        <Skeleton className="h-5 w-24" />
        {[1, 2].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </section>
    );
  }

  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-1.5 text-base font-semibold">
          <Eye className="h-4 w-4 text-muted-foreground" />
          관심 종목
        </h2>
        <Button size="sm" variant="ghost" className="h-7 gap-1 text-xs" onClick={() => setSearchOpen(true)}>
          <Plus className="h-3.5 w-3.5" />
          추가
        </Button>
      </div>

      {items.length === 0 ? (
        <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
          <Eye className="mx-auto mb-2 h-6 w-6 opacity-40" />
          관심 종목을 추가하면 여기에 표시됩니다
        </div>
      ) : (
        <div className="divide-y rounded-lg border">
          {items.map((item) => (
            <div key={item.id} className="flex items-center justify-between px-4 py-3">
              <div className="min-w-0">
                <span className="text-sm font-medium">{item.name || item.ticker}</span>
                <span className="ml-2 text-xs text-muted-foreground">{item.ticker}</span>
                <span className="ml-1.5 rounded bg-muted px-1 py-0.5 text-[10px] text-muted-foreground">
                  {item.market}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <Link
                  href={`/dashboard/stocks/${item.ticker}`}
                  className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                  title="종목 상세"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </Link>
                <button
                  onClick={() => handleRemove(item.id, item.ticker)}
                  className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                  title="관심 종목 삭제"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <StockSearchDialog
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelect={handleAdd}
      />
    </section>
  );
}
