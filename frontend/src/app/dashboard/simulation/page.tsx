"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CalendarRange, Save } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { SimulationMetaForm } from "./SimulationMetaForm";
import { SimulationSummary } from "./SimulationSummary";
import { SimulationChart } from "./SimulationChart";
import { SimulationTable } from "./SimulationTable";
import {
  buildRows,
  computeDerived,
  summarize,
  DEFAULT_META,
  metaToAPI,
  metaFromAPI,
} from "./SimulationEngine";
import type { SimulationMeta, SimulationRow, SimulationDataAPI } from "./types";

const EMPTY_STATE_MSG = "메타를 입력하고 [행 생성]을 눌러주세요";

export default function SimulationPage() {
  const [meta, setMeta] = useState<SimulationMeta>(DEFAULT_META);
  const [rows, setRows] = useState<SimulationRow[]>([]);
  const [dirty, setDirty] = useState(false);

  // Load saved params on mount
  const { data: savedData, isLoading } = useQuery({
    queryKey: ["simulation", "params"],
    queryFn: async () => {
      const res = await api.get<SimulationDataAPI | null>(
        "/users/me/simulation-params",
      );
      return res.data;
    },
    staleTime: 60_000,
  });

  // Apply saved data when it loads (TanStack Query v5: no onSuccess)
  useEffect(() => {
    if (!savedData) return;
    try {
      const parsed = metaFromAPI(savedData);
      setMeta(parsed.meta);
      if (parsed.rows.length > 0) setRows(parsed.rows);
    } catch {
      // Ignore malformed saved data
    }
  }, [savedData]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = metaToAPI(meta, rows);
      await api.put("/users/me/simulation-params", payload);
    },
    onSuccess: () => {
      setDirty(false);
      toast.success("시뮬레이션을 저장했습니다");
    },
    onError: () => {
      toast.error("저장에 실패했습니다. 다시 시도해주세요");
    },
  });

  const handleGenerate = useCallback(() => {
    setRows(buildRows(meta));
    setDirty(true);
  }, [meta]);

  const handleMetaChange = useCallback((newMeta: SimulationMeta) => {
    setMeta(newMeta);
    setDirty(true);
  }, []);

  const updateRow = useCallback(
    (age: number, patch: { flow?: number; rate?: number }) => {
      setRows((prev) =>
        prev.map((r) => (r.age === age ? { ...r, ...patch } : r)),
      );
      setDirty(true);
    },
    [],
  );

  const derived = useMemo(
    () => computeDerived(rows, meta.initialBalance),
    [rows, meta.initialBalance],
  );
  const summary = useMemo(
    () => summarize(derived, meta.retireAge),
    [derived, meta.retireAge],
  );

  return (
    <div className="space-y-5">
      {/* Header */}
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
            <CalendarRange className="h-[18px] w-[18px] text-muted-foreground" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">계획 / 시뮬레이션</p>
            <h1 className="text-xl font-bold tracking-tight">자산 시뮬레이션</h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {dirty && (
            <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
              <span className="h-1.5 w-1.5 rounded-full bg-current" />
              변경됨
            </span>
          )}
          <Button
            size="sm"
            variant={dirty ? "default" : "outline"}
            disabled={!dirty || saveMutation.isPending}
            onClick={() => saveMutation.mutate()}
          >
            <Save className="h-3.5 w-3.5" />
            저장
          </Button>
        </div>
      </header>

      {/* Meta form */}
      {isLoading ? (
        <Skeleton className="h-52 rounded-lg" />
      ) : (
        <SimulationMetaForm
          meta={meta}
          onChange={handleMetaChange}
          onGenerate={handleGenerate}
        />
      )}

      {/* Content: summary + chart + table (only when rows exist) */}
      {derived.length === 0 ? (
        <div className="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
          {EMPTY_STATE_MSG}
        </div>
      ) : (
        <>
          {summary && (
            <SimulationSummary summary={summary} retireAge={meta.retireAge} />
          )}
          <SimulationChart data={derived} retireAge={meta.retireAge} />
          <SimulationTable
            rows={derived}
            retireAge={meta.retireAge}
            onUpdateRow={updateRow}
          />
        </>
      )}
    </div>
  );
}
