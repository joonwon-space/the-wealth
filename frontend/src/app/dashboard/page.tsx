"use client";

import { useCallback, useEffect, useRef } from "react";
import Link from "next/link";
import {
  BarChart3,
  Plus,
  RefreshCw,
  Wifi,
  WifiOff,
  Loader2,
  TriangleAlert,
  TrendingUp,
  Banknote,
  Wallet,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AreaChart, Area, ResponsiveContainer, Tooltip } from "recharts";
import { api } from "@/lib/api";
import { usePriceStream } from "@/hooks/usePriceStream";
import { useCountUp } from "@/hooks/useCountUp";
import { useAuthStore } from "@/store/auth";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CardSkeleton, LargeCardSkeleton } from "@/components/CardSkeleton";
import { ChartSkeleton, DonutSkeleton } from "@/components/ChartSkeleton";
import { AllocationDonut } from "@/components/DynamicCharts";
import { DayChangeBadge } from "@/components/DayChangeBadge";
import { HoldingsTable } from "@/components/HoldingsTable";
import { PnLBadge } from "@/components/PnLBadge";
import { formatKRW } from "@/lib/format";
import { WatchlistSection } from "@/components/WatchlistSection";
import { TopHoldingsWidget } from "@/components/TopHoldingsWidget";
import { PageError } from "@/components/PageError";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { toast } from "sonner";

const REFRESH_INTERVAL_MS = 30_000;
const DASHBOARD_QUERY_KEY = ["dashboard", "summary"] as const;

interface HoldingRow {
  id: number;
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
  w52_high: number | null;
  w52_low: number | null;
  currency: "KRW" | "USD";
  portfolio_name: string | null;
}

interface AllocationItem {
  ticker: string;
  name: string;
  value: number;
  ratio: number;
}

interface TriggeredAlert {
  id: number;
  ticker: string;
  name: string;
  condition: "above" | "below";
  threshold: number;
  current_price: number;
}

interface Summary {
  total_asset: number;
  total_invested: number;
  total_pnl_amount: number;
  total_pnl_rate: number;
  total_day_change_rate: number | null;
  day_change_pct: number | null;
  day_change_amount: number | null;
  holdings: HoldingRow[];
  allocation: AllocationItem[];
  triggered_alerts: TriggeredAlert[];
  usd_krw_rate: number | null;
  kis_status: "ok" | "degraded";
  total_cash: number | null;
  total_assets: number | null;
}

// Fake 7-day sparkline data derived from total_asset for display
function generateSparklineData(total: number): { v: number }[] {
  const points = 7;
  const data: { v: number }[] = [];
  let base = total * 0.97;
  const delta = total * 0.01;
  for (let i = 0; i < points; i++) {
    base = base + (Math.random() - 0.4) * delta;
    data.push({ v: Math.max(0, base) });
  }
  data.push({ v: total });
  return data;
}

