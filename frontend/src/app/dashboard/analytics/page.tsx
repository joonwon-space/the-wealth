"use client";

import { useState } from "react";
import { BarChart3 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { AllocationDonut } from "@/components/DynamicCharts";
import { StockSearchDialog } from "@/components/StockSearchDialog";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { SummaryCards } from "./SummaryCards";
import { MetricsSection } from "./MetricsSection";
import { MonthlyReturnsSection } from "./MonthlyReturnsSection";
import { SectorFxSection } from "./SectorFxSection";
import { HistorySection } from "./HistorySection";
import { StockChartSection } from "./StockChartSection";
import { PerformanceTable } from "./PerformanceTable";

interface HoldingRow {
  ticker: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number | null;
  market_value: number | null;
  market_value_krw: number | null;
  pnl_amount: number | null;
  pnl_rate: number | null;
  day_change_rate: number | null;
  currency?: "KRW" | "USD";
  portfolio_name?: string | null;
}

interface AllocationItem {
  ticker: string;
  name: string;
  value: number;
  ratio: number;
}

interface Summary {
  total_asset: number;
  total_invested: number;
  total_pnl_amount: number;
  total_pnl_rate: number;
  holdings: HoldingRow[];
  allocation: AllocationItem[];
}

interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

type ChartPeriod = "1M" | "3M" | "6M" | "1Y" | "3Y";
type HistoryPeriod = "1W" | "1M" | "3M" | "6M" | "1Y" | "ALL";

export default function AnalyticsPage() {
  const [historyPeriod, setHistoryPeriod] = useState<HistoryPeriod>("3M");
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [selectedName, setSelectedName] = useState<string>("");
  const [selectedAvgPrice, setSelectedAvgPrice] = useState<number | undefined>();
  const [period, setPeriod] = useState<ChartPeriod>("3M");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  // Shares the cached response with dashboard/page.tsx
  const { data: summary, isLoading: summaryLoading } = useQuery<Summary>({
    queryKey: ["dashboard", "summary"],
    queryFn: () => api.get<Summary>("/dashboard/summary").then((r) => r.data),
    staleTime: 60_000,
  });

  const fetchChart = async (ticker: string, p: string) => {
    setChartLoading(true);
    setChartError(false);
    try {
      const { data } = await api.get<{ candles: Candle[] }>("/chart/daily", {
        params: { ticker, period: p },
      });
      setCandles(data.candles);
    } catch {
      setChartError(true);
    } finally {
      setChartLoading(false);
    }
  };

  const handleSelectStock = (ticker: string, name: string) => {
    setSelectedTicker(ticker);
    setSelectedName(name);
    const holding = summary?.holdings.find((h) => h.ticker === ticker);
    setSelectedAvgPrice(holding ? Number(holding.avg_price) : undefined);
    fetchChart(ticker, period);
  };

  const handlePeriodChange = (p: ChartPeriod) => {
    setPeriod(p);
    if (selectedTicker) fetchChart(selectedTicker, p);
  };

  if (summaryLoading) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-8 w-24" />
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardContent className="p-4 space-y-2">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-6 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="space-y-2">
          <Skeleton className="h-5 w-20" />
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i}>
                <CardContent className="p-4 space-y-2">
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-6 w-20" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
        <div className="space-y-2">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-[280px] w-full rounded-lg" />
        </div>
        <div className="space-y-2">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-24 w-full rounded-lg" />
        </div>
        <div className="space-y-2">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-[240px] w-full rounded-lg" />
        </div>
      </div>
    );
  }

  if (!summary || (summary.holdings.length === 0 && Number(summary.total_invested) === 0)) {
    return (
      <div className="space-y-8">
        <h1 className="text-2xl font-bold">분석</h1>
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
          <BarChart3 className="mb-3 h-12 w-12 text-muted-foreground/40" />
          <p className="text-lg font-semibold">데이터가 없습니다</p>
          <p className="mt-1 text-sm text-muted-foreground">
            포트폴리오에 종목을 추가하면 분석을 시작합니다.
          </p>
        </div>
      </div>
    );
  }

  const s = summary;
  const sortedByMarketValue = [...s.holdings].sort(
    (a, b) =>
      Number(b.market_value_krw ?? b.market_value ?? 0) -
      Number(a.market_value_krw ?? a.market_value ?? 0),
  );

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">분석</h1>

      <SummaryCards
        totalAsset={s.total_asset}
        totalInvested={s.total_invested}
        totalPnlAmount={s.total_pnl_amount}
        totalPnlRate={s.total_pnl_rate}
      />

      <ErrorBoundary>
        <MetricsSection />
      </ErrorBoundary>

      <ErrorBoundary>
        <HistorySection period={historyPeriod} onPeriodChange={setHistoryPeriod} />
      </ErrorBoundary>

      <ErrorBoundary>
        <MonthlyReturnsSection />
      </ErrorBoundary>

      <ErrorBoundary>
        <SectorFxSection />
      </ErrorBoundary>

      <StockChartSection
        selectedTicker={selectedTicker}
        selectedName={selectedName}
        selectedAvgPrice={selectedAvgPrice}
        period={period}
        candles={candles}
        chartLoading={chartLoading}
        chartError={chartError}
        holdings={s.holdings}
        onPeriodChange={handlePeriodChange}
        onSearchOpen={() => setSearchOpen(true)}
        onSelectStock={handleSelectStock}
        onRetryChart={() => selectedTicker && void fetchChart(selectedTicker, period)}
      />

      {s.allocation.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-base font-semibold">자산 배분</h2>
          <AllocationDonut data={s.allocation} totalAsset={s.total_asset} />
        </section>
      )}

      <PerformanceTable
        holdings={sortedByMarketValue}
        onSelectStock={handleSelectStock}
      />

      <StockSearchDialog
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelect={(ticker, name) => {
          handleSelectStock(ticker, name);
          setSearchOpen(false);
        }}
      />
    </div>
  );
}
