"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AlertTriangle, BarChart3, Plus, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { usePriceStream } from "@/hooks/usePriceStream";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { AllocationDonut } from "@/components/DynamicCharts";
import { DayChangeBadge } from "@/components/DayChangeBadge";
import { HoldingsTable } from "@/components/HoldingsTable";
import { PnLBadge } from "@/components/PnLBadge";
import { formatKRW, formatRate } from "@/lib/format";
import { WatchlistSection } from "@/components/WatchlistSection";
import { toast } from "sonner";

const REFRESH_INTERVAL_MS = 30_000;
const DONUT_COLORS = ["#e31f26", "#1a56db", "#f59e0b", "#10b981", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];

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
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // SSE 실시간 가격 업데이트
  const handleStreamPrices = useCallback((prices: Record<string, string>) => {
    setSummary((prev) => {
      if (!prev) return prev;
      // SSE에서 환율을 모를 경우 기존 계산을 유지 (국내주식만 업데이트)
      const updatedHoldings = prev.holdings.map((h) => {
        const newPrice = prices[h.ticker];
        if (!newPrice) return h;
        const current_price = Number(newPrice);
        if (h.currency === "USD") {
          // 해외주식: 현재가만 업데이트 (PnL은 서버에서 원화 환산 필요)
          return { ...h, current_price };
        }
        const market_value = h.quantity * current_price;
        const invested = h.quantity * h.avg_price;
        const pnl_amount = market_value - invested;
        const pnl_rate = invested ? (pnl_amount / invested) * 100 : null;
        return { ...h, current_price, market_value, market_value_krw: market_value, pnl_amount, pnl_rate };
      });
      const total_asset = updatedHoldings.reduce(
        (sum, h) => sum + (h.market_value_krw ?? h.quantity * h.avg_price),
        0
      );
      const total_pnl_amount = total_asset - prev.total_invested;
      const total_pnl_rate = prev.total_invested ? (total_pnl_amount / prev.total_invested) * 100 : 0;
      return { ...prev, holdings: updatedHoldings, total_asset, total_pnl_amount, total_pnl_rate };
    });
    setLastUpdated(new Date());
  }, []);

  usePriceStream({ onPrices: handleStreamPrices, enabled: !loading });

  const fetchSummary = async (refresh = false) => {
    if (refresh) setRefreshing(true);
    try {
      const { data } = await api.get<Summary>("/dashboard/summary", {
        params: refresh ? { refresh: true } : undefined,
      });
      setSummary(data);
      setError(null);
      setLastUpdated(new Date());
      // 목표가 알림 토스트
      for (const alert of data.triggered_alerts ?? []) {
        const label = alert.name || alert.ticker;
        const dir = alert.condition === "above" ? "이상" : "이하";
        toast.warning(`📊 ${label} 목표가 도달`, {
          description: `현재 ${formatKRW(alert.current_price)} — 목표 ${dir} ${formatKRW(alert.threshold)}`,
          duration: 8000,
        });
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "서버에 연결할 수 없습니다";
      setError(message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchSummary();
    intervalRef.current = setInterval(fetchSummary, REFRESH_INTERVAL_MS);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, []);

  if (loading) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-8 w-32" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-4 space-y-2">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-6 w-28" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="space-y-2">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-48 w-48 rounded-full mx-auto" />
        </div>
        <div className="space-y-2">
          <Skeleton className="h-5 w-20" />
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="space-y-8">
        <h1 className="text-2xl font-bold">대시보드</h1>
        <div className="flex flex-col items-center justify-center rounded-xl border border-destructive/30 bg-destructive/5 py-16 text-center">
          <AlertTriangle className="mb-3 h-10 w-10 text-destructive/60" />
          <p className="text-lg font-semibold">데이터를 불러올 수 없습니다</p>
          <p className="mt-1 text-sm text-muted-foreground">{error}</p>
          <button
            onClick={() => { setLoading(true); setError(null); fetchSummary(); }}
            className="mt-5 flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            <RefreshCw className="h-4 w-4" />
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  const s = summary ?? {
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
  };

  const hasNoPortfolio = !loading && s.holdings.length === 0 && s.total_invested === 0;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">대시보드</h1>
        <div className="flex items-center gap-2">
          {lastUpdated && (
            <span className="text-xs text-muted-foreground">
              {refreshing ? "업데이트 중..." : lastUpdated.toLocaleTimeString("ko-KR")}
            </span>
          )}
          <button
            onClick={() => fetchSummary(true)}
            disabled={refreshing}
            className="rounded p-1 text-muted-foreground hover:bg-muted disabled:opacity-50"
            title="새로고침"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

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
          {/* 요약 카드 */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">총 자산</p>
                <p className="mt-1 text-xl font-bold tabular-nums">{formatKRW(s.total_asset)}</p>
                {(s.day_change_pct != null || s.total_day_change_rate != null) && (
                  <p className="mt-0.5 text-xs flex items-center gap-1">
                    <span className="text-muted-foreground">전일 대비</span>
                    <DayChangeBadge pct={s.day_change_pct ?? s.total_day_change_rate} />
                    {s.day_change_amount != null && (
                      <PnLBadge value={s.day_change_amount} />
                    )}
                  </p>
                )}
              </CardContent>
            </Card>
            <SummaryCard label="투자 원금" value={formatKRW(s.total_invested)} />
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">총 손익</p>
                <p className="mt-1 text-xl font-bold">
                  <PnLBadge value={s.total_pnl_amount} />
                </p>
                <p className="text-xs">
                  <PnLBadge value={s.total_pnl_rate} suffix="%" />
                </p>
              </CardContent>
            </Card>
          </div>

          {/* 자산 배분 도넛 차트 */}
          {s.allocation.length > 0 && (
            <section className="space-y-2">
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

          {/* 관심 종목 */}
          <WatchlistSection />

          {/* 보유 종목 테이블 */}
          <section className="space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold">보유 종목</h2>
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
        </>
      )}
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 text-xl font-bold tabular-nums">{value}</p>
      </CardContent>
    </Card>
  );
}
