"use client";

import { useEffect, useRef, useState } from "react";
import { BarChart3, Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import { formatKRW, formatRate, formatPrice } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PnLBadge } from "@/components/PnLBadge";
import {
  AllocationDonut,
  CandlestickChart,
  PortfolioHistoryChart,
  SectorAllocationChart,
} from "@/components/DynamicCharts";
import { StockSearchDialog } from "@/components/StockSearchDialog";
import { MonthlyHeatmap } from "@/components/MonthlyHeatmap";

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

interface Metrics {
  total_return_rate: number | null;
  cagr: number | null;
  mdd: number | null;
  sharpe_ratio: number | null;
}

interface MonthlyReturnItem {
  year: number;
  month: number;
  return_rate: number;
}

interface HistoryPoint {
  date: string;
  value: number;
}

interface SectorAllocationItem {
  sector: string;
  value: number;
  weight: number;
}

interface KrwAssetPoint {
  date: string;
  value: number;
  domestic_value: number;
  overseas_value_krw: number;
}

interface FxGainLossItem {
  ticker: string;
  name: string;
  quantity: number;
  avg_price_usd: number;
  current_price_usd: number;
  stock_pnl_usd: number;
  fx_rate_at_buy: number;
  fx_rate_current: number;
  fx_gain_krw: number;
  stock_gain_krw: number;
  total_pnl_krw: number;
}

