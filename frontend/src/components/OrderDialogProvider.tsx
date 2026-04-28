"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
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
 * portfolioId는 사용자 portfolios 첫 번째를 사용. 추후 ticker 보유 portfolio
 * 우선 선택 로직을 추가할 수 있다.
 */
export function OrderDialogProvider() {
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
      setState({
        ticker: detail.ticker,
        action: detail.action,
        stockName: detail.stockName ?? detail.ticker,
        currentPrice: detail.currentPrice,
        exchangeCode: detail.exchangeCode,
        portfolioId: list[0].id,
      });
    },
    [portfolios],
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
