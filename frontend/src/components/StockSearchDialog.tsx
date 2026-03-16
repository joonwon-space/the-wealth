"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { api } from "@/lib/api";

interface StockItem {
  prdt_name: string;
  shtn_pdno: string;
  pdno: string;
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
            placeholder="종목명 또는 티커 검색..."
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
          {results.map((item) => (
            <button
              key={item.pdno}
              onClick={() => {
                onSelect(item.shtn_pdno ?? item.pdno, item.prdt_name);
                onClose();
              }}
              className="flex w-full items-center justify-between px-4 py-3 text-sm hover:bg-accent"
            >
              <span className="font-medium">{item.prdt_name}</span>
              <span className="text-muted-foreground">{item.shtn_pdno ?? item.pdno}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
