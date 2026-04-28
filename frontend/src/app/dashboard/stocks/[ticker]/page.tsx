"use client";

import { useEffect, useState, useTransition } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { formatKRW, formatUSD } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PnLBadge } from "@/components/PnLBadge";
import { CandlestickChart } from "@/components/DynamicCharts";
import { ChartSkeleton } from "@/components/ChartSkeleton";
import { RangeIndicator } from "@/components/range-indicator";

const PERIODS = ["1M", "3M", "6M", "1Y", "3Y"] as const;

interface StockDetail {
  ticker: string;
  name?: string | null;
  currency?: "KRW" | "USD";
  market?: string | null;
  usd_krw_rate?: number | null;
  current_price: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  prev_close: number | null;
  volume: number | null;
  day_change_rate: number | null;
  market_cap: number | null;
  per: number | null;
  pbr: number | null;
  eps: number | null;
  bps: number | null;
  w52_high: number | null;
  w52_low: number | null;
  my_holding: { quantity: number; avg_price: number } | null;
  error?: string;
}

interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

function InfoRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex justify-between py-1.5 border-b last:border-0 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="tabular-nums font-medium">{value ?? "—"}</span>
    </div>
  );
}

export default function StockDetailPage() {
  const params = useParams();
  const ticker = typeof params.ticker === "string" ? params.ticker : "";

  const [detail, setDetail] = useState<StockDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [chartError, setChartError] = useState(false);
  const [chartPending, startChartTransition] = useTransition();
  const [period, setPeriod] = useState<(typeof PERIODS)[number]>("3M");

  const loadDetail = () => {
    if (!ticker) return;
    setLoading(true);
    setPageError(null);
    api.get<StockDetail>(`/stocks/${ticker}/detail`)
      .then((r) => setDetail(r.data))
      .catch(() => setPageError("종목 정보를 불러올 수 없습니다. 잠시 후 다시 시도해주세요."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadDetail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  const loadChart = () => {
    if (!ticker) return;
    setChartError(false);
    startChartTransition(async () => {
      await api
        .get<{ candles: Candle[] }>("/chart/daily", {
          params: { ticker, period, ...(detail?.market ? { market: detail.market } : {}) },
        })
        .then((r) => setCandles(r.data.candles))
        .catch(() => setChartError(true));
    });
  };

  useEffect(() => {
    loadChart();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker, period, detail?.market]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-6 w-32" />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}><CardContent className="p-4 space-y-2"><Skeleton className="h-3 w-16" /><Skeleton className="h-5 w-20" /></CardContent></Card>
          ))}
        </div>
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  if (pageError ?? (!detail || detail.error)) {
    return (
      <div className="space-y-4">
        <Link href="/dashboard" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> 돌아가기
        </Link>
        <p className="text-muted-foreground">
          {pageError ?? detail?.error ?? "종목 정보를 불러올 수 없습니다"}
        </p>
        <button
          onClick={loadDetail}
          className="text-sm underline hover:no-underline text-primary"
        >
          다시 시도
        </button>
      </div>
    );
  }

  const isUSD = detail.currency === "USD";
  const fmt = isUSD ? formatUSD : formatKRW;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link href="/dashboard" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-2">
          <ArrowLeft className="h-4 w-4" /> 대시보드
        </Link>
        <div className="flex items-end gap-3 flex-wrap">
          <div>
            <h1 className="text-2xl font-bold">{detail.name || ticker}</h1>
            <p className="text-sm text-muted-foreground">{ticker}{isUSD && detail.market ? ` · ${detail.market}` : ""}</p>
          </div>
          {detail.current_price && (
            <span className="text-xl font-semibold tabular-nums">{fmt(detail.current_price)}</span>
          )}
          {detail.day_change_rate != null && (
            <PnLBadge value={detail.day_change_rate} suffix="%" />
          )}
        </div>
        {isUSD && detail.usd_krw_rate && (
          <p className="mt-1 text-xs text-muted-foreground tabular-nums">
            USD/KRW {formatKRW(detail.usd_krw_rate)}
          </p>
        )}
      </div>

      {/* Key stats */}
      {isUSD && !detail.open && !detail.high && !detail.low && (
        <p className="text-xs text-muted-foreground">미국 장 마감 — 오늘 장 데이터를 아직 수신하지 못했습니다.</p>
      )}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">시가</p><p className="mt-1 font-medium tabular-nums text-sm">{detail.open ? fmt(detail.open) : "—"}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">고가</p><p className="mt-1 font-medium tabular-nums text-sm text-rise">{detail.high ? fmt(detail.high) : "—"}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">저가</p><p className="mt-1 font-medium tabular-nums text-sm text-fall">{detail.low ? fmt(detail.low) : "—"}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">전일 종가</p><p className="mt-1 font-medium tabular-nums text-sm">{detail.prev_close ? fmt(detail.prev_close) : "—"}</p></CardContent></Card>
      </div>

      {/* Candlestick chart */}
      <section className="space-y-3">
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                period === p ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
        {chartPending ? (
          <ChartSkeleton height={400} />
        ) : chartError ? (
          <div className="flex items-center gap-2 h-[400px] justify-center text-sm text-destructive">
            <span>차트 데이터를 불러오지 못했습니다.</span>
            <button
              onClick={loadChart}
              className="underline hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
            >
              다시 시도
            </button>
          </div>
        ) : (
          <CandlestickChart
            candles={candles}
            avgPrice={detail.my_holding?.avg_price}
          />
        )}
      </section>

      {/* Fundamental & 52-week */}
      <div className="grid gap-4 sm:grid-cols-2">
        <section className="space-y-1">
          <h2 className="text-base font-semibold">기본 정보</h2>
          <Card>
            <CardContent className="p-4 divide-y">
              {!isUSD && (
                <InfoRow label="시가총액" value={detail.market_cap ? `${detail.market_cap.toLocaleString("ko-KR")}억` : null} />
              )}
              <InfoRow label="거래량" value={detail.volume ? detail.volume.toLocaleString("ko-KR") : null} />
              <InfoRow label="PER" value={detail.per != null ? `${detail.per.toFixed(2)}배` : null} />
              <InfoRow label="PBR" value={detail.pbr != null ? `${detail.pbr.toFixed(2)}배` : null} />
              <InfoRow label="EPS" value={detail.eps != null ? fmt(detail.eps) : null} />
              {!isUSD && (
                <InfoRow label="BPS" value={detail.bps != null ? fmt(detail.bps) : null} />
              )}
            </CardContent>
          </Card>
        </section>

        <section className="space-y-1">
          <h2 className="text-base font-semibold">52주 범위</h2>
          <Card>
            <CardContent className="p-4">
              {detail.w52_low != null &&
              detail.w52_high != null &&
              detail.current_price != null ? (
                <RangeIndicator
                  low={detail.w52_low}
                  high={detail.w52_high}
                  current={detail.current_price}
                  formatValue={(v) => fmt(v)}
                />
              ) : (
                <p className="text-sm text-muted-foreground">데이터 없음</p>
              )}
            </CardContent>
          </Card>

          {/* 내 보유 현황 */}
          {detail.my_holding && (
            <Card className="mt-3">
              <CardContent className="p-4 divide-y">
                <h3 className="text-sm font-semibold pb-2">내 보유 현황</h3>
                <InfoRow label="수량" value={`${detail.my_holding.quantity.toLocaleString("ko-KR")}주`} />
                <InfoRow label="평균 단가" value={fmt(detail.my_holding.avg_price)} />
                {detail.current_price && (
                  <InfoRow
                    label="평가 손익"
                    value={fmt((detail.current_price - detail.my_holding.avg_price) * detail.my_holding.quantity)}
                  />
                )}
              </CardContent>
            </Card>
          )}
        </section>
      </div>

      {/* Mobile sticky 매수/매도 CTA — 탭바(56px) 위 여유(10px). 데스크탑은 숨김. */}
      <div
        className="fixed inset-x-0 bottom-16 z-30 flex gap-2 border-t bg-background/95 px-4 py-3 backdrop-blur md:hidden"
        style={{ paddingBottom: "calc(env(safe-area-inset-bottom, 0px) + 12px)" }}
      >
        <button
          type="button"
          className="flex-1 rounded-xl bg-rise py-3 text-sm font-bold text-white active:opacity-90"
          onClick={() => {
            // Step 6 의 buy/sell은 기존 OrderDialog 재사용 — 실제 dialog 연결은
            // 포트폴리오 상세의 매수/매도 버튼 패턴을 Step 7 에서 통합한다.
            window.dispatchEvent(new CustomEvent("the-wealth:order", {
              detail: {
                ticker,
                action: "BUY",
                stockName: detail?.name ?? ticker,
                currentPrice: detail?.current_price ?? undefined,
                exchangeCode: detail?.market ?? undefined,
              },
            }));
          }}
          aria-label="매수 주문"
        >
          매수
        </button>
        <button
          type="button"
          className="flex-1 rounded-xl bg-fall py-3 text-sm font-bold text-white active:opacity-90"
          onClick={() => {
            window.dispatchEvent(new CustomEvent("the-wealth:order", {
              detail: {
                ticker,
                action: "SELL",
                stockName: detail?.name ?? ticker,
                currentPrice: detail?.current_price ?? undefined,
                exchangeCode: detail?.market ?? undefined,
              },
            }));
          }}
          aria-label="매도 주문"
        >
          매도
        </button>
      </div>
    </div>
  );
}
