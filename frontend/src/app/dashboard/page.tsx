"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  BarChart3,
  Coins,
  Plus,
  RefreshCw,
  Scale,
  Sparkles,
  Target,
  TrendingUp,
  Wallet,
  Wifi,
  WifiOff,
  Loader2,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { usePriceStream } from "@/hooks/usePriceStream";
import { useInvestMode } from "@/hooks/useInvestMode";
import { useAuthStore } from "@/store/auth";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ChartSkeleton, DonutSkeleton } from "@/components/ChartSkeleton";
import { PageError } from "@/components/PageError";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { formatKRW } from "@/lib/format";
import { toast } from "sonner";
import { HeroValue } from "@/components/hero-value";
import { ModeToggle } from "@/components/mode-toggle";
import { TaskCard } from "@/components/task-card";
import { AreaChart } from "@/components/charts/area-chart";
import { Donut } from "@/components/charts/donut";
import { ProgressRing } from "@/components/charts/progress-ring";
import { PortfolioList } from "@/components/dashboard/PortfolioList";

const REFRESH_INTERVAL_MS = 30_000;
const DASHBOARD_QUERY_KEY = ["dashboard", "summary"] as const;

// ---------- types ----------
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
  condition: "above" | "below" | "pct_change" | "drawdown";
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

interface HomeTask {
  id: string;
  kind: "rebalance" | "dividend" | "alert" | "routine" | "goal";
  title: string;
  sub: string | null;
  accent: string | null;
  priority: number;
}

interface TodayTasksResponse {
  count: number;
  tasks: HomeTask[];
}

interface BenchmarkDelta {
  index_code: string;
  period: string;
  mine_pct: number;
  benchmark_pct: number;
  delta_pct_points: number;
}

interface PortfolioHistoryPoint {
  date: string;
  value: number;
}

interface SectorAllocationRow {
  sector: string;
  value: number;
  weight: number;
}

interface UpcomingDividend {
  ticker: string;
  market: string;
  name: string | null;
  quantity: number | string | null;
  ex_date: string | null;
  record_date: string;
  payment_date: string | null;
  amount: number | string;
  currency: string;
  kind: string;
  source: string;
  estimated_payout: number | string | null;
}

async function fetchSummary(refresh = false): Promise<Summary> {
  const { data } = await api.get<Summary>("/dashboard/summary", {
    params: refresh ? { refresh: true } : undefined,
  });
  return data;
}

// ---------- small widgets ----------
interface StreamStatusBadgeProps {
  status: "connecting" | "connected" | "disconnected";
  onReconnect: () => void;
}

function StreamStatusBadge({ status, onReconnect }: StreamStatusBadgeProps) {
  if (status === "connected") {
    return (
      <Badge tone="primary" className="gap-1">
        <Wifi className="size-3" />
        실시간
      </Badge>
    );
  }
  if (status === "connecting") {
    return (
      <Badge tone="warn" className="gap-1">
        <Loader2 className="size-3 animate-spin" />
        연결 중
      </Badge>
    );
  }
  return (
    <button
      onClick={onReconnect}
      className="inline-flex min-h-[32px] items-center gap-1 rounded-full bg-muted px-3 text-xs font-medium text-muted-foreground hover:bg-muted/80"
      title="SSE 재연결"
      aria-label="SSE 재연결"
    >
      <WifiOff className="size-3" />
      연결 끊김 — 재연결
    </button>
  );
}

