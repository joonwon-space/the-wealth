"use client";

import { useState, useMemo } from "react";
import { BookOpen, ArrowUpCircle, ArrowDownCircle, MessageSquare } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatPrice } from "@/lib/format";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Portfolio {
  id: number;
  name: string;
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
}

function TransactionCard({ txn }: TransactionCardProps) {
  const isBuy = txn.type === "BUY";
  const total = Number(txn.quantity) * Number(txn.price);

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
            <span className="font-semibold text-sm">{txn.ticker}</span>
            <span
              className={cn(
                "ml-2 rounded px-1.5 py-0.5 text-[11px] font-medium",
                isBuy
                  ? "bg-rise/10 text-rise"
                  : "bg-fall/10 text-fall"
              )}
            >
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

  const filtered = useMemo(() => {
    return transactions.filter((txn) => {
      if (typeFilter !== "ALL" && txn.type !== typeFilter) return false;
      if (memoOnly && !txn.memo) return false;
      return true;
    });
  }, [transactions, typeFilter, memoOnly]);

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
      <div className="flex flex-wrap items-center gap-2">
        {(["ALL", "BUY", "SELL"] as TypeFilter[]).map((t) => (
          <Button
            key={t}
            variant={typeFilter === t ? "default" : "outline"}
            size="sm"
            onClick={() => setTypeFilter(t)}
            className="min-h-[36px]"
          >
            {t === "ALL" ? "전체" : t === "BUY" ? "매수" : "매도"}
          </Button>
        ))}
        <Button
          variant={memoOnly ? "default" : "outline"}
          size="sm"
          onClick={() => setMemoOnly((v) => !v)}
          className="min-h-[36px] gap-1"
        >
          <MessageSquare className="h-3.5 w-3.5" />
          메모만
        </Button>
      </div>

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
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
          <BookOpen className="mb-3 h-10 w-10 text-muted-foreground/40" />
          <p className="font-semibold">거래 내역이 없습니다</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {memoOnly ? "메모가 있는 거래 내역이 없습니다." : "해당 포트폴리오에 거래 내역이 없습니다."}
          </p>
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
                    <TransactionCard key={txn.id} txn={txn} />
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
