"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { usePendingOrders } from "@/hooks/useOrders";
import { PortfolioHeader } from "./PortfolioHeader";
import { HoldingsSection } from "./HoldingsSection";
import { TransactionSection } from "./TransactionSection";
import type { Holding } from "./HoldingsSection";

interface PortfolioInfo {
  id: number;
  name: string;
  currency: string;
  kis_account_id: number | null;
  target_value: number | null;
}

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
      return data.find((p) => p.id === portfolioId) ?? { id: portfolioId, name: "", currency: "KRW", kis_account_id: null, target_value: null };
    },
    staleTime: 60_000,
  });

  const isKisConnected = Boolean(portfolioInfo?.kis_account_id);

  const { data: holdings = [] } = useQuery<Holding[]>({
    queryKey: holdingsKey(portfolioId),
    queryFn: async () => {
      const { data } = await api.get<Holding[]>(`/portfolios/${portfolioId}/holdings/with-prices`);
      return data;
    },
  });

  const { data: pendingOrders = [] } = usePendingOrders(isKisConnected ? portfolioId : 0);

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

      <HoldingsSection
        portfolioId={portfolioId}
        isKisConnected={isKisConnected}
      />

      <TransactionSection
        portfolioId={portfolioId}
        holdings={holdings}
        isKisConnected={isKisConnected}
      />
    </div>
  );
}
