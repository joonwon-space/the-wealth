"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { usePendingOrders } from "@/hooks/useOrders";
import { Card, CardContent } from "@/components/ui/card";
import { SectorBar } from "@/components/sector-bar";
import { Badge } from "@/components/ui/badge";
import { PortfolioHeader } from "./PortfolioHeader";
import { HoldingsSection } from "./HoldingsSection";
import { TransactionSection } from "./TransactionSection";
import { AnalysisSection } from "./AnalysisSection";
import type { Holding } from "./HoldingsSection";

interface PortfolioInfo {
  id: number;
  name: string;
  currency: string;
  kis_account_id: number | null;
  target_value: number | null;
}

interface RebalanceRow {
  sector: string;
  current_pct: number;
  target_pct: number;
  diff_pct: number;
  delta_krw: number;
  suggested_action: "BUY" | "SELL" | "HOLD";
}

interface RebalanceResponse {
  portfolio_id: number;
  total_value_krw: number;
  rows: RebalanceRow[];
}

const SECTOR_COLORS = [
  "var(--chart-1)",
  "var(--chart-3)",
  "var(--chart-5)",
  "var(--chart-6)",
  "var(--chart-7)",
  "var(--chart-8)",
  "var(--chart-2)",
  "var(--chart-4)",
];

function holdingsKey(portfolioId: number) {
  return ["portfolios", portfolioId, "holdings"] as const;
}

export default function PortfolioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const portfolioId = Number(id);
  const [showPendingOrders, setShowPendingOrders] = useState(false);

  const { data: portfolioInfo } = useQuery<PortfolioInfo>({
    queryKey: ["portfolio", portfolioId],
    queryFn: async () => {
      const { data } = await api.get<PortfolioInfo[]>("/portfolios");
      return (
        data.find((p) => p.id === portfolioId) ?? {
          id: portfolioId,
          name: "",
          currency: "KRW",
          kis_account_id: null,
          target_value: null,
        }
      );
    },
    staleTime: 60_000,
  });

  const isKisConnected = Boolean(portfolioInfo?.kis_account_id);

  const { data: holdings = [] } = useQuery<Holding[]>({
    queryKey: holdingsKey(portfolioId),
    queryFn: async () => {
      const { data } = await api.get<Holding[]>(
        `/portfolios/${portfolioId}/holdings/with-prices`,
      );
      return data;
    },
  });

  const { data: pendingOrders = [] } = usePendingOrders(isKisConnected ? portfolioId : 0);

  const { data: rebalance } = useQuery<RebalanceResponse>({
    queryKey: ["portfolios", portfolioId, "rebalance"],
    queryFn: async () =>
      (
        await api.get<RebalanceResponse>(
          `/portfolios/${portfolioId}/rebalance-suggestion`,
        )
      ).data,
    staleTime: 5 * 60_000,
    enabled: portfolioId > 0,
  });

  return (
    <div className="space-y-6">
      <PortfolioHeader
        portfolioId={portfolioId}
        holdings={holdings}
        isKisConnected={isKisConnected}
        pendingOrdersCount={pendingOrders.length}
        showPendingOrders={showPendingOrders}
        onTogglePendingOrders={() => setShowPendingOrders((v) => !v)}
      />

      <div className="space-y-6">
        {/* 보유 */}
        <HoldingsSection portfolioId={portfolioId} isKisConnected={isKisConnected} />

        {/* 개요 — 섹터 현재 vs 목표 */}
        <section className="space-y-2">
          <div className="flex items-baseline justify-between">
            <Link
              href={`/dashboard/rebalance?portfolio=${portfolioId}`}
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              리밸런싱 상세
              <ArrowRight className="size-3" />
            </Link>
          </div>
          <Card>
            <CardContent className="space-y-3 p-4">
              {(() => {
                const rows = Array.isArray(rebalance?.rows) ? rebalance.rows : [];
                if (rows.length === 0) {
                  return (
                    <div className="py-6 text-center text-sm text-muted-foreground">
                      목표 비중이 설정되지 않았습니다.{" "}
                      <Link
                        href={`/dashboard/rebalance?portfolio=${portfolioId}`}
                        className="text-primary hover:underline"
                      >
                        지금 설정하기
                      </Link>
                      .
                    </div>
                  );
                }
                const overCount = rows.filter((r) => r.suggested_action !== "HOLD").length;
                return (
                  <>
                    {rows.slice(0, 6).map((r, i) => (
                      <SectorBar
                        key={r.sector}
                        sector={r.sector}
                        pct={r.current_pct}
                        target={r.target_pct}
                        color={SECTOR_COLORS[i % SECTOR_COLORS.length]}
                      />
                    ))}
                    {overCount > 0 && (
                      <div className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2 text-xs">
                        <span className="text-muted-foreground">임계치 초과 섹터</span>
                        <Badge tone="warn">{overCount}개</Badge>
                      </div>
                    )}
                  </>
                );
              })()}
            </CardContent>
          </Card>
        </section>

        {/* 분석 — 평가금액 추이 + 벤치마크 + 환차손익 */}
        <AnalysisSection portfolioId={portfolioId} />

        {/* 거래내역 */}
        <TransactionSection
          portfolioId={portfolioId}
          holdings={holdings}
          isKisConnected={isKisConnected}
        />
      </div>
    </div>
  );
}
