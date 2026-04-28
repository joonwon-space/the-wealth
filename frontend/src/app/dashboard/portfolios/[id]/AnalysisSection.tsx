"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { AreaChart } from "@/components/charts/area-chart";
import { formatKRW } from "@/lib/format";

interface PortfolioHistoryPoint {
  date: string;
  value: number;
}

interface BenchmarkDelta {
  index_code: string;
  period: string;
  mine_pct: number;
  benchmark_pct: number;
  delta_pct_points: number;
}

interface FxGainLossItem {
  ticker: string;
  name: string | null;
  market: string | null;
  stock_pnl_usd: number;
  fx_pnl_krw: number;
  total_pnl_krw: number;
}

interface AnalysisSectionProps {
  portfolioId: number;
}

const PERIOD_LABEL = "1개월";
const PERIOD = "1M";

export function AnalysisSection({ portfolioId }: AnalysisSectionProps) {
  const { data: history } = useQuery<PortfolioHistoryPoint[]>({
    queryKey: ["analytics", "portfolio-history", PERIOD, portfolioId],
    queryFn: async () =>
      (
        await api.get<PortfolioHistoryPoint[]>("/analytics/portfolio-history", {
          params: { period: PERIOD, portfolio_id: portfolioId },
        })
      ).data,
    staleTime: 5 * 60_000,
    enabled: portfolioId > 0,
  });

  const { data: bench } = useQuery<BenchmarkDelta>({
    queryKey: ["analytics", "benchmark-delta", PERIOD],
    queryFn: async () =>
      (
        await api.get<BenchmarkDelta>("/analytics/benchmark-delta", {
          params: { period: PERIOD },
        })
      ).data,
    staleTime: 5 * 60_000,
  });

  const { data: fxItems } = useQuery<FxGainLossItem[]>({
    queryKey: ["analytics", "fx-gain-loss"],
    queryFn: async () =>
      (await api.get<FxGainLossItem[]>("/analytics/fx-gain-loss")).data,
    staleTime: 10 * 60_000,
  });

  const sparkData = Array.isArray(history) && history.length > 0
    ? history.map((p) => ({ v: Number(p.value) }))
    : [];

  const isUp = (bench?.mine_pct ?? 0) >= 0;

  return (
    <section className="space-y-3" aria-label="분석">
      <h2 className="text-sm font-semibold text-foreground">분석 · {PERIOD_LABEL}</h2>

      {/* Portfolio history sparkline */}
      <Card>
        <CardContent className="p-4">
          <div className="text-xs text-muted-foreground mb-2">평가금액 추이</div>
          <AreaChart data={sparkData} height={140} showDot up={isUp} />
        </CardContent>
      </Card>

      {/* Benchmark delta */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="text-xs text-muted-foreground">vs {bench?.index_code ?? "KOSPI200"}</div>
            <div
              className={
                "text-sm font-bold " +
                ((bench?.delta_pct_points ?? 0) >= 0 ? "text-rise" : "text-fall")
              }
            >
              {bench
                ? `${bench.delta_pct_points >= 0 ? "+" : ""}${bench.delta_pct_points.toFixed(2)}%p`
                : "—"}
            </div>
          </div>
          <div className="mt-1 grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-md bg-muted/40 p-2">
              <div className="text-muted-foreground">내 수익률</div>
              <div className={"font-semibold " + ((bench?.mine_pct ?? 0) >= 0 ? "text-rise" : "text-fall")}>
                {bench ? `${bench.mine_pct >= 0 ? "+" : ""}${bench.mine_pct.toFixed(2)}%` : "—"}
              </div>
            </div>
            <div className="rounded-md bg-muted/40 p-2">
              <div className="text-muted-foreground">벤치마크</div>
              <div className={"font-semibold " + ((bench?.benchmark_pct ?? 0) >= 0 ? "text-rise" : "text-fall")}>
                {bench ? `${bench.benchmark_pct >= 0 ? "+" : ""}${bench.benchmark_pct.toFixed(2)}%` : "—"}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* FX gain/loss — user-wide (해외주식) */}
      {Array.isArray(fxItems) && fxItems.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground mb-2">환차손익 (해외주식)</div>
            <div className="space-y-1.5">
              {fxItems.slice(0, 5).map((it) => (
                <div key={it.ticker} className="flex items-center justify-between text-xs">
                  <span className="font-medium">{it.name ?? it.ticker}</span>
                  <span
                    className={
                      "font-semibold " +
                      (it.fx_pnl_krw >= 0 ? "text-rise" : "text-fall")
                    }
                  >
                    {it.fx_pnl_krw >= 0 ? "+" : ""}
                    {formatKRW(it.fx_pnl_krw)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </section>
  );
}
