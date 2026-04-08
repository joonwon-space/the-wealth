"use client";

import { BookOpen } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { JournalFilters } from "./JournalFilters";
import { JournalTimeline } from "./JournalTimeline";
import { useJournalData } from "./useJournalData";

export default function JournalPage() {
  const {
    portfolios,
    portfoliosLoading,
    transactions,
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
  } = useJournalData();

  const handleResetFilters = () => {
    setTypeFilter("ALL");
    setMemoOnly(false);
    setSelectedTag(null);
    setSelectedMonth("ALL");
    setSelectedTicker("ALL");
    setSearchInput("");
  };

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
              <div key={item.ticker} className="rounded-lg border bg-card p-3 space-y-1.5">
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
        onResetFilters={handleResetFilters}
      />

      <JournalTimeline
        isLoading={isLoading}
        filtered={filtered}
        transactions={transactions}
        activePortfolioId={activePortfolioId}
        tickerNameMap={tickerNameMap}
        onResetFilters={handleResetFilters}
      />
    </div>
  );
}
