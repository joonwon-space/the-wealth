"use client";

import { useState } from "react";
import Link from "next/link";
import { GitCompare, Plus } from "lucide-react";
import { useQuery, useQueries } from "@tanstack/react-query";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type Period = "1M" | "3M" | "6M" | "1Y" | "ALL";

const PERIODS: Period[] = ["1M", "3M", "6M", "1Y", "ALL"];

// Up to 3 comparison colors: brand blue + 2 complementary
const PORTFOLIO_COLORS = ["#1e90ff", "#00c853", "#ff6d00"] as const;

interface PortfolioItem {
  id: number;
  name: string;
  currency: string;
  total_invested: number;
}

interface HistoryPoint {
  date: string;
  value: number;
}

interface NormalizedPoint {
  date: string;
  [portfolioName: string]: number | string;
}

function normalizeToReturnPct(data: HistoryPoint[]): Array<{ date: string; pct: number }> {
  if (data.length === 0) return [];
  const base = data[0].value;
  if (base <= 0) return [];
  return data.map((d) => ({
    date: d.date,
    pct: ((d.value - base) / base) * 100,
  }));
}

function mergeHistories(
  histories: Array<{ name: string; points: Array<{ date: string; pct: number }> }>
): NormalizedPoint[] {
  // Collect all dates
  const dateSet = new Set<string>();
  for (const h of histories) {
    for (const p of h.points) dateSet.add(p.date);
  }
  const allDates = Array.from(dateSet).sort();

  return allDates.map((date) => {
    const point: NormalizedPoint = { date };
    for (const h of histories) {
      const found = h.points.find((p) => p.date === date);
      if (found !== undefined) {
        point[h.name] = Math.round(found.pct * 100) / 100;
      }
    }
    return point;
  });
}

interface TooltipEntry {
  name: string;
  value: number;
  color: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipEntry[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-popover px-3 py-2.5 text-xs shadow-md space-y-1.5 min-w-[140px]">
      <p className="text-muted-foreground font-medium">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center justify-between gap-3">
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: entry.color }}
            />
            <span className="text-muted-foreground truncate max-w-[80px]">{entry.name}</span>
          </span>
          <span
            className="font-semibold tabular-nums"
            style={{ color: entry.value >= 0 ? "var(--rise)" : "var(--fall)" }}
          >
            {entry.value >= 0 ? "+" : ""}
            {entry.value.toFixed(2)}%
          </span>
        </div>
      ))}
    </div>
  );
}

