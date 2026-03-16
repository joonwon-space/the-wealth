"use client";

import { useEffect, useState, useOptimistic, useTransition } from "react";
import { api } from "@/lib/api";
import { AllocationDonut } from "@/components/AllocationDonut";
import { HoldingsTable } from "@/components/HoldingsTable";
import { PnLBadge } from "@/components/PnLBadge";

interface HoldingRow {
  id: number;
  ticker: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number | null;
  market_value: number | null;
  pnl_amount: number | null;
  pnl_rate: number | null;
}

interface AllocationItem {
  ticker: string;
  name: string;
  value: number;
  ratio: number;
}

interface Summary {
  total_asset: number;
  total_invested: number;
  total_pnl_amount: number;
  total_pnl_rate: number;
  holdings: HoldingRow[];
  allocation: AllocationItem[];
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<Summary>("/dashboard/summary")
      .then(({ data }) => setSummary(data))
      .catch(() => setSummary(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <span className="text-muted-foreground text-sm">불러오는 중...</span>
      </div>
    );
  }

  const s = summary ?? {
    total_asset: 0,
    total_invested: 0,
    total_pnl_amount: 0,
    total_pnl_rate: 0,
    holdings: [],
    allocation: [],
  };

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">대시보드</h1>

      {/* 요약 카드 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <SummaryCard label="총 자산" value={`₩${s.total_asset.toLocaleString("ko-KR")}`} />
        <SummaryCard label="투자 원금" value={`₩${s.total_invested.toLocaleString("ko-KR")}`} />
        <div className="rounded-xl border bg-card p-4 shadow-sm">
          <p className="text-xs text-muted-foreground">총 손익</p>
          <p className="mt-1 text-xl font-bold">
            <PnLBadge value={s.total_pnl_amount} />
          </p>
          <p className="text-xs">
            <PnLBadge value={s.total_pnl_rate} suffix="%" />
          </p>
        </div>
      </div>

      {/* 자산 배분 도넛 차트 */}
      {s.allocation.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">자산 배분</h2>
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
            <AllocationDonut data={s.allocation} totalAsset={s.total_asset} />
            <div className="flex flex-wrap gap-2">
              {s.allocation.map((item, i) => (
                <div key={item.ticker} className="flex items-center gap-1.5 text-xs">
                  <span
                    className="inline-block h-2.5 w-2.5 rounded-full"
                    style={{ background: DONUT_COLORS[i % DONUT_COLORS.length] }}
                  />
                  <span>{item.name}</span>
                  <span className="text-muted-foreground">{item.ratio.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* 보유 종목 테이블 */}
      <section className="space-y-2">
        <h2 className="text-base font-semibold">보유 종목</h2>
        <HoldingsTable holdings={s.holdings} />
      </section>
    </div>
  );
}

const DONUT_COLORS = ["#e31f26", "#1a56db", "#f59e0b", "#10b981", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border bg-card p-4 shadow-sm">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-bold tabular-nums">{value}</p>
    </div>
  );
}
