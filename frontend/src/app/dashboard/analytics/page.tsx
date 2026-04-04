"use client";

import { useState } from "react";
import { BarChart3, Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatKRW, formatRate, formatPrice } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PnLBadge } from "@/components/PnLBadge";
import { AllocationDonut, CandlestickChart } from "@/components/DynamicCharts";
import { StockSearchDialog } from "@/components/StockSearchDialog";
import { MetricsSection } from "./MetricsSection";
import { MonthlyReturnsSection } from "./MonthlyReturnsSection";
import { SectorFxSection } from "./SectorFxSection";
import { HistorySection } from "./HistorySection";

const PERIODS = ["1M", "3M", "6M", "1Y", "3Y"] as const;

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

export default function AnalyticsPage() {
  const [historyPeriod, setHistoryPeriod] = useState<
    "1W" | "1M" | "3M" | "6M" | "1Y" | "ALL"
  >("3M");

  // Chart state
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [selectedName, setSelectedName] = useState<string>("");
  const [selectedAvgPrice, setSelectedAvgPrice] = useState<number | undefined>();
  const [period, setPeriod] = useState<(typeof PERIODS)[number]>("3M");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [chartLoading, setChartLoading] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  // Use the same query key as dashboard/page.tsx so TanStack Query serves
  // the cached response instead of making a duplicate network request.
  const { data: summary, isLoading: summaryLoading } = useQuery<Summary>({
    queryKey: ["dashboard", "summary"],
    queryFn: () => api.get<Summary>("/dashboard/summary").then((r) => r.data),
    staleTime: 60_000,
  });

  const fetchChart = async (ticker: string, p: string) => {
    setChartLoading(true);
    try {
      const { data } = await api.get<{ candles: Candle[] }>("/chart/daily", {
        params: { ticker, period: p },
      });
      setCandles(data.candles);
    } catch {
      setCandles([]);
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

  const handlePeriodChange = (p: (typeof PERIODS)[number]) => {
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

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">총 자산</p>
            <p className="mt-1 text-lg font-bold tabular-nums">{formatKRW(s.total_asset)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">투자 원금</p>
            <p className="mt-1 text-lg font-bold tabular-nums">{formatKRW(s.total_invested)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">총 손익</p>
            <p className="mt-1 text-lg font-bold">
              <PnLBadge value={s.total_pnl_amount} />
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">수익률</p>
            <p className="mt-1 text-lg font-bold">
              <PnLBadge value={s.total_pnl_rate} suffix="%" />
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 성과 지표 */}
      <MetricsSection />

      {/* 포트폴리오 가치 추이 + 원화 환산 총 자산 추이 */}
      <HistorySection period={historyPeriod} onPeriodChange={setHistoryPeriod} />

      {/* 월별 수익률 */}
      <MonthlyReturnsSection />

      {/* 섹터 배분 + 환차익/환차손 */}
      <SectorFxSection />

      {/* Stock Chart */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">
            {selectedTicker ? `${selectedName} (${selectedTicker})` : "종목 차트"}
          </h2>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setSearchOpen(true)}
            className="gap-1"
          >
            <Search className="h-3.5 w-3.5" />
            종목 선택
          </Button>
        </div>

        {selectedTicker && (
          <div className="flex gap-1">
            {PERIODS.map((p) => (
              <button
                key={p}
                onClick={() => handlePeriodChange(p)}
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
        )}

        {!selectedTicker && s.holdings.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {s.holdings.map((h, i) => (
              <button
                key={`${h.ticker}-${i}`}
                onClick={() => handleSelectStock(h.ticker, h.name)}
                className="min-h-[44px] rounded-lg border px-3 py-1.5 text-xs hover:bg-accent transition-colors"
              >
                {h.name}
              </button>
            ))}
          </div>
        )}

        {chartLoading ? (
          <Skeleton className="h-[400px] w-full" />
        ) : selectedTicker ? (
          <CandlestickChart candles={candles} avgPrice={selectedAvgPrice} />
        ) : (
          <div className="flex h-[300px] items-center justify-center rounded-xl border border-dashed text-sm text-muted-foreground">
            보유 종목을 선택하거나 검색하세요
          </div>
        )}
      </section>

      {/* Allocation chart */}
      {s.allocation.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-base font-semibold">자산 배분</h2>
          <AllocationDonut data={s.allocation} totalAsset={s.total_asset} />
        </section>
      )}

      {/* Performance table */}
      {sortedByMarketValue.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-base font-semibold">종목별 성과</h2>

          {/* Mobile card view */}
          <div className="space-y-3 md:hidden">
            {sortedByMarketValue.map((h, i) => (
              <button
                key={`${h.ticker}-${i}`}
                className="w-full text-left rounded-lg border p-3 space-y-2 active:bg-accent/50 hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                onClick={() => handleSelectStock(h.ticker, h.name)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-sm">{h.name}</div>
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <span>{h.ticker}</span>
                      {h.portfolio_name && (
                        <span className="rounded bg-muted px-1 text-[10px] font-medium">
                          {h.portfolio_name}
                        </span>
                      )}
                    </div>
                  </div>
                  <PnLBadge value={h.pnl_rate ?? 0} suffix="%" />
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">수량</span>
                    <span className="tabular-nums">
                      {Number(h.quantity).toLocaleString("ko-KR")}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">현재가</span>
                    <span className="tabular-nums">
                      {h.current_price
                        ? formatPrice(h.current_price, h.currency ?? "KRW")
                        : "—"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">평균단가</span>
                    <span className="tabular-nums">
                      {formatPrice(h.avg_price, h.currency ?? "KRW")}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">평가금액(₩)</span>
                    <span className="tabular-nums">{formatKRW(h.market_value_krw)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">수익금(₩)</span>
                    <PnLBadge value={h.pnl_amount ?? 0} />
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Desktop table view */}
          <div className="hidden md:block overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  {(
                    [
                      "종목",
                      "수량",
                      "평균단가",
                      "현재가",
                      "평가금액(₩)",
                      "손익(₩)",
                      "수익률",
                    ] as const
                  ).map((h) => (
                    <th
                      key={h}
                      className="px-4 py-2 text-left font-medium text-muted-foreground"
                    >
                      {h}
                    </th>
                  ))}
                  <th className="hidden lg:table-cell px-4 py-2 text-left font-medium text-muted-foreground">
                    전일 대비
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedByMarketValue.map((h, i) => (
                  <tr
                    key={`${h.ticker}-${i}`}
                    className="border-t cursor-pointer hover:bg-accent/50 focus-visible:outline-none focus-visible:bg-accent/50"
                    tabIndex={0}
                    onClick={() => handleSelectStock(h.ticker, h.name)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        handleSelectStock(h.ticker, h.name);
                      }
                    }}
                  >
                    <td className="px-4 py-2">
                      <div className="font-medium">{h.name}</div>
                      <div className="text-xs text-muted-foreground flex items-center gap-1">
                        <span>{h.ticker}</span>
                        {h.portfolio_name && (
                          <span className="rounded bg-muted px-1 text-[10px] font-medium">
                            {h.portfolio_name}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-2 tabular-nums">
                      {Number(h.quantity).toLocaleString("ko-KR")}
                    </td>
                    <td className="px-4 py-2 tabular-nums">
                      {formatPrice(h.avg_price, h.currency ?? "KRW")}
                    </td>
                    <td className="px-4 py-2 tabular-nums">
                      {h.current_price
                        ? formatPrice(h.current_price, h.currency ?? "KRW")
                        : "—"}
                    </td>
                    <td className="px-4 py-2 tabular-nums">{formatKRW(h.market_value_krw)}</td>
                    <td className="px-4 py-2">
                      <PnLBadge value={h.pnl_amount ?? 0} />
                    </td>
                    <td className="px-4 py-2">
                      <PnLBadge value={h.pnl_rate ?? 0} suffix="%" />
                    </td>
                    <td className="hidden lg:table-cell px-4 py-2">
                      {h.day_change_rate != null ? (
                        <PnLBadge value={h.day_change_rate} suffix="%" />
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

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
