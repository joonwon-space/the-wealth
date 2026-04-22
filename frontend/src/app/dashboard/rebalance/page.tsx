"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Save, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { SectorBar } from "@/components/sector-bar";
import { formatKRW } from "@/lib/format";

interface PortfolioSummary {
  id: number;
  name: string;
  target_value: number | null;
}

interface RebalanceCandidate {
  ticker: string;
  name: string;
  weight_in_sector: number;
  suggested_qty: number;
  suggested_action: "BUY" | "SELL";
}

interface RebalanceRow {
  sector: string;
  current_pct: number;
  target_pct: number;
  diff_pct: number;
  delta_krw: number;
  suggested_action: "BUY" | "SELL" | "HOLD";
  candidates: RebalanceCandidate[];
}

interface RebalanceResponse {
  portfolio_id: number;
  total_value_krw: number;
  rows: RebalanceRow[];
}

interface TargetAllocationResponse {
  portfolio_id: number;
  target_allocation: Record<string, number> | null;
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

export default function RebalancePage() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const portfolioIdFromQuery = Number(searchParams.get("portfolio") || 0);

  const { data: portfolios } = useQuery<PortfolioSummary[]>({
    queryKey: ["portfolios", "summaries"],
    queryFn: async () => (await api.get<PortfolioSummary[]>("/portfolios")).data,
    staleTime: 60_000,
  });

  const [portfolioId, setPortfolioId] = useState(portfolioIdFromQuery);
  useEffect(() => {
    if (portfolioId === 0 && portfolios && portfolios.length > 0) {
      setPortfolioId(portfolios[0]!.id);
    }
  }, [portfolios, portfolioId]);

  const activePortfolio = portfolios?.find((p) => p.id === portfolioId);

  const { data: rebalance } = useQuery<RebalanceResponse>({
    queryKey: ["portfolios", portfolioId, "rebalance"],
    queryFn: async () =>
      (
        await api.get<RebalanceResponse>(
          `/portfolios/${portfolioId}/rebalance-suggestion`,
        )
      ).data,
    enabled: portfolioId > 0,
    staleTime: 2 * 60_000,
  });

  const { data: saved } = useQuery<TargetAllocationResponse>({
    queryKey: ["portfolios", portfolioId, "target-allocation"],
    queryFn: async () =>
      (
        await api.get<TargetAllocationResponse>(
          `/portfolios/${portfolioId}/target-allocation`,
        )
      ).data,
    enabled: portfolioId > 0,
  });

  const [drafts, setDrafts] = useState<Record<string, number>>({});
  useEffect(() => {
    if (saved?.target_allocation) {
      setDrafts(saved.target_allocation);
    } else if (rebalance) {
      // 저장된 목표가 없으면 현재 비중을 초기값으로 제시
      const next: Record<string, number> = {};
      rebalance.rows.forEach((r) => {
        next[r.sector] = Math.round(r.current_pct * 100) / 100;
      });
      setDrafts(next);
    }
  }, [saved, rebalance]);

  const total = useMemo(
    () => Object.values(drafts).reduce((sum, v) => sum + v, 0),
    [drafts],
  );

  const save = useMutation({
    mutationFn: async () => {
      const payload = { target_allocation: drafts };
      await api.put(`/portfolios/${portfolioId}/target-allocation`, payload);
    },
    onSuccess: () => {
      toast.success("목표 비중이 저장되었습니다.");
      queryClient.invalidateQueries({
        queryKey: ["portfolios", portfolioId, "target-allocation"],
      });
      queryClient.invalidateQueries({
        queryKey: ["portfolios", portfolioId, "rebalance"],
      });
    },
    onError: () => toast.error("저장에 실패했습니다."),
  });

