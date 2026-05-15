"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface CashSummaryAccount {
  kis_account_id: number;
  label: string;
  total_cash: string | null;
  available_cash: string | null;
  total_evaluation: string | null;
  total_profit_loss: string | null;
  foreign_cash: string | null;
  usd_krw_rate: string | null;
  error: string | null;
}

export interface CashSummary {
  total_cash: string;
  available_cash: string;
  total_evaluation: string;
  total_profit_loss: string;
  kis_connected: boolean;
  accounts: CashSummaryAccount[];
  has_errors: boolean;
}

export const CASH_SUMMARY_QUERY_KEY = ["dashboard", "cash-summary"] as const;

async function fetchCashSummary(): Promise<CashSummary> {
  const res = await api.get<CashSummary>("/dashboard/cash-summary");
  return res.data;
}

/** 사용자의 모든 KIS 계좌 예수금 합산 조회 (30초 폴링, 60초 stale). */
export function useCashSummary(options?: { enabled?: boolean }) {
  return useQuery<CashSummary>({
    queryKey: CASH_SUMMARY_QUERY_KEY,
    queryFn: fetchCashSummary,
    refetchInterval: 30_000,
    staleTime: 30_000,
    enabled: options?.enabled ?? true,
    retry: 1,
  });
}
