"use client";

import { useEffect, useState } from "react";
import { BarChart3, Search } from "lucide-react";
import { api } from "@/lib/api";
import { formatKRW, formatRate } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PnLBadge } from "@/components/PnLBadge";
import { AllocationDonut } from "@/components/AllocationDonut";
import { CandlestickChart } from "@/components/CandlestickChart";
import { StockSearchDialog } from "@/components/StockSearchDialog";

const DONUT_COLORS = ["#e31f26", "#1a56db", "#f59e0b", "#10b981", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];
const PERIODS = ["1M", "3M", "6M", "1Y", "3Y"] as const;

interface HoldingRow {
  ticker: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number | null;
  market_value: number | null;
  pnl_amount: number | null;
  pnl_rate: number | null;
  day_change_rate: number | null;
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
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);

  // Chart state
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [selectedName, setSelectedName] = useState<string>("");
  const [selectedAvgPrice, setSelectedAvgPrice] = useState<number | undefined>();
  const [period, setPeriod] = useState<(typeof PERIODS)[number]>("3M");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [chartLoading, setChartLoading] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    api.get<Summary>("/dashboard/summary")
      .then(({ data }) => setSummary(data))
      .finally(() => setLoading(false));
  }, []);

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
    // Find avg_price from holdings
    const holding = summary?.holdings.find((h) => h.ticker === ticker);
    setSelectedAvgPrice(holding ? Number(holding.avg_price) : undefined);
    fetchChart(ticker, period);
  };

  const handlePeriodChange = (p: (typeof PERIODS)[number]) => {
    setPeriod(p);
    if (selectedTicker) fetchChart(selectedTicker, p);
  };

  if (loading) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-8 w-24" />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}><CardContent className="p-4 space-y-2"><Skeleton className="h-3 w-16" /><Skeleton className="h-6 w-24" /></CardContent></Card>
          ))}
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
          <p className="mt-1 text-sm text-muted-foreground">포트폴리오에 종목을 추가하면 분석을 시작합니다.</p>
        </div>
      </div>
    );
  }

  const s = summary;
  const sortedByPnl = [...s.holdings]
    .filter((h) => h.pnl_rate != null)
    .sort((a, b) => Number(b.pnl_rate) - Number(a.pnl_rate));

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">분석</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">총 자산</p><p className="mt-1 text-lg font-bold tabular-nums">{formatKRW(s.total_asset)}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">투자 원금</p><p className="mt-1 text-lg font-bold tabular-nums">{formatKRW(s.total_invested)}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">총 손익</p><p className="mt-1 text-lg font-bold"><PnLBadge value={s.total_pnl_amount} /></p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">수익률</p><p className="mt-1 text-lg font-bold"><PnLBadge value={s.total_pnl_rate} suffix="%" /></p></CardContent></Card>
      </div>

      {/* Stock Chart */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">
            {selectedTicker ? `${selectedName} (${selectedTicker})` : "종목 차트"}
          </h2>
          <Button size="sm" variant="outline" onClick={() => setSearchOpen(true)} className="gap-1">
            <Search className="h-3.5 w-3.5" />
            종목 선택
          </Button>
        </div>

        {/* Period selector */}
        {selectedTicker && (
          <div className="flex gap-1">
            {PERIODS.map((p) => (
              <button
                key={p}
                onClick={() => handlePeriodChange(p)}
                className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                  period === p ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        )}

        {/* Quick select from holdings */}
        {!selectedTicker && s.holdings.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {s.holdings.map((h, i) => (
              <button
                key={`${h.ticker}-${i}`}
                onClick={() => handleSelectStock(h.ticker, h.name)}
                className="rounded-lg border px-3 py-1.5 text-xs hover:bg-accent transition-colors"
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
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
            <AllocationDonut data={s.allocation} totalAsset={s.total_asset} />
            <div className="flex flex-wrap gap-2">
              {s.allocation.map((item, i) => (
                <div key={`${item.ticker}-${i}`} className="flex items-center gap-1.5 text-xs">
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: DONUT_COLORS[i % DONUT_COLORS.length] }} />
                  <span>{item.name}</span>
                  <span className="text-muted-foreground">{formatRate(item.ratio)}%</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Performance table */}
      {sortedByPnl.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-base font-semibold">종목별 성과</h2>

          {/* Mobile card view */}
          <div className="space-y-3 md:hidden">
            {sortedByPnl.map((h, i) => (
              <div
                key={`${h.ticker}-${i}`}
                className="cursor-pointer rounded-lg border p-3 space-y-2 active:bg-accent/50"
                onClick={() => handleSelectStock(h.ticker, h.name)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-sm">{h.name}</div>
                    <div className="text-xs text-muted-foreground">{h.ticker}</div>
                  </div>
                  <PnLBadge value={h.pnl_rate ?? 0} suffix="%" />
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">수량</span>
                    <span className="tabular-nums">{Number(h.quantity).toLocaleString("ko-KR")}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">현재가</span>
                    <span className="tabular-nums">{h.current_price ? formatKRW(h.current_price) : "—"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">평균단가</span>
                    <span className="tabular-nums">{formatKRW(h.avg_price)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">수익금</span>
                    <PnLBadge value={h.pnl_amount ?? 0} />
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Desktop table view */}
          <div className="hidden md:block overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  {["종목", "수량", "평균단가", "현재가", "손익", "수익률", "전일 대비"].map((h) => (
                    <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedByPnl.map((h, i) => (
                  <tr
                    key={`${h.ticker}-${i}`}
                    className="border-t cursor-pointer hover:bg-accent/50"
                    onClick={() => handleSelectStock(h.ticker, h.name)}
                  >
                    <td className="px-4 py-2">
                      <div className="font-medium">{h.name}</div>
                      <div className="text-xs text-muted-foreground">{h.ticker}</div>
                    </td>
                    <td className="px-4 py-2 tabular-nums">{Number(h.quantity).toLocaleString("ko-KR")}</td>
                    <td className="px-4 py-2 tabular-nums">{formatKRW(h.avg_price)}</td>
                    <td className="px-4 py-2 tabular-nums">{h.current_price ? formatKRW(h.current_price) : "—"}</td>
                    <td className="px-4 py-2"><PnLBadge value={h.pnl_amount ?? 0} /></td>
                    <td className="px-4 py-2"><PnLBadge value={h.pnl_rate ?? 0} suffix="%" /></td>
                    <td className="px-4 py-2">
                      {h.day_change_rate != null
                        ? <PnLBadge value={h.day_change_rate} suffix="%" />
                        : <span className="text-muted-foreground">—</span>}
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
        onSelect={(ticker, name) => { handleSelectStock(ticker, name); setSearchOpen(false); }}
      />
    </div>
  );
}
