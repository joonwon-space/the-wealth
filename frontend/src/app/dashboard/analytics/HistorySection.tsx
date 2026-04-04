"use client";

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
import { formatKRW } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PortfolioHistoryChart } from "@/components/DynamicCharts";

interface HistoryPoint {
  date: string;
  value: number;
}

interface KrwAssetPoint {
  date: string;
  value: number;
  domestic_value: number;
  overseas_value_krw: number;
}

interface HistorySectionProps {
  period: "1W" | "1M" | "3M" | "6M" | "1Y" | "ALL";
  onPeriodChange: (p: "1W" | "1M" | "3M" | "6M" | "1Y" | "ALL") => void;
}

export function HistorySection({ period, onPeriodChange }: HistorySectionProps) {
  const {
    data: portfolioHistory = [],
    isLoading: historyLoading,
    isError: historyError,
    refetch: refetchHistory,
  } = useQuery<HistoryPoint[]>({
    queryKey: ["analytics", "portfolio-history", period],
    queryFn: () =>
      api
        .get<HistoryPoint[]>("/analytics/portfolio-history", { params: { period } })
        .then((r) => r.data),
    staleTime: 3_600_000,
  });

  const {
    data: krwAssetHistory = [],
    isLoading: krwLoading,
    isError: krwError,
    refetch: refetchKrw,
  } = useQuery<KrwAssetPoint[]>({
    queryKey: ["analytics", "krw-asset-history", period],
    queryFn: () =>
      api
        .get<KrwAssetPoint[]>("/analytics/krw-asset-history", { params: { period } })
        .then((r) => r.data),
    staleTime: 3_600_000,
  });

  return (
    <>
      {/* 포트폴리오 가치 추이 */}
      <section className="space-y-2">
        <h2 className="text-base font-semibold">포트폴리오 가치 추이</h2>
        {historyLoading ? (
          <Skeleton className="h-48 rounded-lg" />
        ) : historyError ? (
          <div className="flex items-center gap-2 text-sm text-destructive">
            <span>포트폴리오 히스토리를 불러오지 못했습니다.</span>
            <button onClick={() => refetchHistory()} className="underline">
              다시 시도
            </button>
          </div>
        ) : (
          <PortfolioHistoryChart
            data={portfolioHistory}
            period={period}
            onPeriodChange={onPeriodChange}
          />
        )}
      </section>

      {/* 원화 환산 총 자산 추이 */}
      {krwLoading ? (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">원화 환산 총 자산 추이</h2>
          <Skeleton className="h-48 rounded-lg" />
        </section>
      ) : krwError ? (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">원화 환산 총 자산 추이</h2>
          <div className="flex items-center gap-2 text-sm text-destructive">
            <span>데이터를 불러오지 못했습니다.</span>
            <button onClick={() => refetchKrw()} className="underline">
              다시 시도
            </button>
          </div>
        </section>
      ) : krwAssetHistory.length > 0 ? (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">원화 환산 총 자산 추이</h2>
          <p className="text-xs text-muted-foreground">
            해외주식은 해당 날짜 환율로 원화 환산. 기간 탭은 위 차트와 연동됩니다.
          </p>
          <Card>
            <CardContent className="p-4">
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart
                  data={krwAssetHistory}
                  margin={{ top: 4, right: 8, bottom: 0, left: 0 }}
                >
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
      ) : null}
    </>
  );
}
