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
import { WidgetErrorFallback } from "@/components/WidgetErrorFallback";

interface KrwAssetPoint {
  date: string;
  value: number;
  domestic_value: number;
  overseas_value_krw: number;
}

type Period = "1W" | "1M" | "3M" | "6M" | "1Y" | "ALL";

interface HistorySectionProps {
  period: Period;
  onPeriodChange: (p: Period) => void;
}

const PERIODS: Period[] = ["1W", "1M", "3M", "6M", "1Y", "ALL"];

/**
 * 유저 전체 자산 KRW 환산 추이 (국내 + 해외 환율 환산 분해).
 *
 * portfolio별 가치 추이 + 벤치마크 비교는 portfolio detail 페이지의
 * `AnalysisSection` 으로 위임됨 (RD-7 follow-up). 본 섹션은 사용자 단위
 * 환차 영향을 시각화하는 용도로만 남는다.
 */
export function HistorySection({ period, onPeriodChange }: HistorySectionProps) {
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
    <section className="space-y-2">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-base font-semibold">원화 환산 총 자산 추이</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            해외주식은 해당 날짜 환율로 원화 환산. 포트폴리오별 추이는 각 포트폴리오 상세 페이지의
            &lsquo;분석&rsquo; 섹션을 참고하세요.
          </p>
        </div>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => onPeriodChange(p)}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                period === p
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {krwLoading ? (
        <Skeleton className="h-48 rounded-lg" />
      ) : krwError ? (
        <WidgetErrorFallback
          message="데이터를 불러오지 못했습니다."
          onRetry={() => refetchKrw()}
        />
      ) : krwAssetHistory.length === 0 ? (
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">
              스냅샷 데이터가 쌓이면 표시됩니다.
            </p>
          </CardContent>
        </Card>
      ) : (
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
      )}
    </section>
  );
}
