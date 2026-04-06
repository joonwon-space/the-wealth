"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AllocationDonut } from "@/components/DynamicCharts";
import { HoldingsTable } from "@/components/HoldingsTable";
import { TopHoldingsWidget } from "@/components/TopHoldingsWidget";
import { WatchlistSection } from "@/components/WatchlistSection";

interface HoldingRow {
  id: number;
  ticker: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number | null;
  market_value: number | null;
  market_value_krw: number | null;
  pnl_amount: number | null;
  pnl_rate: number | null;
  day_change_rate: number | null;
  w52_high: number | null;
  w52_low: number | null;
  currency: "KRW" | "USD";
  portfolio_name: string | null;
}

interface AllocationItem {
  ticker: string;
  name: string;
  value: number;
  ratio: number;
}

interface PortfolioListProps {
  holdings: HoldingRow[];
  allocation: AllocationItem[];
  totalAsset: number;
}

interface WidgetErrorFallbackProps {
  title: string;
  error: Error;
  reset: () => void;
}

function WidgetErrorFallback({ title, error, reset }: WidgetErrorFallbackProps) {
  return (
    <section className="space-y-2">
      <h2 className="text-section-header">{title}</h2>
      <div
        role="alert"
        className="flex items-center justify-between rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3"
      >
        <p className="text-sm text-destructive">
          {title} 위젯을 불러오는 중 오류가 발생했습니다.
          {process.env.NODE_ENV !== "production" && (
            <span className="ml-1 text-muted-foreground">{error.message}</span>
          )}
        </p>
        <button
          onClick={reset}
          className="ml-4 shrink-0 rounded px-2 py-1 text-xs font-medium text-destructive hover:bg-destructive/10"
        >
          다시 시도
        </button>
      </div>
    </section>
  );
}

export function PortfolioList({ holdings, allocation, totalAsset }: PortfolioListProps) {
  return (
    <>
      {/* 수익 상위 3종목 위젯 */}
      {holdings.length > 0 && (
        <div
          className="animate-in fade-in slide-in-from-bottom-2 duration-500"
          style={{ animationDelay: "200ms", animationFillMode: "both" }}
        >
          <TopHoldingsWidget holdings={holdings} />
        </div>
      )}

      {/* 자산 배분 도넛 차트 */}
      {allocation.length > 0 && (
        <ErrorBoundary
          fallback={(err, reset) => (
            <WidgetErrorFallback title="자산 배분" error={err} reset={reset} />
          )}
        >
          <section
            className="space-y-3 animate-in fade-in slide-in-from-bottom-2 duration-500"
            style={{ animationDelay: "300ms", animationFillMode: "both" }}
          >
            <h2 className="text-section-header">자산 배분</h2>
            <AllocationDonut data={allocation} totalAsset={totalAsset} />
          </section>
        </ErrorBoundary>
      )}

      {/* 관심 종목 */}
      <ErrorBoundary
        fallback={(err, reset) => (
          <WidgetErrorFallback title="관심 종목" error={err} reset={reset} />
        )}
      >
        <WatchlistSection />
      </ErrorBoundary>

      {/* 보유 종목 테이블 */}
      <ErrorBoundary
        fallback={(err, reset) => (
          <WidgetErrorFallback title="보유 종목" error={err} reset={reset} />
        )}
      >
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-section-header">보유 종목</h2>
            {holdings.length === 0 && (
              <Link
                href="/dashboard/portfolios"
                className="flex items-center gap-1 text-sm text-primary hover:underline"
              >
                <Plus className="h-3.5 w-3.5" />
                종목 추가하기
              </Link>
            )}
          </div>
          <HoldingsTable holdings={holdings} />
        </section>
      </ErrorBoundary>
    </>
  );
}