  if (!portfolios) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
    );
  }

  if (portfolios.length === 0) {
    return (
      <div className="space-y-4">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" /> 대시보드
        </Link>
        <Card>
          <CardContent className="p-6 text-center text-sm text-muted-foreground">
            포트폴리오를 먼저 만들어주세요.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Link
          href={portfolioId > 0 ? `/dashboard/portfolios/${portfolioId}` : "/dashboard"}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3" />
          {activePortfolio?.name || "대시보드"}
        </Link>
        <h1 className="text-2xl font-bold tracking-tight">리밸런싱</h1>
        <p className="text-sm text-muted-foreground">
          포트폴리오의 섹터 목표 비중을 조정하면 제안 주문이 자동으로 업데이트됩니다.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card p-2">
        {portfolios.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => setPortfolioId(p.id)}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold ${
              p.id === portfolioId
                ? "bg-foreground text-background"
                : "text-muted-foreground hover:bg-muted"
            }`}
          >
            {p.name}
          </button>
        ))}
      </div>

      {/* Target editor */}
      <section className="space-y-2">
        <div className="flex items-baseline justify-between">
          <h2 className="text-section-header">목표 비중 (합계 {Math.round(total * 100)}%)</h2>
          <Badge tone={Math.abs(total - 1) < 0.01 ? "ok" : "warn"}>
            {Math.abs(total - 1) < 0.01 ? "100% 일치" : "100% 와 다름"}
          </Badge>
        </div>
        <Card>
          <CardContent className="space-y-4 p-4">
            {Object.keys(drafts).length === 0 && (
              <p className="text-sm text-muted-foreground">
                목표 비중이 없습니다. 보유 섹터가 있으면 현재 비중이 초기값으로 채워집니다.
              </p>
            )}
            {Object.entries(drafts).map(([sector, value], i) => (
              <div key={sector} className="space-y-1.5">
                <div className="flex items-center gap-3 text-sm">
                  <span className="w-20 font-semibold">{sector}</span>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.01}
                    value={value}
                    onChange={(e) =>
                      setDrafts((prev) => ({
                        ...prev,
                        [sector]: parseFloat(e.target.value),
                      }))
                    }
                    className="flex-1 accent-[color:var(--primary)]"
                    aria-label={`${sector} 목표 비중`}
                  />
                  <span className="w-14 text-right tabular-nums font-bold">
                    {(value * 100).toFixed(0)}%
                  </span>
                </div>
                <SectorBar
                  sector={sector}
                  pct={
                    rebalance?.rows.find((r) => r.sector === sector)
                      ?.current_pct ?? value
                  }
                  target={value}
                  color={SECTOR_COLORS[i % SECTOR_COLORS.length]}
                />
              </div>
            ))}
          </CardContent>
        </Card>
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => save.mutate()}
            disabled={save.isPending || portfolioId === 0}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            <Save className="size-4" />
            {save.isPending ? "저장 중..." : "저장"}
          </button>
        </div>
      </section>

      {/* Suggested orders */}
      <section className="space-y-2">
        <h2 className="text-section-header">제안 주문</h2>
        <Card>
          <CardContent className="p-4">
            {!rebalance ||
            !rebalance.rows.some((r) => r.suggested_action !== "HOLD") ? (
              <div className="flex flex-col items-center gap-2 py-6 text-center">
                <Sparkles className="size-6 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">
                  조정이 필요한 섹터가 없습니다. (임계치 3% 이내)
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {rebalance.rows
                  .filter((r) => r.suggested_action !== "HOLD")
                  .map((r) => (
                    <div key={r.sector} className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-semibold">{r.sector}</span>
                        <Badge
                          tone={r.suggested_action === "SELL" ? "rise" : "fall"}
                          solid
                        >
                          {r.suggested_action === "SELL" ? "매도" : "매수"}
                          {" "}
                          {formatKRW(Math.abs(r.delta_krw))}
                        </Badge>
                      </div>
                      {r.candidates.length > 0 && (
                        <div className="grid grid-cols-1 gap-1.5 text-xs">
                          {r.candidates.map((c) => (
                            <div
                              key={c.ticker}
                              className="flex items-center justify-between rounded-md bg-muted/40 px-3 py-2"
                            >
                              <div className="flex flex-col">
                                <span className="font-semibold">{c.name}</span>
                                <span className="text-muted-foreground tabular-nums">
                                  {c.ticker} · 섹터 내 비중{" "}
                                  {(c.weight_in_sector * 100).toFixed(0)}%
                                </span>
                              </div>
                              <div
                                className={`text-right tabular-nums font-bold ${
                                  c.suggested_action === "SELL"
                                    ? "text-rise"
                                    : "text-fall"
                                }`}
                              >
                                {c.suggested_action === "SELL" ? "매도 " : "매수 "}
                                {c.suggested_qty.toFixed(2)}주
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
