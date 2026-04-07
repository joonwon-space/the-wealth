"use client";

import { useState, useMemo, useEffect, useRef } from "react";
import { BookOpen, ArrowUpCircle, ArrowDownCircle, MessageSquare, TrendingUp, TrendingDown } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatPrice } from "@/lib/format";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { JournalFilters } from "./JournalFilters";

interface Portfolio {
  id: number;
  name: string;
}

interface SummaryHolding {
  ticker: string;
  name: string;
  current_price: number | null;
  avg_price: number;
  market_value_krw: number | null;
  pnl_rate: number | null;
}

interface Transaction {
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

type TypeFilter = "ALL" | "BUY" | "SELL";

function formatDateGroup(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
  });
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
}

function groupByDate(transactions: Transaction[]): Map<string, Transaction[]> {
  const groups = new Map<string, Transaction[]>();
  for (const txn of transactions) {
    const key = txn.traded_at.slice(0, 10);
    const existing = groups.get(key) ?? [];
    groups.set(key, [...existing, txn]);
  }
  return groups;
}

interface TransactionCardProps {
  txn: Transaction;
  stockName?: string;
}

function TagBadge({ tag }: { tag: string }) {
  return (
    <span className="inline-flex items-center rounded-full bg-accent/70 px-2 py-0.5 text-[10px] font-medium text-accent-foreground">
      {tag}
    </span>
  );
}