export default function ComparePage() {
  const [period, setPeriod] = useState<Period>("3M");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const { data: portfolios = [], isLoading: portfoliosLoading } = useQuery<PortfolioItem[]>({
    queryKey: ["portfolios"],
    queryFn: () => api.get<PortfolioItem[]>("/portfolios").then((r) => r.data),
    staleTime: 60_000,
  });

  // Fetch history for each selected portfolio using useQueries (hooks-safe)
  const historyQueries = useQueries({
    queries: selectedIds.map((id) => ({
      queryKey: ["portfolio-history", id, period] as const,
      queryFn: () =>
        api
          .get<HistoryPoint[]>("/analytics/portfolio-history", {
            params: { period, portfolio_id: id },
          })
          .then((r) => r.data),
      staleTime: 3_600_000,
    })),
  });

  const handleToggle = (id: number) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 3) return prev; // max 3
      return [...prev, id];
    });
  };

  const allLoaded = historyQueries.every((q) => !q.isLoading);

  const chartData: NormalizedPoint[] = (() => {
    if (!allLoaded || selectedIds.length === 0) return [];
    const histories = selectedIds.map((id, idx) => {
      const portfolio = portfolios.find((p) => p.id === id);
      const points = normalizeToReturnPct(historyQueries[idx]?.data ?? []);
      return { name: portfolio?.name ?? `포트폴리오 ${id}`, points };
    });
    return mergeHistories(histories);
  })();

  if (portfoliosLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-32" />
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
        <Skeleton className="h-[320px] w-full rounded-lg" />
      </div>
    );
  }

  if (portfolios.length < 2) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">포트폴리오 비교</h1>
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
          <GitCompare className="mb-3 h-12 w-12 text-muted-foreground/40" />
          <p className="text-lg font-semibold">포트폴리오 비교는 2개 이상의 포트폴리오가 필요합니다</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {portfolios.length === 0
              ? "포트폴리오를 생성하고 종목을 추가하면 비교할 수 있습니다."
              : "포트폴리오가 1개뿐입니다. 비교하려면 포트폴리오를 1개 더 만드세요."}
          </p>
          <Link href="/dashboard/portfolios">
            <button className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">
              <Plus className="h-4 w-4" />
              포트폴리오 만들기
            </button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">포트폴리오 비교</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          최대 3개 포트폴리오를 선택해 수익률을 비교하세요.
        </p>
      </div>

      {/* Portfolio selector */}
      <section className="space-y-2">
        <p className="text-sm font-medium text-muted-foreground">비교할 포트폴리오 선택</p>
        <div className="flex flex-wrap gap-2">
          {portfolios.map((p, idx) => {
            const selIdx = selectedIds.indexOf(p.id);
            const isSelected = selIdx !== -1;
            const color = isSelected ? PORTFOLIO_COLORS[selIdx] : undefined;
            const isDisabled = !isSelected && selectedIds.length >= 3;
            return (
              <button
                key={p.id}
                onClick={() => !isDisabled && handleToggle(p.id)}
                disabled={isDisabled}
                className={`min-h-[44px] rounded-lg border px-4 py-2 text-sm font-medium transition-all ${
                  isSelected
                    ? "text-white shadow-sm"
                    : isDisabled
                    ? "cursor-not-allowed opacity-40 bg-muted text-muted-foreground"
                    : "hover:bg-accent bg-background text-foreground"
                }`}
                style={isSelected ? { background: color, borderColor: color } : undefined}
              >
                {p.name}
              </button>
            );
          })}
        </div>
        {selectedIds.length >= 3 && (
          <p className="text-xs text-muted-foreground">최대 3개까지 선택할 수 있습니다.</p>
        )}
      </section>

      {/* Period selector — always visible */}
      <div className="flex gap-1">
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            aria-pressed={period === p}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              period === p
                ? "text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
            style={period === p ? { background: "var(--accent-indigo)" } : undefined}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Chart */}
      {selectedIds.length === 0 ? (
        <Card>
          <CardContent className="flex h-[320px] items-center justify-center text-sm text-muted-foreground p-6">
            <div className="text-center space-y-3">
              <GitCompare className="mx-auto h-10 w-10 text-muted-foreground/30 mb-2" />
              <p>비교할 포트폴리오를 추가하세요</p>
              <p className="text-xs text-muted-foreground">
                위 목록에서 포트폴리오를 선택하면 수익률 비교 차트가 표시됩니다.
              </p>
              {portfolios.length > 0 && (
                <button
                  onClick={() => handleToggle(portfolios[0].id)}
                  className="mt-2 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                  aria-label="포트폴리오 추가"
                >
                  <Plus className="h-4 w-4" />
                  포트폴리오 추가
                </button>
              )}
            </div>
          </CardContent>
        </Card>
      ) : !allLoaded ? (
        <Skeleton className="h-[320px] w-full rounded-lg" />
      ) : chartData.length === 0 ? (
        <Card>
          <CardContent className="flex h-[320px] items-center justify-center text-sm text-muted-foreground p-6">
            <p>선택한 기간에 가격 스냅샷 데이터가 없습니다.</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-4">
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="currentColor"
                  strokeOpacity={0.08}
                />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10 }}
                  tickFormatter={(v: string) => v.slice(5)}
                  tickLine={false}
                  axisLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fontSize: 10 }}
                  tickFormatter={(v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`}
                  tickLine={false}
                  axisLine={false}
                  width={56}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                  iconType="circle"
                  iconSize={8}
                />
                {selectedIds.map((id, idx) => {
                  const portfolio = portfolios.find((p) => p.id === id);
                  const name = portfolio?.name ?? `포트폴리오 ${id}`;
                  return (
                    <Line
                      key={id}
                      type="monotone"
                      dataKey={name}
                      stroke={PORTFOLIO_COLORS[idx]}
                      strokeWidth={2.5}
                      dot={false}
                      activeDot={{ r: 4, strokeWidth: 0 }}
                      connectNulls
                    />
                  );
                })}
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Summary table */}
      {selectedIds.length > 0 && chartData.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-muted-foreground">기간 수익률 요약</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {selectedIds.map((id, idx) => {
              const portfolio = portfolios.find((p) => p.id === id);
              const name = portfolio?.name ?? `포트폴리오 ${id}`;
              const points = historyQueries[idx]?.data ?? [];
              const normalized = normalizeToReturnPct(points);
              const lastPct = normalized.length > 0 ? normalized[normalized.length - 1].pct : null;
              return (
                <Card key={id}>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-full"
                        style={{ background: PORTFOLIO_COLORS[idx] }}
                      />
                      <p className="text-sm font-medium truncate">{name}</p>
                    </div>
                    {lastPct != null ? (
                      <p
                        className="text-xl font-bold tabular-nums"
                        style={{ color: lastPct >= 0 ? "var(--rise)" : "var(--fall)" }}
                      >
                        {lastPct >= 0 ? "+" : ""}
                        {lastPct.toFixed(2)}%
                      </p>
                    ) : (
                      <p className="text-muted-foreground text-sm">데이터 없음</p>
                    )}
                    <p className="text-xs text-muted-foreground mt-0.5">기간 내 누적 수익률</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
