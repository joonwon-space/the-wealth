"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PnLBadge } from "@/components/PnLBadge";
import { SectorAllocationChart } from "@/components/DynamicCharts";
import { WidgetErrorFallback } from "@/components/WidgetErrorFallback";

interface SectorAllocationItem {
  sector: string;
  value: number;
  weight: number;
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

export function SectorFxSection() {
  const {
    data: sectorAllocation = [],
    isLoading: sectorLoading,
    isError: sectorError,
    refetch: refetchSector,
  } = useQuery<SectorAllocationItem[]>({
    queryKey: ["analytics", "sector-allocation"],
    queryFn: () =>
      api.get<SectorAllocationItem[]>("/analytics/sector-allocation").then((r) => r.data),
    staleTime: 3_600_000,
  });

  const {
    data: fxGainLoss = [],
    isLoading: fxLoading,
    isError: fxError,
    refetch: refetchFx,
  } = useQuery<FxGainLossItem[]>({
    queryKey: ["analytics", "fx-gain-loss"],
    queryFn: () =>
      api.get<FxGainLossItem[]>("/analytics/fx-gain-loss").then((r) => r.data),
    staleTime: 3_600_000,
  });

  return (
    <>
      {/* 섹터 배분 */}
      <section className="space-y-3">
        <h2 className="text-base font-semibold">섹터 배분</h2>
        {sectorLoading ? (
          <Skeleton className="h-48 rounded-lg" />
        ) : sectorError ? (
          <WidgetErrorFallback
            message="섹터 배분을 불러오지 못했습니다."
            onRetry={() => refetchSector()}
          />
        ) : sectorAllocation.length > 0 ? (
          <Card>
            <CardContent className="p-4">
              <SectorAllocationChart data={sectorAllocation} />
            </CardContent>
          </Card>
        ) : null}
      </section>

      {/* 해외주식 환차익/환차손 */}
      <section className="space-y-3">
        <h2 className="text-base font-semibold">해외주식 환차익/환차손</h2>
        {fxLoading ? (
          <Skeleton className="h-32 rounded-lg" />
        ) : fxError ? (
          <WidgetErrorFallback
            message="환차익 데이터를 불러오지 못했습니다."
            onRetry={() => refetchFx()}
          />
        ) : fxGainLoss.length > 0 ? (
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50">
                    <tr>
                      {(
                        [
                          "종목",
                          "수량",
                          "매입가(USD)",
                          "현재가(USD)",
                          "주가 수익(KRW)",
                          "환차익(KRW)",
                          "총 손익(KRW)",
                        ] as const
                      ).map((h) => (
                        <th
                          key={h}
                          className="whitespace-nowrap px-4 py-2 text-left font-medium text-muted-foreground"
                        >
                          {h}
                        </th>
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
                        <td className="px-4 py-2 tabular-nums">
                          {item.quantity.toLocaleString("ko-KR")}
                        </td>
                        <td className="px-4 py-2 tabular-nums">
                          ${item.avg_price_usd.toFixed(2)}
                        </td>
                        <td className="px-4 py-2 tabular-nums">
                          ${item.current_price_usd.toFixed(2)}
                        </td>
                        <td className="px-4 py-2">
                          <PnLBadge value={item.stock_gain_krw} />
                        </td>
                        <td className="px-4 py-2">
                          <PnLBadge value={item.fx_gain_krw} />
                        </td>
                        <td className="px-4 py-2">
                          <PnLBadge value={item.total_pnl_krw} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="border-t px-4 py-2 text-xs text-muted-foreground">
                매입 시 환율: 보유 등록일 기준 / 현재 환율:{" "}
                {fxGainLoss[0]?.fx_rate_current.toLocaleString("ko-KR")}원/USD
              </div>
            </CardContent>
          </Card>
        ) : null}
      </section>
    </>
  );
}
