"use client";

import { useCallback, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarRange, Save } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { SimulationMetaForm } from "./SimulationMetaForm";
import { SimulationTable } from "./SimulationTable";
import {
  buildRows,
  computeDerived,
  DEFAULT_META,
  metaToAPI,
  metaFromAPI,
} from "./SimulationEngine";
import type { SimulationMeta, SimulationRow, SimulationDataAPI } from "./types";

const QUERY_KEY = ["simulation", "params"] as const;
const EMPTY_STATE_MSG = "메타를 입력하고 [행 생성]을 눌러주세요";

export default function SimulationPage() {
  const queryClient = useQueryClient();

  // Load saved params from server — source of truth when no local overrides
  const { data: savedData, isLoading } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const res = await api.get<SimulationDataAPI | null>(
        "/users/me/simulation-params",
      );
      return res.data ?? null;
    },
    staleTime: 60_000,
  });

  // Parse saved data once — no useEffect + setState needed
  const savedParsed = useMemo(() => {
    if (!savedData) return null;
    try {
      return metaFromAPI(savedData);
    } catch {
      return null;
    }
  }, [savedData]);

  // Local overrides — null means "use server data"
  const [metaOverride, setMetaOverride] = useState<SimulationMeta | null>(null);
  const [rowsOverride, setRowsOverride] = useState<SimulationRow[] | null>(null);

  // Effective values: local edit > saved > default (memoized for stable refs)
  const meta = useMemo(
    () => metaOverride ?? savedParsed?.meta ?? DEFAULT_META,
    [metaOverride, savedParsed],
  );
  const rows = useMemo(
    () => rowsOverride ?? savedParsed?.rows ?? [],
    [rowsOverride, savedParsed],
  );

  // Dirty when local overrides exist
  const dirty = metaOverride !== null || rowsOverride !== null;

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = metaToAPI(meta, rows);
      await api.put("/users/me/simulation-params", payload);
      return payload;
    },
    onSuccess: (payload) => {
      // Update cache so savedParsed reflects saved state, then drop overrides
      queryClient.setQueryData<SimulationDataAPI>(QUERY_KEY, payload);
      setMetaOverride(null);
      setRowsOverride(null);
      toast.success("시뮬레이션을 저장했습니다");
    },
    onError: () => {
      toast.error("저장에 실패했습니다. 다시 시도해주세요");
    },
  });

  const handleGenerate = useCallback(() => {
    setRowsOverride(buildRows(meta));
    // Also lock in current meta so subsequent meta edits don't auto-rebuild
    setMetaOverride(meta);
  }, [meta]);

  const handleMetaChange = useCallback((newMeta: SimulationMeta) => {
    setMetaOverride(newMeta);
  }, []);

  const updateRow = useCallback(
    (age: number, patch: { flow?: number; rate?: number }) => {
      setRowsOverride((prev) => {
        const base = prev ?? savedParsed?.rows ?? [];
        return base.map((r) => (r.age === age ? { ...r, ...patch } : r));
      });
    },
    [savedParsed?.rows],
  );

  const derived = useMemo(
    () => computeDerived(rows, meta.initialBalance),
    [rows, meta.initialBalance],
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

      {/* Table only — 시트와 동일 5컬럼 구조 */}
      {derived.length === 0 ? (
        <div className="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
          {EMPTY_STATE_MSG}
        </div>
      ) : (
        <SimulationTable
          rows={derived}
          retireAge={meta.retireAge}
          onUpdateRow={updateRow}
        />
      )}
    </div>
  );
}