function TransactionCard({ txn, stockName }: TransactionCardProps) {
  const isBuy = txn.type === "BUY";
  const total = Number(txn.quantity) * Number(txn.price);
  const hasTags = txn.tags && txn.tags.length > 0;

  return (
    <div className="flex gap-3 rounded-lg border bg-card p-3">
      {/* Type icon */}
      <div className="mt-0.5 shrink-0">
        {isBuy ? (
          <ArrowUpCircle className="h-5 w-5 text-rise" aria-label="매수" />
        ) : (
          <ArrowDownCircle className="h-5 w-5 text-fall" aria-label="매도" />
        )}
      </div>

      {/* Main content */}
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-center justify-between gap-2">
          <div>
            <span className="font-semibold text-sm">{stockName ?? txn.ticker}</span>
            {stockName && <span className="ml-1 text-xs text-muted-foreground">{txn.ticker}</span>}
            <span
              className={cn(
                "ml-2 inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[11px] font-medium",
                isBuy
                  ? "bg-rise/10 text-rise"
                  : "bg-fall/10 text-fall"
              )}
              aria-label={isBuy ? "매수" : "매도"}
            >
              {isBuy ? (
                <TrendingUp className="h-2.5 w-2.5" aria-hidden="true" />
              ) : (
                <TrendingDown className="h-2.5 w-2.5" aria-hidden="true" />
              )}
              {isBuy ? "매수" : "매도"}
            </span>
          </div>
          <span className="text-xs text-muted-foreground">{formatTime(txn.traded_at)}</span>
        </div>

        <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
          <span>
            {Number(txn.quantity).toLocaleString("ko-KR")}주 &times;{" "}
            {formatPrice(Number(txn.price), "KRW")}
          </span>
          <span className="font-medium text-foreground">
            = {formatPrice(total, "KRW")}
          </span>
        </div>

        {/* Tags */}
        {hasTags && (
          <div className="mt-1 flex flex-wrap gap-1">
            {txn.tags!.map((tag) => (
              <TagBadge key={tag} tag={tag} />
            ))}
          </div>
        )}

        {/* Memo */}
        {txn.memo && (
          <div className="mt-1 flex items-start gap-1.5 rounded-md bg-muted/60 px-2.5 py-2">
            <MessageSquare className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <p className="text-xs text-foreground/80 leading-relaxed">{txn.memo}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function JournalPage() {
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

  // Auto-select first portfolio
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

  // Dashboard summary for current prices (used in retrospective widget)
  const { data: summaryHoldings = [] } = useQuery<SummaryHolding[]>({
    queryKey: ["dashboard-summary-holdings"],
    queryFn: () =>
      api
        .get<{ holdings: SummaryHolding[] }>("/dashboard/summary")
        .then((r) => r.data.holdings ?? []),
    staleTime: 60_000,
  });

  // Retrospective: recent 30-day BUY transactions, max 5, sorted by market_value_krw desc
  const retrospectiveItems = useMemo(() => {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 30);
    const recentBuys = transactions.filter(
      (t) => t.type === "BUY" && new Date(t.traded_at) >= cutoff
    );
    // Deduplicate by ticker, keep the most recent buy for each ticker
    const byTicker = new Map<string, Transaction>();
    for (const txn of recentBuys) {
      const existing = byTicker.get(txn.ticker);
      if (!existing || txn.traded_at > existing.traded_at) {
        byTicker.set(txn.ticker, txn);
      }
    }
    // Match with current prices
    const holdingMap = new Map(summaryHoldings.map((h) => [h.ticker, h]));
    const items = Array.from(byTicker.values())
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
      // Sort by market value desc (largest position first), fallback to buyPrice
      .sort((a, b) => (b.marketValueKrw ?? 0) - (a.marketValueKrw ?? 0))
      .slice(0, 5);
    return items;
  }, [transactions, summaryHoldings]);

  // Derive unique months and tickers from all transactions
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

  const grouped = useMemo(() => groupByDate(filtered), [filtered]);
  const sortedDates = useMemo(() => [...grouped.keys()].sort((a, b) => b.localeCompare(a)), [grouped]);

  const isLoading = portfoliosLoading || (activePortfolioId !== null && txnsLoading);

  if (portfoliosLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-24" />
        <div className="flex gap-2">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-9 w-24 rounded-full" />)}
        </div>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-20 w-full rounded-lg" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (portfolios.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">투자 일지</h1>
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
          <BookOpen className="mb-3 h-12 w-12 text-muted-foreground/40" />
          <p className="text-lg font-semibold">포트폴리오가 없습니다</p>
          <p className="mt-1 text-sm text-muted-foreground">
            포트폴리오를 먼저 생성하고 거래 내역을 추가하세요.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">투자 일지</h1>

      {/* 투자 결정 회고 위젯 */}
      {retrospectiveItems.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">최근 30일 매수 회고</h2>
          <p className="text-xs text-muted-foreground">최근 30일 이내 매수한 종목의 현재 손익 현황</p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {retrospectiveItems.map((item) => (
              <div
                key={item.ticker}
                className="rounded-lg border bg-card p-3 space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-sm truncate max-w-[120px]">{item.name}</div>
                    <div className="text-xs text-muted-foreground">{item.ticker}</div>
                  </div>
                  {item.pnlRate != null && (
                    <span
                      className={cn(
                        "text-sm font-bold tabular-nums",
                        item.pnlRate > 0 ? "text-rise" : item.pnlRate < 0 ? "text-fall" : ""
                      )}
                    >
                      {item.pnlRate > 0 ? "▲" : item.pnlRate < 0 ? "▼" : ""}{" "}
                      {Math.abs(item.pnlRate).toFixed(2)}%
                    </span>
                  )}
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>매수가</span>
                  <span className="tabular-nums font-medium text-foreground">
                    {item.buyPrice.toLocaleString("ko-KR")}
                  </span>
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>현재가</span>
                  <span className="tabular-nums font-medium text-foreground">
                    {item.currentPrice != null ? item.currentPrice.toLocaleString("ko-KR") : "—"}
                  </span>
                </div>
                <div className="text-[10px] text-muted-foreground/70">
                  매수일: {new Date(item.tradedAt).toLocaleDateString("ko-KR")}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Portfolio selector */}
      {portfolios.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {portfolios.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelectedPortfolioId(p.id)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-sm transition-colors",
                (selectedPortfolioId === p.id || (selectedPortfolioId === null && p.id === portfolios[0]?.id))
                  ? "bg-primary text-primary-foreground border-primary"
                  : "hover:bg-accent"
              )}
            >
              {p.name}
            </button>
          ))}
        </div>
      )}

      {/* Filters */}
      <JournalFilters
        typeFilter={typeFilter}
        onTypeFilterChange={setTypeFilter}
        memoOnly={memoOnly}
        onMemoOnlyChange={setMemoOnly}
        selectedTag={selectedTag}
        onTagChange={setSelectedTag}
        selectedMonth={selectedMonth}
        onMonthChange={setSelectedMonth}
        selectedTicker={selectedTicker}
        onTickerChange={setSelectedTicker}
        searchInput={searchInput}
        onSearchInputChange={setSearchInput}
        availableMonths={availableMonths}
        availableTickers={availableTickers}
        onResetFilters={() => {
          setTypeFilter("ALL");
          setMemoOnly(false);
          setSelectedTag(null);
          setSelectedMonth("ALL");
          setSelectedTicker("ALL");
          setSearchInput("");
        }}
      />

      {/* Timeline */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-40" />
              {[1, 2].map((j) => <Skeleton key={j} className="h-20 w-full rounded-lg" />)}
            </div>
          ))}
        </div>
      ) : filtered.length === 0 && transactions.length > 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
          <BookOpen className="mb-3 h-10 w-10 text-muted-foreground/40" />
          <p className="font-semibold">필터 조건에 맞는 거래가 없습니다</p>
          <p className="mt-1 text-sm text-muted-foreground">
            다른 필터 조건을 선택하거나 필터를 초기화해 보세요.
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-4"
            onClick={() => {
              setTypeFilter("ALL");
              setMemoOnly(false);
              setSelectedTag(null);
              setSelectedMonth("ALL");
              setSelectedTicker("ALL");
              setSearchInput("");
            }}
          >
            필터 초기화
          </Button>

        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
          <BookOpen className="mb-3 h-10 w-10 text-muted-foreground/40" />
          <p className="font-semibold">거래 내역이 없습니다</p>
          <p className="mt-1 text-sm text-muted-foreground">
            포트폴리오에 거래 내역을 추가하세요.
          </p>
          {activePortfolioId !== null && (
            <a
              href={`/dashboard/portfolios/${activePortfolioId}`}
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              거래 추가하기
            </a>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          {sortedDates.map((dateKey) => {
            const dayTxns = grouped.get(dateKey) ?? [];
            return (
              <div key={dateKey} className="space-y-2">
                {/* Date header */}
                <div className="flex items-center gap-3">
                  <span className="text-sm font-semibold text-muted-foreground">
                    {formatDateGroup(dateKey + "T00:00:00")}
                  </span>
                  <div className="h-px flex-1 bg-border" />
                  <span className="text-xs text-muted-foreground">{dayTxns.length}건</span>
                </div>

                {/* Transactions for this day */}
                <div className="space-y-2">
                  {dayTxns.map((txn) => (
                    <TransactionCard key={txn.id} txn={txn} stockName={tickerNameMap.get(txn.ticker)} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