export default function AnalyticsPage() {
  const [historyPeriod, setHistoryPeriod] = useState<"1W" | "1M" | "3M" | "6M" | "1Y" | "ALL">("3M");

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

  const { data: metrics } = useQuery<Metrics>({
    queryKey: ["analytics", "metrics"],
    queryFn: () => api.get<Metrics>("/analytics/metrics").then((r) => r.data),
    staleTime: 3_600_000,
  });

  const { data: monthlyReturns = [] } = useQuery<MonthlyReturnItem[]>({
    queryKey: ["analytics", "monthly-returns"],
    queryFn: () => api.get<MonthlyReturnItem[]>("/analytics/monthly-returns").then((r) => r.data),
    staleTime: 3_600_000,
  });

  const { data: portfolioHistory = [] } = useQuery<HistoryPoint[]>({
    queryKey: ["analytics", "portfolio-history", historyPeriod],
    queryFn: () =>
      api
        .get<HistoryPoint[]>("/analytics/portfolio-history", { params: { period: historyPeriod } })
        .then((r) => r.data),
    staleTime: 3_600_000,
  });

  const { data: sectorAllocation = [] } = useQuery<SectorAllocationItem[]>({
    queryKey: ["analytics", "sector-allocation"],
    queryFn: () =>
      api.get<SectorAllocationItem[]>("/analytics/sector-allocation").then((r) => r.data),
    staleTime: 3_600_000,
  });

  const { data: fxGainLoss = [] } = useQuery<FxGainLossItem[]>({
    queryKey: ["analytics", "fx-gain-loss"],
    queryFn: () =>
      api.get<FxGainLossItem[]>("/analytics/fx-gain-loss").then((r) => r.data),
    staleTime: 3_600_000,
  });

  const { data: krwAssetHistory = [] } = useQuery<KrwAssetPoint[]>({
    queryKey: ["analytics", "krw-asset-history", historyPeriod],
    queryFn: () =>
      api
        .get<KrwAssetPoint[]>("/analytics/krw-asset-history", { params: { period: historyPeriod } })
        .then((r) => r.data),
    staleTime: 3_600_000,
  });

  const loading = summaryLoading;

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
        {/* Summary cards */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}><CardContent className="p-4 space-y-2"><Skeleton className="h-3 w-16" /><Skeleton className="h-6 w-24" /></CardContent></Card>
          ))}
        </div>
        {/* Metrics cards */}
        <div className="space-y-2">
          <Skeleton className="h-5 w-20" />
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i}><CardContent className="p-4 space-y-2"><Skeleton className="h-3 w-16" /><Skeleton className="h-6 w-20" /></CardContent></Card>
            ))}
          </div>
        </div>
        {/* History chart */}
        <div className="space-y-2">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-[280px] w-full rounded-lg" />
        </div>
        {/* Heatmap */}
        <div className="space-y-2">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-24 w-full rounded-lg" />
        </div>
        {/* Sector chart */}
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
          <p className="mt-1 text-sm text-muted-foreground">포트폴리오에 종목을 추가하면 분석을 시작합니다.</p>
        </div>
      </div>
    );
  }

  const s = summary;
  const sortedByMarketValue = [...s.holdings]
    .sort((a, b) => Number(b.market_value_krw ?? b.market_value ?? 0) - Number(a.market_value_krw ?? a.market_value ?? 0));

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">분석</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">총 자산</p><p className="mt-1 text-lg font-bold tabular-nums">{formatKRW(s.total_asset)}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">투자 원금</p><p className="mt-1 text-lg font-bold tabular-nums">{formatKRW(s.total_invested)}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">총 손익</p><p className="mt-1 text-lg font-bold"><PnLBadge value={s.total_pnl_amount} /></p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">수익률</p><p className="mt-1 text-lg font-bold"><PnLBadge value={s.total_pnl_rate} suffix="%" /></p></CardContent></Card>
      </div>

      {/* 성과 지표 */}
      {metrics && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">성과 지표</h2>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <MetricCard label="총 수익률" value={metrics.total_return_rate} suffix="%" tooltip="전체 투자 기간 동안의 누적 수익률" />
            <MetricCard label="CAGR" value={metrics.cagr} suffix="%" tooltip="연평균 복리 수익률(CAGR): 투자 원금이 현재 가치가 되기까지 매년 몇 %씩 성장했는지 나타냅니다. 데이터가 30일 미만이면 표시되지 않습니다." nullHint="데이터 30일 이상 필요" />
            <MetricCard label="MDD" value={metrics.mdd != null ? -metrics.mdd : null} suffix="%" tooltip="최대 낙폭(MDD): 고점 대비 최대 하락폭입니다. 값이 클수록 손실 위험이 큽니다." nullHint="이력 데이터 부족" />
            <MetricCard label="샤프 비율" value={metrics.sharpe_ratio} tooltip="샤프 비율: 위험(변동성) 한 단위당 초과 수익률. 1 이상이면 양호, 2 이상이면 우수합니다." nullHint="데이터 30일 이상 필요" />
          </div>
        </section>
      )}

      {/* 포트폴리오 가치 추이 */}
      <section className="space-y-2">
        <h2 className="text-base font-semibold">포트폴리오 가치 추이</h2>
        <PortfolioHistoryChart
          data={portfolioHistory}
          period={historyPeriod}
          onPeriodChange={setHistoryPeriod}
        />
      </section>

      {/* 원화 환산 총 자산 추이 */}
      {krwAssetHistory.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">원화 환산 총 자산 추이</h2>
          <p className="text-xs text-muted-foreground">해외주식은 해당 날짜 환율로 원화 환산. 기간 탭은 위 차트와 연동됩니다.</p>
          <Card>
            <CardContent className="p-4">
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={krwAssetHistory} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
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
      )}

      {/* 월별 수익률 히트맵 */}
      <section className="space-y-2">
        <h2 className="text-base font-semibold">월별 수익률</h2>
        <MonthlyHeatmap data={monthlyReturns} />
      </section>

      {/* 섹터 배분 */}
      {sectorAllocation.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-base font-semibold">섹터 배분</h2>
          <Card>
            <CardContent className="p-4">
              <SectorAllocationChart data={sectorAllocation} />
            </CardContent>
          </Card>
        </section>
      )}

      {/* 해외주식 환차익/환차손 */}
      {fxGainLoss.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-base font-semibold">해외주식 환차익/환차손</h2>
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50">
                    <tr>
                      {(["종목", "수량", "매입가(USD)", "현재가(USD)", "주가 수익(KRW)", "환차익(KRW)", "총 손익(KRW)"] as const).map((h) => (
                        <th key={h} className="whitespace-nowrap px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {fxGainLoss.map((item, i) => (
                      <tr key={`${item.ticker}-${i}`} className="border-t">
                        <td className="px-4 py-2">
                          <div className="font-medium">{item.name}</div>
                          <div className="text-xs text-muted-foreground">{item.ticker}</div>
                        </td>
                        <td className="px-4 py-2 tabular-nums">{item.quantity.toLocaleString("ko-KR")}</td>
                        <td className="px-4 py-2 tabular-nums">${item.avg_price_usd.toFixed(2)}</td>
                        <td className="px-4 py-2 tabular-nums">${item.current_price_usd.toFixed(2)}</td>
                        <td className="px-4 py-2"><PnLBadge value={item.stock_gain_krw} /></td>
                        <td className="px-4 py-2"><PnLBadge value={item.fx_gain_krw} /></td>
                        <td className="px-4 py-2"><PnLBadge value={item.total_pnl_krw} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="border-t px-4 py-2 text-xs text-muted-foreground">
                매입 시 환율: 보유 등록일 기준 / 현재 환율: {fxGainLoss[0]?.fx_rate_current.toLocaleString("ko-KR")}원/USD
              </div>
            </CardContent>
          </Card>
        </section>
      )}

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
                className={`min-h-[44px] min-w-[44px] rounded px-3 py-1 text-xs font-medium transition-colors ${
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
                    <span className="tabular-nums">{h.current_price ? formatPrice(h.current_price, h.currency ?? "KRW") : "—"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">평균단가</span>
                    <span className="tabular-nums">{formatPrice(h.avg_price, h.currency ?? "KRW")}</span>
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
                  {(["종목", "수량", "평균단가", "현재가", "평가금액(₩)", "손익(₩)", "수익률"] as const).map((h) => (
                    <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
                  ))}
                  <th className="hidden lg:table-cell px-4 py-2 text-left font-medium text-muted-foreground">전일 대비</th>
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
                      <div className="text-xs text-muted-foreground">{h.ticker}</div>
                    </td>
                    <td className="px-4 py-2 tabular-nums">{Number(h.quantity).toLocaleString("ko-KR")}</td>
                    <td className="px-4 py-2 tabular-nums">{formatPrice(h.avg_price, h.currency ?? "KRW")}</td>
                    <td className="px-4 py-2 tabular-nums">{h.current_price ? formatPrice(h.current_price, h.currency ?? "KRW") : "—"}</td>
                    <td className="px-4 py-2 tabular-nums">{formatKRW(h.market_value_krw)}</td>
                    <td className="px-4 py-2"><PnLBadge value={h.pnl_amount ?? 0} /></td>
                    <td className="px-4 py-2"><PnLBadge value={h.pnl_rate ?? 0} suffix="%" /></td>
                    <td className="hidden lg:table-cell px-4 py-2">
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

interface MetricCardProps {
  label: string;
  value: number | null;
  suffix?: string;
  tooltip?: string;
  /** Short hint shown below "—" when value is null */
  nullHint?: string;
}

function MetricTooltip({ text }: { text: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [tooltipStyle, setTooltipStyle] = useState<React.CSSProperties | null>(null);

  const show = () => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    setTooltipStyle({
      position: "fixed",
      top: rect.top - 8,
      left: rect.left + rect.width / 2,
      transform: "translate(-50%, -100%)",
      zIndex: 9999,
    });
  };

  return (
    <>
      <span
        ref={ref}
        className="cursor-help text-xs text-muted-foreground/60 hover:text-muted-foreground"
        onMouseEnter={show}
        onMouseLeave={() => setTooltipStyle(null)}
      >
        ⓘ
      </span>
      {tooltipStyle && (
        <div
          className="w-52 rounded-md border bg-popover px-2.5 py-2 text-xs text-popover-foreground shadow-lg"
          style={tooltipStyle}
        >
          {text}
        </div>
      )}
    </>
  );
}

function MetricCard({ label, value, suffix = "", tooltip, nullHint }: MetricCardProps) {
  const display = value != null ? `${value > 0 && suffix === "%" ? "+" : ""}${value.toFixed(suffix === "%" ? 2 : 3)}${suffix}` : "—";
  const color = value == null ? "" : value > 0 ? "text-rise" : value < 0 ? "text-fall" : "";
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-1">
          <p className="text-xs text-muted-foreground">{label}</p>
          {tooltip && <MetricTooltip text={tooltip} />}
        </div>
        <p className={`mt-1 text-lg font-bold tabular-nums ${color}`}>{display}</p>
        {value == null && nullHint && (
          <p className="mt-0.5 text-[10px] text-muted-foreground/70">{nullHint}</p>
        )}
      </CardContent>
    </Card>
  );
}
