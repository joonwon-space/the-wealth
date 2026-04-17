"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CandlestickChart } from "@/components/DynamicCharts";
import { api } from "@/lib/api";

const CHART_PERIODS = ["1M", "3M", "6M", "1Y", "3Y"] as const;
type ChartPeriod = (typeof CHART_PERIODS)[number];

const SMA_PERIODS = [20, 60, 120] as const;
type SmaPeriod = (typeof SMA_PERIODS)[number] | 0;

interface HoldingRow {
  ticker: string;
  name: string;
}

interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface SmaPoint {
  date: string;
  sma: number;
}

interface StockChartSectionProps {
  selectedTicker: string | null;
  selectedName: string;
  selectedAvgPrice: number | undefined;
  period: ChartPeriod;
  candles: Candle[];
  chartLoading: boolean;
  chartError?: boolean;
  holdings: HoldingRow[];
  onPeriodChange: (p: ChartPeriod) => void;
  onSearchOpen: () => void;
  onSelectStock: (ticker: string, name: string) => void;
  onRetryChart?: () => void;
}

export function StockChartSection({
  selectedTicker,
  selectedName,
  selectedAvgPrice,
  period,
  candles,
  chartLoading,
  chartError = false,
  holdings,
  onPeriodChange,
  onSearchOpen,
  onSelectStock,
  onRetryChart,
}: StockChartSectionProps) {
  const [smaPeriod, setSmaPeriod] = useState<SmaPeriod>(0);

  const { data: smaData = [] } = useQuery<SmaPoint[]>({
    queryKey: ["analytics", "sma", selectedTicker, smaPeriod],
    queryFn: () =>
      api
        .get<SmaPoint[]>(`/analytics/stocks/${selectedTicker}/sma`, {
          params: { period: smaPeriod },
        })
        .then((r) => r.data),
    enabled: smaPeriod !== 0 && selectedTicker !== null,
    staleTime: 3_600_000,
  });

  // Convert SmaPoint[] to {time, value}[] for lightweight-charts LineSeries
  const smaLineData = smaData.map((p) => ({ time: p.date, value: p.sma }));

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">
          {selectedTicker ? `${selectedName} (${selectedTicker})` : "종목 차트"}
        </h2>
        <Button
          size="sm"
          variant="outline"
          onClick={onSearchOpen}
          className="gap-1"
        >
          <Search className="h-3.5 w-3.5" />
          종목 선택
        </Button>
      </div>

      {selectedTicker && (
        <div className="flex flex-wrap items-center gap-2">
          {/* Chart period selector */}
          <div className="flex gap-1">
            {CHART_PERIODS.map((p) => (
              <button
                key={p}
                onClick={() => onPeriodChange(p)}
                className={`min-h-[44px] min-w-[44px] rounded px-3 py-1 text-xs font-medium transition-colors ${
                  period === p
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {p}
              </button>
            ))}
          </div>

          {/* SMA period selector */}
          <div className="flex gap-1 ml-auto">
            <span className="text-xs text-muted-foreground self-center">이동평균:</span>
            <button
              onClick={() => setSmaPeriod(0)}
              className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                smaPeriod === 0
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              OFF
            </button>
            {SMA_PERIODS.map((sp) => (
              <button
                key={sp}
                onClick={() => setSmaPeriod(sp)}
                className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                  smaPeriod === sp
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {sp}일
              </button>
            ))}
          </div>
        </div>
      )}

      {!selectedTicker && holdings.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {holdings.map((h, i) => (
            <button
              key={`${h.ticker}-${i}`}
              onClick={() => onSelectStock(h.ticker, h.name)}
              className="min-h-[44px] rounded-lg border px-3 py-1.5 text-xs hover:bg-accent transition-colors"
            >
              {h.name}
            </button>
          ))}
        </div>
      )}

      {chartLoading ? (
        <Skeleton className="h-[400px] w-full" />
      ) : chartError ? (
        <div className="flex h-[400px] items-center justify-center gap-2 rounded-xl border border-dashed text-sm text-destructive">
          <span>차트 데이터를 불러오지 못했습니다.</span>
          {onRetryChart && (
            <button
              onClick={onRetryChart}
              className="underline hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
            >
              다시 시도
            </button>
          )}
        </div>
      ) : selectedTicker ? (
        <CandlestickChart
          candles={candles}
          avgPrice={selectedAvgPrice}
          smaData={smaPeriod !== 0 ? smaLineData : undefined}
          smaPeriod={smaPeriod !== 0 ? smaPeriod : undefined}
        />
      ) : (
        <div className="flex h-[300px] items-center justify-center rounded-xl border border-dashed text-sm text-muted-foreground">
          보유 종목을 선택하거나 검색하세요
        </div>
      )}
    </section>
  );
}
