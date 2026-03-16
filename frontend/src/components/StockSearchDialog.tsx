"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { api } from "@/lib/api";

interface StockItem {
  ticker: string;
  name: string;
  market: string;
}

interface Props {
  open: boolean;
  onClose: () => void;
  onSelect: (ticker: string, name: string) => void;
}

export function StockSearchDialog({ open, onClose, onSelect }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockItem[]>([]);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const search = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.get<{ items: StockItem[] }>("/stocks/search", { params: { q } });
      setResults(data.items ?? []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(query), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, search]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setResults([]);
    }
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-md rounded-xl border bg-background shadow-lg">
        <div className="flex items-center gap-2 border-b px-4 py-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="종목명 또는 티커 검색... (예: 삼성, 005930)"
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="max-h-72 overflow-y-auto">
          {loading && (
            <div className="px-4 py-6 text-center text-sm text-muted-foreground">검색 중...</div>
          )}
          {!loading && results.length === 0 && query && (
            <div className="px-4 py-6 text-center text-sm text-muted-foreground">검색 결과 없음</div>
          )}
          {!loading && results.length === 0 && !query && (
            <div className="px-4 py-6 text-center text-sm text-muted-foreground">종목명 또는 티커를 입력하세요</div>
          )}
          {results.map((item) => (
            <button
              key={item.ticker}
              onClick={() => {
                onSelect(item.ticker, item.name);
                onClose();
              }}
              className="flex w-full items-center justify-between px-4 py-3 text-sm hover:bg-accent"
            >
              <div className="flex items-center gap-2">
                <span className="font-medium">{item.name}</span>
                <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">{item.market}</span>
              </div>
              <span className="font-mono text-muted-foreground">{item.ticker}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
