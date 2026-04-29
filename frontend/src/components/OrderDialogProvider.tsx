"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

const OrderDialog = dynamic(
  () => import("@/components/OrderDialog").then((m) => ({ default: m.OrderDialog })),
  { ssr: false },
);

interface OrderEventDetail {
  ticker: string;
  action: "BUY" | "SELL";
  stockName?: string;
  currentPrice?: number;
  exchangeCode?: string;
}

interface PortfolioSummary {
  id: number;
  name: string;
  currency: "KRW" | "USD";
}

interface SummaryHolding {
  ticker: string;
  portfolio_name: string | null;
  currency: "KRW" | "USD";
}

interface DashboardSummary {
  holdings: SummaryHolding[];
}

interface OrderDialogState {
  ticker: string;
  stockName: string;
  action: "BUY" | "SELL";
  currentPrice?: number;
  exchangeCode?: string;
  portfolioId: number;
}

/**
 * 글로벌 'the-wealth:order' 이벤트 listener — stock detail 페이지의 매수/매도
 * 버튼이 dispatch한 이벤트를 받아 OrderDialog를 연다.
 *
 * 기본 portfolio 선택 우선순위:
 *   1) ticker 를 이미 보유한 portfolio (dashboard summary 캐시 활용)
 *   2) ticker currency 와 같은 currency 의 portfolio (KRW vs USD)
 *   3) portfolios 목록의 첫 번째
 */
export function OrderDialogProvider() {
  const queryClient = useQueryClient();
  const [state, setState] = useState<OrderDialogState | null>(null);

  const { data: portfolios } = useQuery<PortfolioSummary[]>({
    queryKey: ["portfolios", "for-order-dialog"],
    queryFn: async () => (await api.get<PortfolioSummary[]>("/portfolios")).data,
    staleTime: 60_000,
  });

  const handleOrderEvent = useCallback(
    (e: Event) => {
      const detail = (e as CustomEvent<OrderEventDetail>).detail;
      if (!detail || !detail.ticker) return;
      const list = Array.isArray(portfolios) ? portfolios : [];
      if (list.length === 0) return;

      const tickerCurrency: "KRW" | "USD" = detail.exchangeCode ? "USD" : "KRW";

      // 1) Already-holding portfolio — read from dashboard summary cache so we
      // don't issue a fresh fetch in the click path. portfolio_name → id map
      // joins dashboard's per-holding portfolio_name with the portfolios list.
      const summary = queryClient.getQueryData<DashboardSummary>([
        "dashboard",
        "summary",
      ]);
      const heldPortfolioName = summary?.holdings?.find(
        (h) => h.ticker === detail.ticker,
      )?.portfolio_name;
      const heldPortfolio =
        heldPortfolioName != null
          ? list.find((p) => p.name === heldPortfolioName)
          : undefined;

      // 2) Currency-compatible portfolio
      const currencyMatch = list.find((p) => p.currency === tickerCurrency);

      const chosen = heldPortfolio ?? currencyMatch ?? list[0];

      setState({
        ticker: detail.ticker,
        action: detail.action,
        stockName: detail.stockName ?? detail.ticker,
        currentPrice: detail.currentPrice,
        exchangeCode: detail.exchangeCode,
        portfolioId: chosen.id,
      });
    },
    [portfolios, queryClient],
  );

  useEffect(() => {
    window.addEventListener("the-wealth:order", handleOrderEvent);
    return () => {
      window.removeEventListener("the-wealth:order", handleOrderEvent);
    };
  }, [handleOrderEvent]);

  if (!state) return null;

  return (
    <OrderDialog
      open
      onOpenChange={(open) => {
        if (!open) setState(null);
      }}
      portfolioId={state.portfolioId}
      ticker={state.ticker}
      stockName={state.stockName}
      currentPrice={state.currentPrice}
      exchangeCode={state.exchangeCode}
      initialTab={state.action}
    />
  );
}
