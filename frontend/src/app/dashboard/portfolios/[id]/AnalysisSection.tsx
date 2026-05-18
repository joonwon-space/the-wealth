"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { AreaChart } from "@/components/charts/area-chart";

interface PortfolioHistoryPoint {
  date: string;
  value: number;
}

interface AnalysisSectionProps {
  portfolioId: number;
}

const PERIOD_LABEL = "1개월";
const PERIOD = "1M";

export function AnalysisSection({ portfolioId }: AnalysisSectionProps) {
  const { data: history } = useQuery<PortfolioHistoryPoint[]>({
    queryKey: ["analytics", "portfolio-history", PERIOD, portfolioId],
    queryFn: async () =>
      (
        await api.get<PortfolioHistoryPoint[]>("/analytics/portfolio-history", {
          params: { period: PERIOD, portfolio_id: portfolioId },
        })
      ).data,
    staleTime: 5 * 60_000,
    enabled: portfolioId > 0,
  });

  const sparkData =
    Array.isArray(history) && history.length > 0
      ? history.map((p) => ({ v: Number(p.value) }))
      : [];

  const isUp =
    sparkData.length >= 2 && sparkData[sparkData.length - 1].v >= sparkData[0].v;

  return (
    <section className="space-y-3" aria-label="분석">
      <h2 className="text-sm font-semibold text-foreground">분석 · {PERIOD_LABEL}</h2>

      <Card>
        <CardContent className="p-4">
          <div className="text-xs text-muted-foreground mb-2">평가금액 추이</div>
          <AreaChart data={sparkData} height={140} showDot up={isUp} />
        </CardContent>
      </Card>
    </section>
  );
}
