"use client";

import { BookOpen, ArrowUpCircle, ArrowDownCircle, MessageSquare, TrendingUp, TrendingDown } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { formatKRW, formatUSD } from "@/lib/format";

/** Infer currency from ticker: 1-5 uppercase letters → USD, else KRW */
function getCurrencyFromTicker(ticker: string): "KRW" | "USD" {
  return /^[A-Z]{1,5}$/.test(ticker) ? "USD" : "KRW";
}

function formatTxnPrice(value: string | number, ticker: string): string {
  return getCurrencyFromTicker(ticker) === "USD"
    ? formatUSD(value)
    : formatKRW(value);
}
import type { Transaction } from "./useJournalData";

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

function TagBadge({ tag }: { tag: string }) {
  return (
    <span className="inline-flex items-center rounded-full bg-accent/70 px-2 py-0.5 text-[10px] font-medium text-accent-foreground">
      {tag}
    </span>
  );
}

interface TransactionCardProps {
  txn: Transaction;
  stockName?: string;
}

function TransactionCard({ txn, stockName }: TransactionCardProps) {
  const isBuy = txn.type === "BUY";
  const total = Number(txn.quantity) * Number(txn.price);
  const hasTags = txn.tags && txn.tags.length > 0;

  return (
    <div className="flex gap-3 rounded-lg border bg-card p-3">
      <div className="mt-0.5 shrink-0">
        {isBuy ? (
          <ArrowUpCircle className="h-5 w-5 text-rise" aria-label="매수" />
        ) : (
          <ArrowDownCircle className="h-5 w-5 text-fall" aria-label="매도" />
        )}
      </div>

      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-center justify-between gap-2">
          <div>
            <span className="font-semibold text-sm">{stockName ?? txn.ticker}</span>
            {stockName && <span className="ml-1 text-xs text-muted-foreground">{txn.ticker}</span>}
            <span
              className={cn(
                "ml-2 inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[11px] font-medium",
                isBuy ? "bg-rise/10 text-rise" : "bg-fall/10 text-fall"
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
            {formatTxnPrice(Number(txn.price), txn.ticker)}
          </span>
          <span className="font-medium text-foreground">
            = {formatTxnPrice(total, txn.ticker)}
          </span>
        </div>

        {hasTags && (
          <div className="mt-1 flex flex-wrap gap-1">
            {txn.tags!.map((tag) => (
              <TagBadge key={tag} tag={tag} />
            ))}
          </div>
        )}

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

export interface JournalTimelineProps {
  isLoading: boolean;
  filtered: Transaction[];
  transactions: Transaction[];
  activePortfolioId: number | null;
  tickerNameMap: Map<string, string>;
  onResetFilters: () => void;
}

export function JournalTimeline({
  isLoading,
  filtered,
  transactions,
  activePortfolioId,
  tickerNameMap,
  onResetFilters,
}: JournalTimelineProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2].map((i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-4 w-40" />
            {[1, 2].map((j) => <Skeleton key={j} className="h-20 w-full rounded-lg" />)}
          </div>
        ))}
      </div>
    );
  }

  if (filtered.length === 0 && transactions.length > 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
        <BookOpen className="mb-3 h-10 w-10 text-muted-foreground/40" />
        <p className="font-semibold">필터 조건에 맞는 거래가 없습니다</p>
        <p className="mt-1 text-sm text-muted-foreground">
          다른 필터 조건을 선택하거나 필터를 초기화해 보세요.
        </p>
        <Button variant="outline" size="sm" className="mt-4" onClick={onResetFilters}>
          필터 초기화
        </Button>
      </div>
    );
  }

  if (filtered.length === 0) {
    return (
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
    );
  }

  const grouped = groupByDate(filtered);
  const sortedDates = [...grouped.keys()].sort((a, b) => b.localeCompare(a));

  return (
    <div className="space-y-6">
      {sortedDates.map((dateKey) => {
        const dayTxns = grouped.get(dateKey) ?? [];
        return (
          <div key={dateKey} className="space-y-2">
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-muted-foreground">
                {formatDateGroup(dateKey + "T00:00:00")}
              </span>
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs text-muted-foreground">{dayTxns.length}건</span>
            </div>

            <div className="space-y-2">
              {dayTxns.map((txn) => (
                <TransactionCard key={txn.id} txn={txn} stockName={tickerNameMap.get(txn.ticker)} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
