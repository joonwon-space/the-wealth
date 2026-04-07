"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import { formatKRW } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PortfolioHistoryChart } from "@/components/DynamicCharts";
import { WidgetErrorFallback } from "@/components/WidgetErrorFallback";

interface HistoryPoint {
  date: string;
  value: number;
}

interface KrwAssetPoint {
  date: string;
  value: number;
  domestic_value: number;
  overseas_value_krw: number;
}

interface BenchmarkPoint {
  date: string;
  close_price: number;
}

type BenchmarkMode = "OFF" | "KOSPI200" | "SP500";

interface HistorySectionProps {
  period: "1W" | "1M" | "3M" | "6M" | "1Y" | "ALL";
  onPeriodChange: (p: "1W" | "1M" | "3M" | "6M" | "1Y" | "ALL") => void;
}

/** 두 시계열을 날짜 기준으로 병합한다. 기준점 대비 % 변화율로 정규화. */
function mergeWithBenchmark(
  history: HistoryPoint[],
  benchmark: BenchmarkPoint[],
): Array<{ date: string; portfolio_pct: number; benchmark_pct: number | null }> {
  if (history.length === 0) return [];

  const firstPortfolio = history[0].value;
  const benchmarkMap = new Map(benchmark.map((b) => [b.date, b.close_price]));
  const firstBenchmark = benchmarkMap.get(history[0].date) ?? benchmark[0]?.close_price;

  return history.map((h) => {
    const portfolioPct =
      firstPortfolio > 0 ? ((h.value - firstPortfolio) / firstPortfolio) * 100 : 0;
    const bPrice = benchmarkMap.get(h.date);
    const benchmarkPct =
      bPrice != null && firstBenchmark != null && firstBenchmark > 0
        ? ((bPrice - firstBenchmark) / firstBenchmark) * 100
        : null;
    return { date: h.date, portfolio_pct: portfolioPct, benchmark_pct: benchmarkPct };
  });
}