function WidgetErrorFallback({
  title,
  error,
  reset,
}: {
  title: string;
  error: Error;
  reset: () => void;
}) {
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

// ---------- task icon mapping ----------
const TASK_ICONS: Record<HomeTask["kind"], LucideIcon> = {
  rebalance: Scale,
  dividend: Coins,
  alert: TriangleAlert,
  routine: Sparkles,
  goal: Target,
};

// ---------- page ----------
export default function DashboardPage() {
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);
  const refreshAccessToken = useAuthStore((s) => s.refreshAccessToken);
  const [mode, setMode] = useInvestMode();

  useEffect(() => {
    if (!accessToken) {
      void refreshAccessToken();
    }
  }, [accessToken, refreshAccessToken]);

  const [streamActive, setStreamActive] = useState(false);

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
    refetchInterval: streamActive ? false : REFRESH_INTERVAL_MS,
    staleTime: 60_000,
  });

  // Satellite queries powering the new home sections.
  const { data: todayTasks } = useQuery<TodayTasksResponse>({
    queryKey: ["tasks", "today"],
    queryFn: async () => (await api.get<TodayTasksResponse>("/tasks/today")).data,
    staleTime: 60_000,
    enabled: !isLoading,
  });

  const { data: benchmark } = useQuery<BenchmarkDelta>({
    queryKey: ["analytics", "benchmark-delta", "6M"],
    queryFn: async () =>
      (await api.get<BenchmarkDelta>("/analytics/benchmark-delta", {
        params: { period: "6M" },
      })).data,
    staleTime: 5 * 60_000,
    enabled: !isLoading,
  });

  const { data: sectorAllocation } = useQuery<SectorAllocationRow[]>({
    queryKey: ["analytics", "sector-allocation"],
    queryFn: async () =>
      (await api.get<SectorAllocationRow[]>("/analytics/sector-allocation")).data,
    staleTime: 5 * 60_000,
    enabled: !isLoading,
  });

  const { data: upcomingDividends } = useQuery<UpcomingDividend[]>({
    queryKey: ["dividends", "upcoming"],
    queryFn: async () =>
      (await api.get<UpcomingDividend[]>("/dividends/upcoming")).data,
    staleTime: 10 * 60_000,
    enabled: !isLoading,
  });

  const { data: portfolioHistory } = useQuery<PortfolioHistoryPoint[]>({
    queryKey: ["analytics", "portfolio-history", "1M"],
    queryFn: async () =>
      (await api.get<PortfolioHistoryPoint[]>("/analytics/portfolio-history", {
        params: { period: "1M" },
      })).data,
    staleTime: 5 * 60_000,
    enabled: !isLoading,
  });

  // Alerts toast
  const shownAlertIds = useRef<Set<number>>(new Set());
  useEffect(() => {
    if (!summary) return;
    for (const alert of summary.triggered_alerts ?? []) {
      if (shownAlertIds.current.has(alert.id)) continue;
      shownAlertIds.current.add(alert.id);
      const label = alert.name || alert.ticker;
      const description = (() => {
        switch (alert.condition) {
          case "above":
            return `현재 ${formatKRW(alert.current_price)} — 목표 이상 ${formatKRW(alert.threshold)}`;
          case "below":
            return `현재 ${formatKRW(alert.current_price)} — 목표 이하 ${formatKRW(alert.threshold)}`;
          case "pct_change":
            return `일일 변동 ±${alert.threshold}% 도달 — 현재 ${formatKRW(alert.current_price)}`;
          case "drawdown":
            return `평균단가 대비 -${alert.threshold}% 이상 하락 — 현재 ${formatKRW(alert.current_price)}`;
        }
      })();
      toast.warning(`알림 발화 — ${label}`, {
        description,
        duration: 8000,
      });
    }
  }, [summary]);

  // SSE 실시간 가격 업데이트 — caller는 이미 검증된 기존 로직을 그대로 사용.
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
          0,
        );
        const total_pnl_amount = total_asset - prev.total_invested;
        const total_pnl_rate = prev.total_invested
          ? (total_pnl_amount / prev.total_invested) * 100
          : 0;
        return { ...prev, holdings: updatedHoldings, total_asset, total_pnl_amount, total_pnl_rate };
      });
    },
    [queryClient],
  );

  const { status: streamStatus, reconnect: reconnectStream } = usePriceStream({
    onPrices: handleStreamPrices,
    enabled: !isLoading,
  });

  useEffect(() => {
    setStreamActive(streamStatus === "connected");
  }, [streamStatus]);

  const handleManualRefresh = async () => {
    const result = await api.get<Summary>("/dashboard/summary", {
      params: { refresh: true },
    });
    queryClient.setQueryData(DASHBOARD_QUERY_KEY, result.data);
  };

  const lastUpdated = dataUpdatedAt ? new Date(dataUpdatedAt) : null;

  const animatedTotalAsset = summary?.total_asset ?? 0;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-32" />
        <Card>
          <CardContent className="p-6 space-y-4">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-10 w-60" />
            <ChartSkeleton height={120} />
          </CardContent>
        </Card>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
        <DonutSkeleton />
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
  const dayChangePct = (() => {
    // Pydantic v2 serializes Decimal as string — always coerce to number
    const raw = s.day_change_pct ?? s.total_day_change_rate;
    if (raw != null) {
      const n = Number(raw);
      return Number.isFinite(n) ? n : null;
    }
    // day_change_amount만 있을 때 전일 기준가로 % 역산
    if (s.day_change_amount != null && s.total_asset != null) {
      const prev = Number(s.total_asset) - Number(s.day_change_amount);
      if (prev !== 0) return (Number(s.day_change_amount) / prev) * 100;
    }
    return null;
  })();

  // Number() 변환: Pydantic v2가 Decimal을 문자열로 직렬화하는 경우 NaN 방지.
  const spark = Array.isArray(portfolioHistory) && portfolioHistory.length > 0
    ? portfolioHistory.map((p) => ({ v: Number(p.value) }))
    : [];
  const isPositiveDay = (dayChangePct ?? Number(s.day_change_amount ?? 0)) >= 0;

  const sectorList = Array.isArray(sectorAllocation) ? sectorAllocation : [];
  const sectorSegments = sectorList.slice(0, 8).map((row, i) => ({
    pct: row.weight / 100,
    color: `var(--chart-${(i % 8) + 1})`,
    label: row.sector,
  }));
  const dividendList = Array.isArray(upcomingDividends) ? upcomingDividends : [];
  const todayTasksList =
    todayTasks && Array.isArray(todayTasks.tasks) ? todayTasks : { count: 0, tasks: [] };

  const goalPortfolio = (s as Summary & { target_value?: number }).target_value
    ? { total: s.total_asset, target: (s as Summary & { target_value: number }).target_value }
    : null;

  return (
    <div className="space-y-6">
      {/* ----- Top bar ----- */}
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold tracking-tight">대시보드</h1>
        <ModeToggle
          mode={mode}
          onChange={setMode}
          position="header"
          className="ml-2"
        />
        <div className="ml-auto flex items-center gap-2">
          <StreamStatusBadge status={streamStatus} onReconnect={reconnectStream} />
          {lastUpdated && (
            <span className="text-xs text-muted-foreground">
              {isFetching ? "업데이트 중..." : lastUpdated.toLocaleTimeString("ko-KR")}
            </span>
          )}
          <button
            onClick={handleManualRefresh}
            disabled={isFetching}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded text-muted-foreground hover:bg-muted disabled:opacity-50"
            title="새로고침"
            aria-label="새로고침"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* ----- KIS degraded banner ----- */}
      {s.kis_status === "degraded" && (
        <div
          className="flex items-start gap-2.5 rounded-lg border px-4 py-3 text-sm"
          style={{
            borderColor: "color-mix(in oklch, var(--accent-amber) 40%, transparent)",
            background: "color-mix(in oklch, var(--accent-amber) 12%, transparent)",
            color: "var(--accent-amber)",
          }}
        >
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          <div>
            <span className="font-medium">KIS API 일시 오류</span>
            <span className="ml-1 opacity-80">
              — 가격 정보가 최신이 아닐 수 있습니다. 30초마다 자동으로 재시도합니다.
            </span>
          </div>
        </div>
      )}

      {hasNoPortfolio ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
          <BarChart3 className="mb-3 size-12 text-muted-foreground/40" />
          <p className="text-lg font-semibold">아직 보유 종목이 없습니다</p>
          <p className="mt-1 text-sm text-muted-foreground">
            포트폴리오를 만들고 종목을 추가해보세요.
          </p>
          <Link
            href="/dashboard/portfolios"
            className="mt-5 flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            <Plus className="size-4" />
            포트폴리오 만들기
          </Link>
        </div>
      ) : (
        <>
          {/* ----- Hero: total + today change + chart ----- */}
          <ErrorBoundary
            fallback={(err, reset) => (
              <WidgetErrorFallback title="총 자산" error={err} reset={reset} />
            )}
          >
            <Card>
              <CardContent className="p-6">
                <HeroValue
                  label="총 평가금액 · KRW"
                  value={formatKRW(animatedTotalAsset)}
                  change={s.day_change_amount != null ? formatKRW(s.day_change_amount) : undefined}
                  changePct={dayChangePct}
                  up={isPositiveDay}
                  footnote={
                    s.usd_krw_rate != null ? `USD/KRW ${formatKRW(s.usd_krw_rate)}` : null
                  }
                />
                <div className="mt-4 -mx-2">
                  <AreaChart data={spark} height={140} showDot up={isPositiveDay} />
                </div>
              </CardContent>
            </Card>
          </ErrorBoundary>

          {/* ----- Goal ring + Benchmark + Cash ----- */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {goalPortfolio ? (
              <Card>
                <CardContent className="flex items-center gap-4 p-4">
                  <ProgressRing
                    pct={goalPortfolio.total / goalPortfolio.target}
                    size={72}
                    thickness={8}
                  />
                  <div className="min-w-0">
                    <p className="text-section-header">목표 진척도</p>
                    <p className="mt-1 text-lg font-bold tabular-nums">
                      {formatKRW(goalPortfolio.total)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      / 목표 {formatKRW(goalPortfolio.target)}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="flex items-center gap-4 p-4">
                  <div className="flex size-[72px] shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
                    <Target className="size-6" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-section-header">목표 진척도</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      목표를 설정하고 진척도를 추적하세요.
                    </p>
                    <Link
                      href="/dashboard/portfolios"
                      className="mt-1 inline-flex min-h-[44px] items-center gap-1 text-xs font-medium text-primary hover:underline"
                    >
                      <Plus className="size-3" /> 설정하기
                    </Link>
                  </div>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardContent className="p-4">
                <p className="text-section-header">
                  {benchmark ? `vs ${benchmark.index_code}` : "벤치마크"}
                </p>
                <p
                  className={`mt-2 text-lg font-bold tabular-nums ${
                    benchmark && benchmark.delta_pct_points >= 0
                      ? "text-rise"
                      : benchmark
                        ? "text-fall"
                        : "text-muted-foreground"
                  }`}
                >
                  {benchmark
                    ? `${benchmark.delta_pct_points >= 0 ? "+" : ""}${benchmark.delta_pct_points.toFixed(2)}%p`
                    : "—"}
                </p>
                {benchmark && (
                  <p className="text-xs text-muted-foreground tabular-nums">
                    내 {benchmark.mine_pct.toFixed(2)}% · 벤치 {benchmark.benchmark_pct.toFixed(2)}%
                    ({benchmark.period})
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <p className="text-section-header">예수금</p>
                <p className="mt-2 text-lg font-bold tabular-nums">
                  {s.total_cash != null ? formatKRW(s.total_cash) : "—"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {s.total_cash != null ? "KIS 계좌 합계" : "KIS 연동 시 노출됩니다"}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* ----- Tasks (오늘 할 것) ----- */}
          {todayTasksList.count > 0 && (
            <section className="space-y-2">
              <div className="flex items-center justify-between">
                <h2 className="text-section-header">
                  오늘 할 것 · {todayTasksList.count}
                </h2>
                <Link
                  href="/dashboard/stream"
                  className="inline-flex min-h-[44px] items-center text-xs font-medium text-primary hover:underline"
                >
                  모두 보기
                </Link>
              </div>
              <div className="space-y-2">
                {todayTasksList.tasks.slice(0, 4).map((t) => {
                  const Icon = TASK_ICONS[t.kind] ?? Sparkles;
                  return (
                    <TaskCard
                      key={t.id}
                      icon={<Icon />}
                      title={t.title}
                      sub={t.sub ?? undefined}
                      accent={t.accent ?? undefined}
                    />
                  );
                })}
              </div>
            </section>
          )}

          {/* ----- Sector donut + Dividends ----- */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <section className="space-y-2 lg:col-span-2">
              <h2 className="text-section-header">자산 배분</h2>
              <Card>
                <CardContent className="flex flex-wrap items-center gap-6 p-4">
                  {sectorSegments.length > 0 ? (
                    <Donut
                      size={112}
                      thickness={14}
                      segments={sectorSegments}
                      center={
                        <div>
                          <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                            섹터
                          </div>
                          <div className="text-sm font-bold tabular-nums">
                            {sectorSegments.length}
                          </div>
                        </div>
                      }
                    />
                  ) : (
                    <div className="size-[112px] rounded-full bg-muted" aria-hidden />
                  )}
                  <div className="flex-1 min-w-0 space-y-1.5">
                    {sectorSegments.slice(0, 4).map((r) => (
                      <div
                        key={r.label ?? r.color}
                        className="flex items-center gap-2 text-sm"
                      >
                        <span
                          className="inline-block size-2 rounded-sm"
                          style={{ background: r.color }}
                          aria-hidden
                        />
                        <span className="flex-1 truncate">{r.label}</span>
                        <span className="font-semibold tabular-nums">
                          {(r.pct * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                    {sectorSegments.length === 0 && (
                      <p className="text-sm text-muted-foreground">
                        섹터 데이터를 불러오는 중...
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </section>

            <section className="space-y-2">
              <h2 className="text-section-header">
                다음 배당 · {dividendList.length}
              </h2>
              <Card>
                <CardContent className="divide-y p-0">
                  {dividendList.length === 0 && (
                    <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
                      <Coins className="size-4" />
                      30일 내 예정 배당이 없습니다.
                    </div>
                  )}
                  {dividendList.slice(0, 4).map((d) => (
                    <div
                      key={`${d.ticker}-${d.record_date}-${d.kind}`}
                      className="flex items-center justify-between p-3"
                    >
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold">
                          {d.name || d.ticker}
                        </div>
                        <div className="text-xs text-muted-foreground tabular-nums">
                          배당락 {d.ex_date ?? d.record_date} · 지급 {d.payment_date ?? "미정"}
                        </div>
                      </div>
                      <div className="shrink-0 text-right">
                        <div className="text-sm font-bold tabular-nums text-rise">
                          +
                          {d.currency === "KRW"
                            ? Number(d.amount).toLocaleString("ko-KR")
                            : `$${Number(d.amount).toFixed(2)}`}
                        </div>
                        {d.estimated_payout != null && (
                          <div className="text-[10px] text-muted-foreground tabular-nums">
                            예상 {Number(d.estimated_payout).toLocaleString("ko-KR")}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </section>
          </div>

          {/* ----- Holdings table (기존) ----- */}
          <section className="space-y-2">
            <h2 className="text-section-header">
              <span className="inline-flex items-center gap-1.5">
                <Wallet className="size-4" />
                보유 종목
              </span>
            </h2>
            <ErrorBoundary
              fallback={(err, reset) => (
                <WidgetErrorFallback title="보유 종목" error={err} reset={reset} />
              )}
            >
              <PortfolioList
                holdings={s.holdings}
                allocation={s.allocation}
                totalAsset={s.total_asset}
              />
            </ErrorBoundary>
          </section>

          {/* ----- Footer hint: short mode → movers quick link (full 구현 Step 6 이후) ----- */}
          {mode === "short" && (
            <Card>
              <CardContent className="flex items-center gap-3 p-4">
                <TrendingUp className="size-5 text-rise" />
                <div className="flex-1">
                  <p className="text-sm font-semibold">단타 모드</p>
                  <p className="text-xs text-muted-foreground">
                    실시간 mover/미체결 주문은 Step 6(종목 상세) 이후 연결됩니다.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
