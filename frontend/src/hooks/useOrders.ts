"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface Order {
  id: number;
  portfolio_id: number;
  kis_account_id: number | null;
  ticker: string;
  name: string | null;
  order_type: "BUY" | "SELL";
  order_class: "limit" | "market";
  quantity: string; // Decimal serialized as string
  price: string | null;
  order_no: string | null;
  status: "pending" | "filled" | "partial" | "cancelled" | "failed";
  filled_quantity: string | null;
  filled_price: string | null;
  memo: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrderRequest {
  ticker: string;
  name?: string;
  order_type: "BUY" | "SELL";
  order_class: "limit" | "market";
  quantity: number;
  price?: number;
  exchange_code?: string;
  memo?: string;
}

export interface CashBalance {
  total_cash: string;
  available_cash: string;
  total_evaluation: string;
  total_profit_loss: string;
  profit_loss_rate: string;
  currency: "KRW" | "USD";
  foreign_cash: string | null;
  usd_krw_rate: string | null;
}

export interface OrderableInfo {
  orderable_quantity: string;
  orderable_amount: string;
  current_price: string | null;
  currency: "KRW" | "USD";
}

export interface PendingOrder {
  order_no: string;
  ticker: string;
  name: string;
  order_type: "BUY" | "SELL";
  order_class: "limit" | "market";
  quantity: string;
  price: string;
  filled_quantity: string;
  remaining_quantity: string;
  order_time: string;
}

// ─── Query Keys ──────────────────────────────────────────────────────────────

const CASH_BALANCE_KEY = (portfolioId: number) =>
  ["cash-balance", portfolioId] as const;

const ORDERABLE_KEY = (
  portfolioId: number,
  ticker: string,
  price: number,
  orderType: string
) => ["orderable", portfolioId, ticker, price, orderType] as const;

const PENDING_ORDERS_KEY = (portfolioId: number) =>
  ["pending-orders", portfolioId] as const;

// ─── API Functions ───────────────────────────────────────────────────────────

async function fetchCashBalance(portfolioId: number): Promise<CashBalance> {
  const res = await api.get<CashBalance>(
    `/portfolios/${portfolioId}/cash-balance`
  );
  return res.data;
}

async function fetchOrderableQuantity(
  portfolioId: number,
  ticker: string,
  price: number,
  orderType: string
): Promise<OrderableInfo> {
  const res = await api.get<OrderableInfo>(
    `/portfolios/${portfolioId}/orders/orderable`,
    { params: { ticker, price, order_type: orderType } }
  );
  return res.data;
}

async function fetchPendingOrders(
  portfolioId: number,
  isOverseas = false
): Promise<PendingOrder[]> {
  const res = await api.get<PendingOrder[]>(
    `/portfolios/${portfolioId}/orders/pending`,
    { params: { is_overseas: isOverseas } }
  );
  return res.data;
}

async function placeOrder(
  portfolioId: number,
  request: OrderRequest
): Promise<Order> {
  const res = await api.post<Order>(
    `/portfolios/${portfolioId}/orders`,
    request
  );
  return res.data;
}

async function settleOrders(portfolioId: number): Promise<{
  settled: number;
  partial: number;
  unchanged: number;
}> {
  const res = await api.post(`/portfolios/${portfolioId}/orders/settle`);
  return res.data;
}

async function cancelPendingOrder(
  portfolioId: number,
  orderNo: string,
  params: {
    ticker: string;
    quantity: number;
    price: number;
    is_overseas?: boolean;
    exchange_code?: string;
  }
): Promise<void> {
  await api.delete(`/portfolios/${portfolioId}/orders/${orderNo}`, { params });
}

// ─── Hooks ───────────────────────────────────────────────────────────────────

/** 예수금 + 총 평가금액 조회 (30초 폴링). */
export function useCashBalance(portfolioId: number) {
  return useQuery<CashBalance>({
    queryKey: CASH_BALANCE_KEY(portfolioId),
    queryFn: () => fetchCashBalance(portfolioId),
    refetchInterval: 30_000,
    staleTime: 15_000,
    enabled: portfolioId > 0,
  });
}

/** 주문 가능 수량/금액 조회. */
export function useOrderableQuantity(
  portfolioId: number,
  ticker: string,
  price: number,
  orderType: "BUY" | "SELL"
) {
  return useQuery<OrderableInfo>({
    queryKey: ORDERABLE_KEY(portfolioId, ticker, price, orderType),
    queryFn: () => fetchOrderableQuantity(portfolioId, ticker, price, orderType),
    enabled: portfolioId > 0 && ticker.length > 0 && price >= 0,
    staleTime: 10_000,
  });
}

/** 미체결 주문 목록 조회 (30초 폴링). */
export function usePendingOrders(portfolioId: number, isOverseas = false) {
  return useQuery<PendingOrder[]>({
    queryKey: PENDING_ORDERS_KEY(portfolioId),
    queryFn: () => fetchPendingOrders(portfolioId, isOverseas),
    refetchInterval: 30_000,
    staleTime: 15_000,
    enabled: portfolioId > 0,
  });
}

/** 주문 실행 mutation. 성공 시 관련 캐시 무효화. */
export function usePlaceOrder(portfolioId: number) {
  const queryClient = useQueryClient();

  return useMutation<Order, Error, OrderRequest>({
    mutationFn: (request) => placeOrder(portfolioId, request),
    onSuccess: () => {
      // pending 주문은 holdings/평가금액에 영향을 주지 않으므로
      // 미체결 목록과 예수금만 무효화한다.
      queryClient.invalidateQueries({
        queryKey: CASH_BALANCE_KEY(portfolioId),
      });
      queryClient.invalidateQueries({
        queryKey: PENDING_ORDERS_KEY(portfolioId),
      });
    },
  });
}

/** 주문 취소 mutation. */
export function useCancelOrder(portfolioId: number) {
  const queryClient = useQueryClient();

  return useMutation<
    void,
    Error,
    {
      orderNo: string;
      ticker: string;
      quantity: number;
      price: number;
      isOverseas?: boolean;
      exchangeCode?: string;
    }
  >({
    mutationFn: ({ orderNo, ticker, quantity, price, isOverseas, exchangeCode }) =>
      cancelPendingOrder(portfolioId, orderNo, {
        ticker,
        quantity,
        price,
        is_overseas: isOverseas,
        exchange_code: exchangeCode,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: PENDING_ORDERS_KEY(portfolioId),
      });
      queryClient.invalidateQueries({
        queryKey: CASH_BALANCE_KEY(portfolioId),
      });
    },
  });
}

/** 미체결 주문 수동 체결 확인 mutation. */
export function useSettleOrders(portfolioId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => settleOrders(portfolioId),
    onSuccess: (data) => {
      if (data.settled > 0 || data.partial > 0) {
        queryClient.invalidateQueries({ queryKey: PENDING_ORDERS_KEY(portfolioId) });
        queryClient.invalidateQueries({ queryKey: CASH_BALANCE_KEY(portfolioId) });
        queryClient.invalidateQueries({ queryKey: ["portfolios", portfolioId, "holdings"] });
        queryClient.invalidateQueries({ queryKey: ["portfolio", portfolioId] });
        queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      }
    },
  });
}
