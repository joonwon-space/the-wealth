"use client";

import { MessageSquare, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type TypeFilter = "ALL" | "BUY" | "SELL";

const PRESET_TAGS = ["#실적발표", "#배당투자", "#단기매매", "#장기투자", "#리밸런싱"] as const;

export interface JournalFiltersProps {
  typeFilter: TypeFilter;
  onTypeFilterChange: (value: TypeFilter) => void;
  memoOnly: boolean;
  onMemoOnlyChange: (value: boolean) => void;
  selectedTag: string | null;
  onTagChange: (value: string | null) => void;
  selectedMonth: string;
  onMonthChange: (value: string) => void;
  selectedTicker: string;
  onTickerChange: (value: string) => void;
  searchInput: string;
  onSearchInputChange: (value: string) => void;
  availableMonths: string[];
  availableTickers: string[];
  onResetFilters: () => void;
}

export function JournalFilters({
  typeFilter,
  onTypeFilterChange,
  memoOnly,
  onMemoOnlyChange,
  selectedTag,
  onTagChange,
  selectedMonth,
  onMonthChange,
  selectedTicker,
  onTickerChange,
  searchInput,
  onSearchInputChange,
  availableMonths,
  availableTickers,
}: JournalFiltersProps) {
  return (
    <div className="space-y-2">
      {/* Row 1: type + memo + month + ticker */}
      <div className="flex flex-wrap items-center gap-2">
        {(["ALL", "BUY", "SELL"] as TypeFilter[]).map((t) => (
          <Button
            key={t}
            variant={typeFilter === t ? "default" : "outline"}
            size="sm"
            onClick={() => onTypeFilterChange(t)}
            className="min-h-[36px]"
          >
            {t === "ALL" ? "전체" : t === "BUY" ? "매수" : "매도"}
          </Button>
        ))}
        <Button
          variant={memoOnly ? "default" : "outline"}
          size="sm"
          onClick={() => onMemoOnlyChange(!memoOnly)}
          className="min-h-[36px] gap-1"
        >
          <MessageSquare className="h-3.5 w-3.5" />
          메모만
        </Button>

        {/* Month filter */}
        {availableMonths.length > 0 && (
          <select
            value={selectedMonth}
            onChange={(e) => onMonthChange(e.target.value)}
            className="h-9 rounded-md border bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            aria-label="월별 필터"
          >
            <option value="ALL">전체 월</option>
            {availableMonths.map((m) => (
              <option key={m} value={m}>
                {m.replace("-", "년 ")}월
              </option>
            ))}
          </select>
        )}

        {/* Ticker filter */}
        {availableTickers.length > 0 && (
          <select
            value={selectedTicker}
            onChange={(e) => onTickerChange(e.target.value)}
            className="h-9 rounded-md border bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            aria-label="종목별 필터"
          >
            <option value="ALL">전체 종목</option>
            {availableTickers.map((ticker) => (
              <option key={ticker} value={ticker}>
                {ticker}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Row 2: keyword search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          value={searchInput}
          onChange={(e) => onSearchInputChange(e.target.value)}
          placeholder="메모 내용 검색..."
          className="h-9 w-full rounded-md border bg-background pl-8 pr-8 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          aria-label="메모 검색"
        />
        {searchInput && (
          <button
            onClick={() => onSearchInputChange("")}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            aria-label="검색어 지우기"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Tag filter */}
      <div className="flex flex-wrap gap-1.5">
        {PRESET_TAGS.map((tag) => (
          <button
            key={tag}
            onClick={() => onTagChange(selectedTag === tag ? null : tag)}
            className={cn(
              "rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors",
              selectedTag === tag
                ? "border-transparent text-white"
                : "hover:bg-accent text-muted-foreground"
            )}
            style={
              selectedTag === tag
                ? { background: "var(--accent-indigo)" }
                : undefined
            }
          >
            {tag}
          </button>
        ))}
        {selectedTag && (
          <button
            onClick={() => onTagChange(null)}
            className="rounded-full px-2 py-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
          >
            ✕ 초기화
          </button>
        )}
      </div>
    </div>
  );
}
