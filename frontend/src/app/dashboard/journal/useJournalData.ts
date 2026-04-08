"use client";

import { useState, useMemo, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Portfolio {
  id: number;
  name: string;
}

export interface SummaryHolding {
  ticker: string;
  name: string;
  current_price: number | null;
  avg_price: number;
  market_value_krw: number | null;
  pnl_rate: number | null;
}

export interface Transaction {
  id: number;
  portfolio_id: number;
  ticker: string;
  type: string;
  quantity: string;
  price: string;
  traded_at: string;
  memo: string | null;
  tags: string[] | null;
}

export type TypeFilter = "ALL" | "BUY" | "SELL";

export interface RetrospectiveItem {
  ticker: string;
  name: string;
  buyPrice: number;
  currentPrice: number | null;
  pnlRate: number | null;
  marketValueKrw: number | null;
  tradedAt: string;
}

export interface UseJournalDataResult {
  portfolios: Portfolio[];
  portfoliosLoading: boolean;
  transactions: Transaction[];
  summaryHoldings: SummaryHolding[];
  activePortfolioId: number | null;
  setSelectedPortfolioId: (id: number) => void;
  selectedPortfolioId: number | null;
  typeFilter: TypeFilter;
  setTypeFilter: (value: TypeFilter) => void;
  memoOnly: boolean;
  setMemoOnly: (value: boolean) => void;
  selectedTag: string | null;
  setSelectedTag: (value: string | null) => void;
  selectedMonth: string;
  setSelectedMonth: (value: string) => void;
  selectedTicker: string;
  setSelectedTicker: (value: string) => void;
  searchInput: string;
  setSearchInput: (value: string) => void;
  filtered: Transaction[];
  tickerNameMap: Map<string, string>;
  availableMonths: string[];
  availableTickers: string[];
  retrospectiveItems: RetrospectiveItem[];
  isLoading: boolean;
}

export function useJournalData(): UseJournalDataResult {
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<number | null>(null);
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("ALL");
  const [memoOnly, setMemoOnly] = useState(false);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [selectedMonth, setSelectedMonth] = useState<string>("ALL");
  const [selectedTicker, setSelectedTicker] = useState<string>("ALL");
  const [searchInput, setSearchInput] = useState<string>("");
  const [debouncedSearch, setDebouncedSearch] = useState<string>("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce search input (300ms)
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchInput]);

  const { data: portfolios = [], isLoading: portfoliosLoading } = useQuery<Portfolio[]>({
    queryKey: ["portfolios"],
    queryFn: () => api.get<Portfolio[]>("/portfolios").then((r) => r.data),
    staleTime: 60_000,
  });

  const activePortfolioId = selectedPortfolioId ?? portfolios[0]?.id ?? null;

  const { data: transactions = [], isLoading: txnsLoading } = useQuery<Transaction[]>({
    queryKey: ["journal-transactions", activePortfolioId],
    queryFn: () =>
      api
        .get<Transaction[]>(`/portfolios/${activePortfolioId}/transactions`, {
          params: { limit: 100 },
        })
        .then((r) => r.data),
    enabled: activePortfolioId !== null,
    staleTime: 60_000,
  });

  const { data: summaryHoldings = [] } = useQuery<SummaryHolding[]>({
    queryKey: ["dashboard-summary-holdings"],
    queryFn: () =>
      api
        .get<{ holdings: SummaryHolding[] }>("/dashboard/summary")
        .then((r) => r.data.holdings ?? []),
    staleTime: 60_000,
  });

  const retrospectiveItems = useMemo((): RetrospectiveItem[] => {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 30);
    const recentBuys = transactions.filter(
      (t) => t.type === "BUY" && new Date(t.traded_at) >= cutoff
    );
    const byTicker = new Map<string, Transaction>();
    for (const txn of recentBuys) {
      const existing = byTicker.get(txn.ticker);
      if (!existing || txn.traded_at > existing.traded_at) {
        byTicker.set(txn.ticker, txn);
      }
    }
    const holdingMap = new Map(summaryHoldings.map((h) => [h.ticker, h]));
    return Array.from(byTicker.values())
      .map((txn) => {
        const holding = holdingMap.get(txn.ticker);
        const currentPrice = holding?.current_price ?? null;
        const buyPrice = Number(txn.price);
        const pnlRate =
          currentPrice != null && buyPrice > 0
            ? ((currentPrice - buyPrice) / buyPrice) * 100
            : null;
        return {
          ticker: txn.ticker,
          name: holding?.name ?? txn.ticker,
          buyPrice,
          currentPrice,
          pnlRate,
          marketValueKrw: holding?.market_value_krw ?? null,
          tradedAt: txn.traded_at,
        };
      })
      .sort((a, b) => (b.marketValueKrw ?? 0) - (a.marketValueKrw ?? 0))
      .slice(0, 5);
  }, [transactions, summaryHoldings]);

  const availableMonths = useMemo(() => {
    const months = new Set(transactions.map((t) => t.traded_at.slice(0, 7)));
    return Array.from(months).sort((a, b) => b.localeCompare(a));
  }, [transactions]);

  const availableTickers = useMemo(() => {
    const tickers = new Set(transactions.map((t) => t.ticker));
    return Array.from(tickers).sort();
  }, [transactions]);

  const filtered = useMemo(() => {
    return transactions.filter((txn) => {
      if (typeFilter !== "ALL" && txn.type !== typeFilter) return false;
      if (memoOnly && !txn.memo) return false;
      if (selectedTag && !(txn.tags ?? []).includes(selectedTag)) return false;
      if (selectedMonth !== "ALL" && !txn.traded_at.startsWith(selectedMonth)) return false;
      if (selectedTicker !== "ALL" && txn.ticker !== selectedTicker) return false;
      if (debouncedSearch && !(txn.memo ?? "").toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
      return true;
    });
  }, [transactions, typeFilter, memoOnly, selectedTag, selectedMonth, selectedTicker, debouncedSearch]);

  const tickerNameMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const h of summaryHoldings) {
      map.set(h.ticker, h.name);
    }
    return map;
  }, [summaryHoldings]);

  const isLoading = portfoliosLoading || (activePortfolioId !== null && txnsLoading);

  return {
    portfolios,
    portfoliosLoading,
    transactions,
    summaryHoldings,
    activePortfolioId,
    setSelectedPortfolioId,
    selectedPortfolioId,
    typeFilter,
    setTypeFilter,
    memoOnly,
    setMemoOnly,
    selectedTag,
    setSelectedTag,
    selectedMonth,
    setSelectedMonth,
    selectedTicker,
    setSelectedTicker,
    searchInput,
    setSearchInput,
    filtered,
    tickerNameMap,
    availableMonths,
    availableTickers,
    retrospectiveItems,
    isLoading,
  };
}
