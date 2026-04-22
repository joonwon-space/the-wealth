"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, BadgeCheck, Coins, Scale, Search, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StreamCard } from "@/components/stream/stream-card";
import { cn } from "@/lib/utils";

type StreamKind = "alert" | "fill" | "dividend" | "rebalance" | "routine";

interface StreamItem {
  id: string;
  kind: StreamKind;
  ts: string;
  title: string;
  sub: string | null;
  payload: Record<string, unknown>;
}

interface StreamResponse {
  items: StreamItem[];
  next_cursor: string | null;
}

const FILTERS: Array<{ value: "all" | StreamKind; label: string }> = [
  { value: "all", label: "전체" },
  { value: "alert", label: "알림" },
  { value: "fill", label: "체결" },
  { value: "rebalance", label: "리밸런싱" },
  { value: "dividend", label: "배당" },
  { value: "routine", label: "루틴" },
];

const KIND_ICON: Record<StreamKind, typeof AlertCircle> = {
  alert: AlertCircle,
  fill: BadgeCheck,
  rebalance: Scale,
  dividend: Coins,
  routine: Sparkles,
};

function formatRelative(ts: string): string {
  const date = new Date(ts);
  const diffMs = Date.now() - date.getTime();
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 1) return "방금";
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}일 전`;
  return date.toLocaleDateString("ko-KR");
}

export default function StreamPage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["value"]>("all");
  const [query, setQuery] = useState("");

  const { data, isLoading, isError, refetch } = useQuery<StreamResponse>({
    queryKey: ["stream", filter],
    queryFn: async () =>
      (
        await api.get<StreamResponse>("/stream", {
          params: { filter, limit: 50 },
        })
      ).data,
    staleTime: 30_000,
  });

  const filtered = useMemo(() => {
    if (!data) return [];
    const needle = query.trim().toLowerCase();
    if (!needle) return data.items;
    return data.items.filter(
      (it) =>
        it.title.toLowerCase().includes(needle) ||
        (it.sub ?? "").toLowerCase().includes(needle),
    );
  }, [data, query]);

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-baseline gap-3">
        <h1 className="text-2xl font-bold tracking-tight">스트림</h1>
        <p className="text-sm text-muted-foreground">
          알림·체결·배당·리밸런싱·루틴 한 피드로 모아보기
        </p>
      </header>

      <div className="flex flex-wrap gap-2 rounded-lg border border-border bg-card p-2">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            aria-pressed={filter === f.value}
            onClick={() => setFilter(f.value)}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-semibold transition-colors",
              filter === f.value
                ? "bg-foreground text-background"
                : "bg-muted text-muted-foreground hover:bg-muted/70",
            )}
          >
            {f.label}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="검색"
              className="h-8 w-40 rounded-md border border-border bg-background pl-7 pr-2 text-xs tabular-nums outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      ) : isError ? (
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <p className="text-sm text-destructive">
              스트림을 불러오지 못했습니다.
            </p>
            <button
              type="button"
              onClick={() => refetch()}
              className="inline-flex items-center gap-1 rounded-md border border-border bg-card px-2.5 py-1 text-xs font-semibold hover:bg-muted"
            >
              다시 시도
            </button>
          </CardContent>
        </Card>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
            <Sparkles className="size-6 text-muted-foreground/50" />
            <p className="text-sm font-semibold">조건에 맞는 이벤트가 없습니다.</p>
            <p className="text-xs text-muted-foreground">
              필터나 검색어를 바꿔보세요.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {filtered.map((item) => {
            const Icon = KIND_ICON[item.kind];
            const ticker =
              (item.payload.ticker as string | undefined) ?? undefined;
            return (
              <StreamCard
                key={item.id}
                kind={item.kind}
                title={item.title}
                sub={item.sub ?? undefined}
                ts={formatRelative(item.ts)}
                badgeLabel={undefined}
              >
                {ticker && (
                  <div className="flex gap-2">
                    <Link
                      href={`/dashboard/stocks/${ticker}`}
                      className={cn(
                        "inline-flex items-center gap-1 rounded-md border border-border bg-card px-2.5 py-1 text-xs font-semibold text-foreground hover:bg-muted",
                      )}
                    >
                      <Icon className="size-3" /> 종목 보기
                    </Link>
                  </div>
                )}
              </StreamCard>
            );
          })}
        </div>
      )}
    </div>
  );
}
