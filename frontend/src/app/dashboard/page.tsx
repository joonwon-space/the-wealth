"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { BarChart3, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { AllocationDonut } from "@/components/AllocationDonut";
import { HoldingsTable } from "@/components/HoldingsTable";
import { PnLBadge } from "@/components/PnLBadge";

const REFRESH_INTERVAL_MS = 30_000;
const DONUT_COLORS = ["#e31f26", "#1a56db", "#f59e0b", "#10b981", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];

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
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchSummary = async () => {
    try {
      const { data } = await api.get<Summary>("/dashboard/summary");
      setSummary(data);
    } catch {
      setSummary(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
    intervalRef.current = setInterval(fetchSummary, REFRESH_INTERVAL_MS);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
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

  const hasNoPortfolio = !loading && s.holdings.length === 0 && s.total_invested === 0;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">대시보드</h1>

      {/* 포트폴리오/종목이 없을 때 빈 상태 */}
      {hasNoPortfolio ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
          <BarChart3 className="mb-3 h-12 w-12 text-muted-foreground/40" />
          <p className="text-lg font-semibold">아직 보유 종목이 없습니다</p>
          <p className="mt-1 text-sm text-muted-foreground">포트폴리오를 만들고 종목을 추가해보세요.</p>
          <Link
            href="/dashboard/portfolios"
            className="mt-5 flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            <Plus className="h-4 w-4" />
            포트폴리오 만들기
          </Link>
        </div>
      ) : (
        <>
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
                      <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: DONUT_COLORS[i % DONUT_COLORS.length] }} />
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
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold">보유 종목</h2>
              {s.holdings.length === 0 && (
                <Link
                  href="/dashboard/portfolios"
                  className="flex items-center gap-1 text-sm text-primary hover:underline"
                >
                  <Plus className="h-3.5 w-3.5" />
                  종목 추가하기
                </Link>
              )}
            </div>
            <HoldingsTable holdings={s.holdings} />
          </section>
        </>
      )}
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border bg-card p-4 shadow-sm">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-bold tabular-nums">{value}</p>
    </div>
  );
}
