"use client";

import { useState } from "react";
import { Check, Download, Loader2, Pencil, RefreshCw, Target, X } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatKRW } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { PendingOrdersPanel } from "@/components/PendingOrdersPanel";
import { toast } from "sonner";

interface PortfolioInfo {
  id: number;
  name: string;
  currency: string;
  kis_account_id: number | null;
  target_value: number | null;
}

interface Holding {
  id: number;
  market_value_krw: string | null;
}

interface PortfolioHeaderProps {
  portfolioId: number;
  holdings: Holding[];
  isKisConnected: boolean;
  pendingOrdersCount: number;
  showPendingOrders: boolean;
  onTogglePendingOrders: () => void;
}

export function PortfolioHeader({
  portfolioId,
  holdings,
  isKisConnected,
  pendingOrdersCount,
  showPendingOrders,
  onTogglePendingOrders,
}: PortfolioHeaderProps) {
  const queryClient = useQueryClient();
  const [isExporting, setIsExporting] = useState(false);
  const [editingTarget, setEditingTarget] = useState(false);
  const [targetInputValue, setTargetInputValue] = useState("");
  const [isSyncing, setIsSyncing] = useState(false);

  const { data: portfolioInfo } = useQuery<PortfolioInfo>({
    queryKey: ["portfolio", portfolioId],
    queryFn: async () => {
      const { data } = await api.get<PortfolioInfo[]>("/portfolios");
      return data.find((p) => p.id === portfolioId) ?? { id: portfolioId, name: "", currency: "KRW", kis_account_id: null, target_value: null };
    },
    staleTime: 60_000,
  });

  const updateTargetMutation = useMutation({
    mutationFn: (target_value: number | null) =>
      api.patch(`/portfolios/${portfolioId}`, { target_value }).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portfolio", portfolioId] });
      setEditingTarget(false);
    },
    onError: () => {
      toast.error("목표 금액 설정에 실패했습니다. 잠시 후 다시 시도해주세요.");
    },
  });

  const handleKisSync = async () => {
    setIsSyncing(true);
    try {
      const { data } = await api.post<{ inserted: number; updated: number; deleted: number }>(
        `/sync/${portfolioId}`
      );
      await queryClient.invalidateQueries({ queryKey: ["portfolios", portfolioId, "holdings"] });
      const total = data.inserted + data.updated + data.deleted;
      toast.success(total > 0 ? `동기화 완료 (+${data.inserted} ~${data.updated} -${data.deleted})` : "이미 최신 상태입니다");
    } catch {
      toast.error("동기화에 실패했습니다. 잠시 후 다시 시도해주세요.");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleTargetSave = () => {
    const raw = targetInputValue.trim().replace(/,/g, "");
    if (raw === "") {
      updateTargetMutation.mutate(null);
    } else {
      const parsed = parseInt(raw, 10);
      if (!isNaN(parsed) && parsed >= 0) {
        updateTargetMutation.mutate(parsed);
      }
    }
  };

  const downloadCsv = async (path: string, filename: string) => {
    if (isExporting) return;
    setIsExporting(true);
    try {
      const response = await api.get<string>(path, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([response.data], { type: "text/csv" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("파일 내보내기에 실패했습니다");
    } finally {
      setIsExporting(false);
    }
  };

  const downloadXlsx = async () => {
    if (isExporting) return;
    setIsExporting(true);
    try {
      const response = await api.get<Blob>(`/portfolios/${portfolioId}/export/xlsx`, {
        responseType: "blob",
      });
      const mimeType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
      const today = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      const url = URL.createObjectURL(new Blob([response.data], { type: mimeType }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `portfolio_${portfolioId}_${today}.xlsx`;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("엑셀 내보내기에 실패했습니다");
    } finally {
      setIsExporting(false);
    }
  };

  const totalCurrentKrw = holdings.reduce(
    (sum, h) => sum + Number(h.market_value_krw ?? 0),
    0
  );
  const targetValue = portfolioInfo?.target_value ?? null;
  const progress = targetValue && targetValue > 0
    ? Math.min((totalCurrentKrw / targetValue) * 100, 100)
    : 0;
  const isAchieved = targetValue != null && totalCurrentKrw >= targetValue;

  return (
    <>
      {/* Export + sync buttons */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">보유 종목</h1>
        <div className="flex gap-2 flex-wrap justify-end">
          {isKisConnected && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={onTogglePendingOrders}
                className="gap-2"
              >
                미체결 주문
                {pendingOrdersCount > 0 && (
                  <span className="ml-1 rounded-full bg-rise px-1.5 text-[10px] text-white">
                    {pendingOrdersCount}
                  </span>
                )}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleKisSync}
                disabled={isSyncing}
                className="gap-2"
              >
                <RefreshCw className={`h-4 w-4 ${isSyncing ? "animate-spin" : ""}`} />
                {isSyncing ? "동기화 중..." : "동기화"}
              </Button>
            </>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => downloadCsv(`/portfolios/${portfolioId}/export/csv`, `holdings_portfolio_${portfolioId}.csv`)}
            disabled={isExporting}
            className="gap-2"
          >
            {isExporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            보유 CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => downloadCsv(`/portfolios/${portfolioId}/transactions/export/csv`, `transactions_portfolio_${portfolioId}.csv`)}
            disabled={isExporting}
            className="gap-2"
          >
            {isExporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            거래 CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={downloadXlsx}
            disabled={isExporting}
            className="gap-2"
          >
            {isExporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            Excel
          </Button>
        </div>
      </div>

      {/* Pending orders panel */}
      {isKisConnected && showPendingOrders && (
        <div className="rounded-lg border p-4">
          <PendingOrdersPanel portfolioId={portfolioId} />
        </div>
      )}

      {/* Target progress widget */}
      {(() => {
        if (!targetValue && !editingTarget) {
          return (
            <button
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => { setTargetInputValue(""); setEditingTarget(true); }}
            >
              <Target className="h-3.5 w-3.5" />
              목표 금액 설정
            </button>
          );
        }
        return (
          <div className="rounded-lg border p-4 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Target className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">목표 달성률</span>
                {isAchieved && (
                  <span
                    className="text-xs rounded-full px-2 py-0.5"
                    style={{
                      background: "color-mix(in oklch, var(--chart-8) 15%, transparent)",
                      color: "var(--chart-8)",
                    }}
                  >
                    달성!
                  </span>
                )}
              </div>
              {editingTarget ? (
                <div className="flex items-center gap-1">
                  <input
                    type="text"
                    className="h-7 w-36 rounded border px-2 text-xs tabular-nums"
                    placeholder="목표 금액 (원)"
                    value={targetInputValue}
                    onChange={(e) => setTargetInputValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleTargetSave();
                      if (e.key === "Escape") setEditingTarget(false);
                    }}
                    autoFocus
                  />
                  <button
                    onClick={handleTargetSave}
                    disabled={updateTargetMutation.isPending}
                    className="p-1 text-primary hover:opacity-80"
                  >
                    <Check className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => setEditingTarget(false)}
                    className="p-1 text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => {
                    setTargetInputValue(targetValue ? String(targetValue) : "");
                    setEditingTarget(true);
                  }}
                  className="p-1 text-muted-foreground hover:text-foreground"
                  aria-label="목표 금액 편집"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
            {targetValue != null && (
              <>
                <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${progress}%`,
                      background: isAchieved ? "var(--color-green-500, #22c55e)" : "var(--accent-indigo, #6366F1)",
                    }}
                  />
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span className="tabular-nums">{formatKRW(totalCurrentKrw)}</span>
                  <span className="tabular-nums font-medium" style={{ color: isAchieved ? "#22c55e" : undefined }}>
                    {progress.toFixed(1)}% / {formatKRW(targetValue)}
                  </span>
                </div>
              </>
            )}
          </div>
        );
      })()}
    </>
  );
}
