"use client";

import { useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { WidgetErrorFallback } from "@/components/WidgetErrorFallback";

interface Metrics {
  total_return_rate: number | null;
  cagr: number | null;
  mdd: number | null;
  sharpe_ratio: number | null;
}

interface MetricCardProps {
  label: string;
  value: number | null;
  suffix?: string;
  tooltip?: string;
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
  const display =
    value != null
      ? `${value > 0 && suffix === "%" ? "+" : ""}${value.toFixed(suffix === "%" ? 2 : 3)}${suffix}`
      : "—";
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

export function MetricsSection() {
  const {
    data: metrics,
    isLoading,
    isError,
    refetch,
  } = useQuery<Metrics>({
    queryKey: ["analytics", "metrics"],
    queryFn: () => api.get<Metrics>("/analytics/metrics").then((r) => r.data),
    staleTime: 3_600_000,
  });

  return (
    <section className="space-y-2">
      <h2 className="text-base font-semibold">성과 지표</h2>
      {isLoading ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-lg" />
          ))}
        </div>
      ) : isError ? (
        <WidgetErrorFallback
          message="지표를 불러오지 못했습니다."
          onRetry={() => refetch()}
        />
      ) : metrics ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <MetricCard
            label="총 수익률"
            value={metrics.total_return_rate}
            suffix="%"
            tooltip="전체 투자 기간 동안의 누적 수익률"
          />
          <MetricCard
            label="CAGR"
            value={metrics.cagr}
            suffix="%"
            tooltip="연평균 복리 수익률(CAGR): 투자 원금이 현재 가치가 되기까지 매년 몇 %씩 성장했는지 나타냅니다. 데이터가 30일 미만이면 표시되지 않습니다."
            nullHint="데이터 30일 이상 필요"
          />
          <MetricCard
            label="MDD"
            value={metrics.mdd != null ? -metrics.mdd : null}
            suffix="%"
            tooltip="최대 낙폭(MDD): 고점 대비 최대 하락폭입니다. 값이 클수록 손실 위험이 큽니다."
            nullHint="이력 데이터 부족"
          />
          <MetricCard
            label="샤프 비율"
            value={metrics.sharpe_ratio}
            tooltip="샤프 비율: 위험(변동성) 한 단위당 초과 수익률. 1 이상이면 양호, 2 이상이면 우수합니다."
            nullHint="데이터 30일 이상 필요"
          />
        </div>
      ) : null}
    </section>
  );
}