export function HistorySection({ period, onPeriodChange }: HistorySectionProps) {
  const [benchmarkMode, setBenchmarkMode] = useState<BenchmarkMode>("OFF");

  const {
    data: portfolioHistory = [],
    isLoading: historyLoading,
    isError: historyError,
    refetch: refetchHistory,
  } = useQuery<HistoryPoint[]>({
    queryKey: ["analytics", "portfolio-history", period],
    queryFn: () =>
      api
        .get<HistoryPoint[]>("/analytics/portfolio-history", { params: { period } })
        .then((r) => r.data),
    staleTime: 3_600_000,
  });

  const {
    data: krwAssetHistory = [],
    isLoading: krwLoading,
    isError: krwError,
    refetch: refetchKrw,
  } = useQuery<KrwAssetPoint[]>({
    queryKey: ["analytics", "krw-asset-history", period],
    queryFn: () =>
      api
        .get<KrwAssetPoint[]>("/analytics/krw-asset-history", { params: { period } })
        .then((r) => r.data),
    staleTime: 3_600_000,
  });

  const {
    data: benchmarkData = [],
    isLoading: benchmarkLoading,
  } = useQuery<BenchmarkPoint[]>({
    queryKey: ["analytics", "benchmark", benchmarkMode],
    queryFn: () =>
      benchmarkMode === "OFF"
        ? Promise.resolve([])
        : api
            .get<BenchmarkPoint[]>("/analytics/benchmark", {
              params: { index_code: benchmarkMode },
            })
            .then((r) => r.data),
    enabled: benchmarkMode !== "OFF",
    staleTime: 3_600_000,
  });

  const showBenchmarkOverlay = benchmarkMode !== "OFF" && portfolioHistory.length > 0;
  const mergedData = showBenchmarkOverlay
    ? mergeWithBenchmark(portfolioHistory, benchmarkData)
    : [];

  const BENCHMARK_MODES: BenchmarkMode[] = ["OFF", "KOSPI200", "SP500"];
  const benchmarkLabel: Record<BenchmarkMode, string> = {
    OFF: "벤치마크 OFF",
    KOSPI200: "KOSPI200",
    SP500: "S&P500",
  };

  return (
    <>
      {/* 포트폴리오 가치 추이 */}
      <section className="space-y-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-base font-semibold">포트폴리오 가치 추이</h2>
          {/* Benchmark toggle */}
          <div className="flex gap-1">
            {BENCHMARK_MODES.map((mode) => (
              <button
                key={mode}
                onClick={() => setBenchmarkMode(mode)}
                className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                  benchmarkMode === mode
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {benchmarkLabel[mode]}
              </button>
            ))}
          </div>
        </div>

        {historyLoading || (benchmarkMode !== "OFF" && benchmarkLoading) ? (
          <Skeleton className="h-48 rounded-lg" />
        ) : historyError ? (
          <WidgetErrorFallback
            message="포트폴리오 히스토리를 불러오지 못했습니다."
            onRetry={() => refetchHistory()}
          />
        ) : showBenchmarkOverlay ? (
          <Card>
            <CardContent className="p-4 space-y-2">
              <p className="text-xs text-muted-foreground">
                기준점 대비 수익률(%) 비교 — 포트폴리오 vs{" "}
                {benchmarkLabel[benchmarkMode]}
              </p>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={mergedData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                    tickFormatter={(d: string) => d.slice(5)}
                    minTickGap={40}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                    tickFormatter={(v: number) => `${v.toFixed(1)}%`}
                    width={52}
                  />
                  <RechartsTooltip
                    formatter={(value: unknown, name: unknown) => [
                      `${Number(value).toFixed(2)}%`,
                      name === "portfolio_pct"
                        ? "내 포트폴리오"
                        : benchmarkLabel[benchmarkMode],
                    ]}
                    labelFormatter={(label: unknown) => String(label)}
                    contentStyle={{
                      background: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "6px",
                      fontSize: "12px",
                    }}
                  />
                  <Legend
                    formatter={(value: string) =>
                      value === "portfolio_pct"
                        ? "내 포트폴리오"
                        : benchmarkLabel[benchmarkMode]
                    }
                    wrapperStyle={{ fontSize: "11px" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="portfolio_pct"
                    stroke="#1e90ff"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="benchmark_pct"
                    stroke="#f59e0b"
                    strokeWidth={1.5}
                    strokeDasharray="5 3"
                    dot={false}
                    activeDot={{ r: 3 }}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        ) : (
          <PortfolioHistoryChart
            data={portfolioHistory}
            period={period}
            onPeriodChange={onPeriodChange}
          />
        )}
      </section>

      {/* 원화 환산 총 자산 추이 */}
      {krwLoading ? (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">원화 환산 총 자산 추이</h2>
          <Skeleton className="h-48 rounded-lg" />
        </section>
      ) : krwError ? (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">원화 환산 총 자산 추이</h2>
          <WidgetErrorFallback
            message="데이터를 불러오지 못했습니다."
            onRetry={() => refetchKrw()}
          />
        </section>
      ) : krwAssetHistory.length > 0 ? (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">원화 환산 총 자산 추이</h2>
          <p className="text-xs text-muted-foreground">
            해외주식은 해당 날짜 환율로 원화 환산. 기간 탭은 위 차트와 연동됩니다.
          </p>
          <Card>
            <CardContent className="p-4">
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart
                  data={krwAssetHistory}
                  margin={{ top: 4, right: 8, bottom: 0, left: 0 }}
                >
                  <defs>
                    <linearGradient id="colorDomestic" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#1e90ff" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#1e90ff" stopOpacity={0.05} />
                    </linearGradient>
                    <linearGradient id="colorOverseas" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#00c853" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#00c853" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                    tickFormatter={(d: string) => d.slice(5)}
                    minTickGap={40}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                    tickFormatter={(v: number) => `${(v / 1_000_000).toFixed(0)}M`}
                    width={48}
                  />
                  <RechartsTooltip
                    formatter={(value: unknown, name: unknown) => [
                      formatKRW(Number(value)),
                      name === "domestic_value" ? "국내주식" : "해외주식(원화환산)",
                    ]}
                    labelFormatter={(label: unknown) => String(label)}
                    contentStyle={{
                      background: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "6px",
                      fontSize: "12px",
                    }}
                  />
                  <Legend
                    formatter={(value: string) =>
                      value === "domestic_value" ? "국내주식" : "해외주식(원화환산)"
                    }
                    wrapperStyle={{ fontSize: "11px" }}
                  />
                  <Area
                    type="monotone"
                    dataKey="domestic_value"
                    stackId="1"
                    stroke="#1e90ff"
                    fill="url(#colorDomestic)"
                    strokeWidth={1.5}
                  />
                  <Area
                    type="monotone"
                    dataKey="overseas_value_krw"
                    stackId="1"
                    stroke="#00c853"
                    fill="url(#colorOverseas)"
                    strokeWidth={1.5}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </section>
      ) : null}
    </>
  );
}
