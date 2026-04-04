"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { MonthlyHeatmap } from "@/components/MonthlyHeatmap";

interface MonthlyReturnItem {
  year: number;
  month: number;
  return_rate: number;
}

export function MonthlyReturnsSection() {
  const {
    data: monthlyReturns = [],
    isLoading,
    isError,
    refetch,
  } = useQuery<MonthlyReturnItem[]>({
    queryKey: ["analytics", "monthly-returns"],
    queryFn: () =>
      api.get<MonthlyReturnItem[]>("/analytics/monthly-returns").then((r) => r.data),
    staleTime: 3_600_000,
  });

  return (
    <section className="space-y-2">
      <h2 className="text-base font-semibold">월별 수익률</h2>
      {isLoading ? (
        <Skeleton className="h-32 rounded-lg" />
      ) : isError ? (
        <div className="flex items-center gap-2 text-sm text-destructive">
          <span>월별 수익률을 불러오지 못했습니다.</span>
          <button onClick={() => refetch()} className="underline">
            다시 시도
          </button>
        </div>
      ) : (
        <MonthlyHeatmap data={monthlyReturns} />
      )}
    </section>
  );
}
