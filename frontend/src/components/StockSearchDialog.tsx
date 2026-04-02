"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Clock, Search, X } from "lucide-react";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

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

const RECENT_KEY = "stock_search_recent";
const MAX_RECENT = 5;

function getRecent(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is string => typeof item === "string");
  } catch {
    return [];
  }
}

function addRecent(query: string): void {
  const list = getRecent().filter((q) => q !== query);
  list.unshift(query);
  localStorage.setItem(RECENT_KEY, JSON.stringify(list.slice(0, MAX_RECENT)));
}

function removeRecent(query: string): void {
  const list = getRecent().filter((q) => q !== query);
  localStorage.setItem(RECENT_KEY, JSON.stringify(list));
}

export function StockSearchDialog({ open, onClose, onSelect }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [recent, setRecent] = useState<string[]>([]);
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
    if (open) {
      setRecent(getRecent());
    } else {
      setQuery("");
      setResults([]);
    }
  }, [open]);

  const handleSelect = (item: StockItem) => {
    addRecent(item.name);
    onSelect(item.ticker, item.name);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
      <DialogContent className="max-w-md p-0 gap-0">
        <DialogHeader className="px-4 pt-4 pb-0">
          <DialogTitle className="sr-only">Stock Search</DialogTitle>
        </DialogHeader>

        <div className="flex items-center gap-2 border-b px-4 py-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <Input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name or ticker (e.g. Samsung, AAPL)"
            className="border-0 shadow-none focus-visible:ring-0 px-0"
          />
        </div>

        <div className="max-h-72 overflow-y-auto">
          {/* Recent searches (shown when no query) */}
          {!query && recent.length > 0 && (
            <div className="px-4 py-2">
              <p className="mb-1 text-xs font-medium text-muted-foreground">Recent</p>
              {recent.map((r) => (
                <div key={r} className="flex items-center justify-between">
                  <button
                    onClick={() => setQuery(r)}
                    className="flex items-center gap-2 py-1.5 text-sm hover:text-foreground text-muted-foreground"
                  >
                    <Clock className="h-3 w-3" />
                    {r}
                  </button>
                  <button
                    onClick={() => { removeRecent(r); setRecent(getRecent()); }}
                    className="p-1 text-muted-foreground/50 hover:text-muted-foreground"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {loading && (
            <div className="px-4 py-6 text-center text-sm text-muted-foreground">Searching...</div>
          )}
          {!loading && results.length === 0 && query && (
            <div className="px-4 py-6 text-center text-sm text-muted-foreground">No results</div>
          )}
          {!loading && results.length === 0 && !query && recent.length === 0 && (
            <div className="px-4 py-6 text-center text-sm text-muted-foreground">Enter a stock name or ticker</div>
          )}
          {results.map((item) => (
            <button
              key={item.ticker}
              onClick={() => handleSelect(item)}
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
      </DialogContent>
    </Dialog>
  );
}
