"use client";

import {
  ArrowDownRight,
  ArrowUpRight,
  Banknote,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { AreaChart, Area, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardContent } from "@/components/ui/card";
import { DayChangeBadge } from "@/components/DayChangeBadge";
import { PnLBadge } from "@/components/PnLBadge";
import { formatKRW } from "@/lib/format";

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

interface DashboardMetricsProps {
  totalAsset: number;
  animatedTotalAsset: number;
  animatedTotalInvested: number;
  animatedTotalPnl: number;
  totalPnlAmount: number;
  totalPnlRate: number;
  dayChangePct: number | null;
  dayChangeAmount: number | null;
  totalCash: number | null;
  usdKrwRate: number | null;
  holdings: HoldingRow[];
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

export function DashboardMetrics({
  totalAsset,
  animatedTotalAsset,
  animatedTotalInvested,
  animatedTotalPnl,
  totalPnlAmount,
  dayChangePct,
  dayChangeAmount,
  totalCash,
  usdKrwRate,
}: DashboardMetricsProps) {
  const sparklineData = generateSparklineData(totalAsset);
  const isPositiveDayChange = (dayChangePct ?? 0) >= 0;

  return (
    <>
      {/* 총 자산 Large 카드 */}
      <Card
        className="relative overflow-hidden border border-white/10 backdrop-blur-sm bg-card/80 animate-in fade-in slide-in-from-bottom-2 duration-500"
        style={{ animationDelay: "0ms", animationFillMode: "both" }}
      >
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
                  <span
                    className={`flex items-center gap-0.5 text-sm font-medium ${isPositiveDayChange ? "text-rise" : "text-fall"}`}
                  >
                    {isPositiveDayChange ? (
                      <ArrowUpRight className="h-4 w-4" />
                    ) : (
                      <ArrowDownRight className="h-4 w-4" />
                    )}
                    <DayChangeBadge pct={dayChangePct} />
                  </span>
                )}
                {dayChangeAmount != null && <PnLBadge value={dayChangeAmount} />}
                <span className="text-metric-label">전일 대비</span>
              </div>
              {usdKrwRate != null && (
                <p className="mt-1 text-metric-label text-numeric">
                  USD/KRW {formatKRW(usdKrwRate)}
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
      <div
        className={`grid grid-cols-1 gap-4 animate-in fade-in slide-in-from-bottom-2 duration-500 ${totalCash != null ? "sm:grid-cols-3" : "sm:grid-cols-2"}`}
        style={{ animationDelay: "100ms", animationFillMode: "both" }}
      >
        {/* 투자 원금 카드 */}
        <MetricCard
          label="투자 원금"
          value={formatKRW(animatedTotalInvested)}
          icon={<Wallet className="h-4 w-4" />}
          accentColor="var(--chart-6)"
        />

        {/* 예수금 카드 (KIS 연결 시에만) */}
        {totalCash != null && (
          <MetricCard
            label="예수금 합계"
            value={formatKRW(totalCash)}
            icon={<Banknote className="h-4 w-4" />}
            accentColor="var(--chart-2)"
          />
        )}

        {/* 총 손익 카드 */}
        <Card className="relative overflow-hidden backdrop-blur-sm bg-card/80 border border-white/10">
          <div
            className="absolute top-0 left-0 right-0 h-0.5"
            style={{
              background: totalPnlAmount >= 0 ? "var(--rise)" : "var(--fall)",
            }}
          />
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-metric-label">총 손익</p>
              <span
                className="flex items-center justify-center h-7 w-7 rounded-full"
                style={{
                  background:
                    totalPnlAmount >= 0
                      ? "color-mix(in oklch, var(--rise) 15%, transparent)"
                      : "color-mix(in oklch, var(--fall) 15%, transparent)",
                  color: totalPnlAmount >= 0 ? "var(--rise)" : "var(--fall)",
                }}
              >
                <TrendingUp className="h-4 w-4" />
              </span>
            </div>
            <p className="text-xl font-bold">
              <PnLBadge value={animatedTotalPnl} />
            </p>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