async function fetchSummary(refresh = false): Promise<Summary> {
  const { data } = await api.get<Summary>("/dashboard/summary", {
    params: refresh ? { refresh: true } : undefined,
  });
  return data;
}

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);
  const refreshAccessToken = useAuthStore((s) => s.refreshAccessToken);

  // On page load after refresh, accessToken is null (not persisted).
  // Silently call /auth/refresh so the SSE hook gets a token.
  useEffect(() => {
    if (!accessToken) {
      void refreshAccessToken();
    }
  }, [accessToken, refreshAccessToken]);

  // streamStatus is hoisted here so the query can react to SSE state.
  // The actual usePriceStream call is below after handleStreamPrices is defined;
  // we track it via a ref updated in an effect to avoid circular dependency.
  const streamActiveRef = useRef(false);

  const {
    data: summary,
    isLoading,
    isError,
    error,
    isFetching,
    dataUpdatedAt,
    refetch,
  } = useQuery<Summary>({
    queryKey: DASHBOARD_QUERY_KEY,
    queryFn: () => fetchSummary(),
    // Disable polling when SSE is active — SSE already provides live prices,
    // so polling /dashboard/summary would be redundant. Re-enable on disconnect.
    refetchInterval: streamActiveRef.current ? false : REFRESH_INTERVAL_MS,
  });

  // Show toast for triggered alerts when data refreshes
  const shownAlertIds = useRef<Set<number>>(new Set());
  useEffect(() => {
    if (!summary) return;
    for (const alert of summary.triggered_alerts ?? []) {
      if (shownAlertIds.current.has(alert.id)) continue;
      shownAlertIds.current.add(alert.id);
      const label = alert.name || alert.ticker;
      const dir = alert.condition === "above" ? "이상" : "이하";
      toast.warning(`목표가 도달 — ${label}`, {
        description: `현재 ${formatKRW(alert.current_price)} — 목표 ${dir} ${formatKRW(alert.threshold)}`,
        duration: 8000,
      });
    }
  }, [summary]);

  // SSE 실시간 가격 업데이트 — queryClient.setQueryData로 캐시 직접 패치
  const handleStreamPrices = useCallback(
    (prices: Record<string, string>) => {
      queryClient.setQueryData<Summary>(DASHBOARD_QUERY_KEY, (prev) => {
        if (!prev) return prev;
        const usdKrwRate = Number(prev.usd_krw_rate) || 1450;
        const updatedHoldings = prev.holdings.map((h) => {
          const newPrice = prices[h.ticker];
          if (!newPrice) return h;
          const current_price = Number(newPrice);
          if (h.currency === "USD") {
            const qty = Number(h.quantity);
            const avg = Number(h.avg_price);
            const market_value = qty * current_price;
            const market_value_krw = market_value * usdKrwRate;
            const invested_krw = qty * avg * usdKrwRate;
            const pnl_amount = market_value_krw - invested_krw;
            const pnl_rate = invested_krw ? (pnl_amount / invested_krw) * 100 : null;
            return { ...h, current_price, market_value, market_value_krw, pnl_amount, pnl_rate };
          }
          const qty = Number(h.quantity);
          const avg = Number(h.avg_price);
          const market_value = qty * current_price;
          const invested = qty * avg;
          const pnl_amount = market_value - invested;
          const pnl_rate = invested ? (pnl_amount / invested) * 100 : null;
          return { ...h, current_price, market_value, market_value_krw: market_value, pnl_amount, pnl_rate };
        });
        const total_asset = updatedHoldings.reduce(
          (sum, h) => sum + (Number(h.market_value_krw) || Number(h.quantity) * Number(h.avg_price)),
          0
        );
        const total_pnl_amount = total_asset - prev.total_invested;
        const total_pnl_rate = prev.total_invested ? (total_pnl_amount / prev.total_invested) * 100 : 0;
        return { ...prev, holdings: updatedHoldings, total_asset, total_pnl_amount, total_pnl_rate };
      });
    },
    [queryClient]
  );

  const { status: streamStatus, reconnect: reconnectStream } = usePriceStream({
    onPrices: handleStreamPrices,
    enabled: !isLoading,
  });

  // Keep ref in sync with SSE connection status so refetchInterval reacts.
  useEffect(() => {
    streamActiveRef.current = streamStatus === "connected";
  }, [streamStatus]);

  const handleManualRefresh = async () => {
    const result = await api.get<Summary>("/dashboard/summary", { params: { refresh: true } });
    queryClient.setQueryData(DASHBOARD_QUERY_KEY, result.data);
  };

  const lastUpdated = dataUpdatedAt ? new Date(dataUpdatedAt) : null;

  // Count-up animation for total asset (runs on first data load)
  const animatedTotalAsset = useCountUp({
    target: summary?.total_asset ?? 0,
    duration: 1200,
  });
  const animatedTotalInvested = useCountUp({
    target: summary?.total_invested ?? 0,
    duration: 1200,
    delay: 100,
  });
  const animatedTotalPnl = useCountUp({
    target: summary?.total_pnl_amount ?? 0,
    duration: 1200,
    delay: 200,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-32" />
        <LargeCardSkeleton />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <CardSkeleton />
          <CardSkeleton showAccentBar />
        </div>
        <div className="space-y-3">
          <Skeleton className="h-3 w-20" />
          <DonutSkeleton />
        </div>
        <div className="space-y-2">
          <Skeleton className="h-3 w-20" />
          <ChartSkeleton height={200} />
        </div>
      </div>
    );
  }

  if (isError && !summary) {
    const message = error instanceof Error ? error.message : "서버에 연결할 수 없습니다";
    return (
      <div className="space-y-8">
        <h1 className="text-2xl font-bold">대시보드</h1>
        <PageError message={message} onRetry={() => refetch()} />
      </div>
    );
  }

  const s: Summary = summary ?? {
    total_asset: 0,
    total_invested: 0,
    total_pnl_amount: 0,
    total_pnl_rate: 0,
    total_day_change_rate: null,
    day_change_pct: null,
    day_change_amount: null,
    holdings: [],
    allocation: [],
    triggered_alerts: [],
    usd_krw_rate: null,
    kis_status: "ok",
    total_cash: null,
    total_assets: null,
  };

  const hasNoPortfolio = !isLoading && s.holdings.length === 0 && s.total_invested === 0;
  const dayChangePct = s.day_change_pct ?? s.total_day_change_rate;
  const sparklineData = generateSparklineData(s.total_asset);
  const isPositiveDayChange = (dayChangePct ?? 0) >= 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">대시보드</h1>
        <div className="flex items-center gap-2">
          <StreamStatusBadge status={streamStatus} onReconnect={reconnectStream} />
          {lastUpdated && (
            <span className="text-xs text-muted-foreground">
              {isFetching ? "업데이트 중..." : lastUpdated.toLocaleTimeString("ko-KR")}
            </span>
          )}
          <button
            onClick={handleManualRefresh}
            disabled={isFetching}
            className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded text-muted-foreground hover:bg-muted disabled:opacity-50"
            title="새로고침"
            aria-label="새로고침"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* KIS API 일시 오류 배너 */}
      {s.kis_status === "degraded" && (
        <div className="flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <span className="font-medium">KIS API 일시 오류</span>
            <span className="ml-1 text-amber-700 dark:text-amber-400">
              — 가격 정보가 최신이 아닐 수 있습니다. 30초마다 자동으로 재시도합니다.
            </span>
          </div>
        </div>
      )}

      {/* 포트폴리오/종목이 없을 때 빈 상태 */}
      {hasNoPortfolio ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
          <BarChart3 className="mb-3 h-12 w-12 text-muted-foreground/40" />
          <p className="text-lg font-semibold">아직 보유 종목이 없습니다</p>
          <p className="mt-1 text-sm text-muted-foreground">포트폴리오를 만들고 종목을 추가해보세요.</p>
          <Link
            href="/dashboard/portfolios"
            className="mt-5 flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            <Plus className="h-4 w-4" />
            포트폴리오 만들기
          </Link>
        </div>
      ) : (
        <>
          {/* 총 자산 Large 카드 */}
          <Card className="relative overflow-hidden border border-white/10 backdrop-blur-sm bg-card/80 animate-in fade-in slide-in-from-bottom-2 duration-500" style={{ animationDelay: "0ms", animationFillMode: "both" }}>
            <div className="absolute inset-0 bg-gradient-to-br from-[var(--accent-indigo)]/10 via-transparent to-[var(--accent-amber)]/5 pointer-events-none" />
            <CardContent className="relative p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="text-section-header mb-2">총 자산 (평가금액)</p>
                  <p className="text-asset-total" style={{ color: "var(--accent-indigo)" }}>
                    {formatKRW(animatedTotalAsset)}
                  </p>
                  <div className="mt-2 flex items-center gap-2 flex-wrap">
                    {dayChangePct != null && (
                      <span className={`flex items-center gap-0.5 text-sm font-medium ${isPositiveDayChange ? "text-rise" : "text-fall"}`}>
                        {isPositiveDayChange ? (
                          <ArrowUpRight className="h-4 w-4" />
                        ) : (
                          <ArrowDownRight className="h-4 w-4" />
                        )}
                        <DayChangeBadge pct={dayChangePct} />
                      </span>
                    )}
                    {s.day_change_amount != null && (
                      <PnLBadge value={s.day_change_amount} />
                    )}
                    <span className="text-metric-label">전일 대비</span>
                  </div>
                  {s.usd_krw_rate != null && (
                    <p className="mt-1 text-metric-label text-numeric">
                      USD/KRW {formatKRW(s.usd_krw_rate)}
                    </p>
                  )}
                </div>
                {/* 7일 미니 sparkline */}
                <div className="w-20 h-16 shrink-0 ml-3 sm:w-32 sm:ml-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={sparklineData} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
                      <defs>
                        <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--accent-indigo)" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="var(--accent-indigo)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <Tooltip content={() => null} />
                      <Area
                        type="monotone"
                        dataKey="v"
                        stroke="var(--accent-indigo)"
                        strokeWidth={2}
                        fill="url(#sparkGrad)"
                        dot={false}
                        activeDot={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 하단 3 카드 그리드 */}
          <div className={`grid grid-cols-1 gap-4 animate-in fade-in slide-in-from-bottom-2 duration-500 ${s.total_cash != null ? "sm:grid-cols-3" : "sm:grid-cols-2"}`} style={{ animationDelay: "100ms", animationFillMode: "both" }}>
            {/* 투자 원금 카드 */}
            <MetricCard
              label="투자 원금"
              value={formatKRW(animatedTotalInvested)}
              icon={<Wallet className="h-4 w-4" />}
              accentColor="var(--chart-6)"
            />

            {/* 예수금 카드 (KIS 연결 시에만) */}
            {s.total_cash != null && (
              <MetricCard
                label="예수금 합계"
                value={formatKRW(s.total_cash)}
                icon={<Banknote className="h-4 w-4" />}
                accentColor="var(--chart-2)"
              />
            )}

            {/* 총 손익 카드 */}
            <Card className="relative overflow-hidden backdrop-blur-sm bg-card/80 border border-white/10">
              <div
                className="absolute top-0 left-0 right-0 h-0.5"
                style={{
                  background:
                    s.total_pnl_amount >= 0 ? "var(--rise)" : "var(--fall)",
                }}
              />
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-metric-label">총 손익</p>
                  <span
                    className="flex items-center justify-center h-7 w-7 rounded-full"
                    style={{
                      background:
                        s.total_pnl_amount >= 0
                          ? "color-mix(in oklch, var(--rise) 15%, transparent)"
                          : "color-mix(in oklch, var(--fall) 15%, transparent)",
                      color: s.total_pnl_amount >= 0 ? "var(--rise)" : "var(--fall)",
                    }}
                  >
                    <TrendingUp className="h-4 w-4" />
                  </span>
                </div>
                <p className="text-xl font-bold">
                  <PnLBadge value={animatedTotalPnl} />
                </p>
                <p className="text-xs mt-0.5">
                  <PnLBadge value={s.total_pnl_rate} suffix="%" />
                </p>
              </CardContent>
            </Card>
          </div>

          {/* 수익 상위 3종목 위젯 */}
          {s.holdings.length > 0 && (
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-500" style={{ animationDelay: "200ms", animationFillMode: "both" }}>
              <TopHoldingsWidget holdings={s.holdings} />
            </div>
          )}

          {/* 자산 배분 도넛 차트 */}
          {s.allocation.length > 0 && (
            <ErrorBoundary fallback={(err, reset) => (
              <WidgetErrorFallback title="자산 배분" error={err} reset={reset} />
            )}>
              <section className="space-y-3 animate-in fade-in slide-in-from-bottom-2 duration-500" style={{ animationDelay: "300ms", animationFillMode: "both" }}>
                <h2 className="text-section-header">자산 배분</h2>
                <AllocationDonut data={s.allocation} totalAsset={s.total_asset} />
              </section>
            </ErrorBoundary>
          )}

          {/* 관심 종목 */}
          <ErrorBoundary fallback={(err, reset) => (
            <WidgetErrorFallback title="관심 종목" error={err} reset={reset} />
          )}>
            <WatchlistSection />
          </ErrorBoundary>

          {/* 보유 종목 테이블 */}
          <ErrorBoundary fallback={(err, reset) => (
            <WidgetErrorFallback title="보유 종목" error={err} reset={reset} />
          )}>
            <section className="space-y-2">
              <div className="flex items-center justify-between">
                <h2 className="text-section-header">보유 종목</h2>
                {s.holdings.length === 0 && (
                  <Link
                    href="/dashboard/portfolios"
                    className="flex items-center gap-1 text-sm text-primary hover:underline"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    종목 추가하기
                  </Link>
                )}
              </div>
              <HoldingsTable holdings={s.holdings} />
            </section>
          </ErrorBoundary>
        </>
      )}
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  accentColor: string;
}

