"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Search, Star, TrendingUp } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StockSearchDialog } from "@/components/StockSearchDialog";
import { useState } from "react";

interface WatchlistItem {
  id: number;
  ticker: string;
  name: string;
  market: string;
}

export default function StocksLandingPage() {
  const router = useRouter();
  const [searchOpen, setSearchOpen] = useState(false);

  const { data: watchlist, isLoading } = useQuery<WatchlistItem[]>({
    queryKey: ["watchlist"],
    queryFn: async () => (await api.get<WatchlistItem[]>("/watchlist")).data,
    staleTime: 60_000,
  });

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">종목</h1>
        <p className="text-sm text-muted-foreground">
          관심종목과 검색으로 바로 이동.
        </p>
      </header>

      <button
        type="button"
        onClick={() => setSearchOpen(true)}
        className="flex w-full items-center gap-3 rounded-lg border border-border bg-card px-4 py-3 text-left text-sm text-muted-foreground hover:bg-muted/40"
      >
        <Search className="size-4" />
        종목명 또는 티커로 검색
      </button>

      <section className="space-y-2">
        <h2 className="text-section-header flex items-center gap-1.5">
          <Star className="size-3.5" />
          관심 종목
        </h2>
        {isLoading ? (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        ) : !watchlist || watchlist.length === 0 ? (
          <Card>
            <CardContent className="p-6 text-center">
              <Star className="mx-auto mb-2 size-6 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                관심 종목이 없습니다. 위 검색으로 찾아 추가해보세요.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {watchlist.map((item) => (
              <Link
                key={item.id}
                href={`/dashboard/stocks/${item.ticker}`}
                className="flex items-center gap-3 rounded-lg border border-border bg-card px-4 py-3 text-sm hover:bg-muted/40"
              >
                <TrendingUp className="size-4 text-muted-foreground" />
                <div className="min-w-0">
                  <div className="truncate font-semibold">{item.name || item.ticker}</div>
                  <div className="text-xs text-muted-foreground tabular-nums">
                    {item.ticker} · {item.market}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      <StockSearchDialog
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelect={(ticker) => {
          setSearchOpen(false);
          router.push(`/dashboard/stocks/${ticker}`);
        }}
      />
    </div>
  );
}