function MetricCard({ label, value, icon, accentColor }: MetricCardProps) {
  return (
    <Card className="relative overflow-hidden backdrop-blur-sm bg-card/80 border border-white/10">
      <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: accentColor }} />
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <p className="text-metric-label">{label}</p>
          <span
            className="flex items-center justify-center h-7 w-7 rounded-full"
            style={{
              background: `color-mix(in oklch, ${accentColor} 15%, transparent)`,
              color: accentColor,
            }}
          >
            {icon}
          </span>
        </div>
        <p className="text-xl font-bold tabular-nums">{value}</p>
      </CardContent>
    </Card>
  );
}

interface WidgetErrorFallbackProps {
  title: string;
  error: Error;
  reset: () => void;
}

interface StreamStatusBadgeProps {
  status: "connecting" | "connected" | "disconnected";
  onReconnect: () => void;
}

function StreamStatusBadge({ status, onReconnect }: StreamStatusBadgeProps) {
  if (status === "connected") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
        <Wifi className="h-3 w-3" />
        실시간
      </span>
    );
  }
  if (status === "connecting") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
        <Loader2 className="h-3 w-3 animate-spin" />
        연결 중
      </span>
    );
  }
  return (
    <button
      onClick={onReconnect}
      className="inline-flex min-h-[44px] items-center gap-1 rounded-full bg-muted px-3 text-xs font-medium text-muted-foreground hover:bg-muted/80"
      title="SSE 재연결"
      aria-label="SSE 재연결"
    >
      <WifiOff className="h-3 w-3" />
      연결 끊김 — 재연결
    </button>
  );
}

function WidgetErrorFallback({ title, error, reset }: WidgetErrorFallbackProps) {
  return (
    <section className="space-y-2">
      <h2 className="text-section-header">{title}</h2>
      <div
        role="alert"
        className="flex items-center justify-between rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3"
      >
        <p className="text-sm text-destructive">
          {title} 위젯을 불러오는 중 오류가 발생했습니다.
          {process.env.NODE_ENV !== "production" && (
            <span className="ml-1 text-muted-foreground">{error.message}</span>
          )}
        </p>
        <button
          onClick={reset}
          className="ml-4 shrink-0 rounded px-2 py-1 text-xs font-medium text-destructive hover:bg-destructive/10"
        >
          다시 시도
        </button>
      </div>
    </section>
  );
}
