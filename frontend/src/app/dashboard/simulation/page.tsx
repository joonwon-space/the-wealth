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
import { ScenarioTabs } from "./ScenarioTabs";
import {
  buildRows,
  computeDerived,
  newScenario,
  storeToAPI,
  storeFromAPI,
  type ScenarioStore,
} from "./SimulationEngine";
import type {
  SimulationMeta,
  SimulationDataMultiAPI,
  Scenario,
} from "./types";

const QUERY_KEY = ["simulation", "params"] as const;
const EMPTY_STATE_MSG = "메타를 입력하고 [행 생성]을 눌러주세요";

function defaultStore(): ScenarioStore {
  const s = newScenario("기본");
  return { scenarios: [s], activeId: s.id };
}

export default function SimulationPage() {
  const queryClient = useQueryClient();

  // 서버에서 저장된 시나리오 목록 로드
  const { data: savedData, isLoading } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const res = await api.get<SimulationDataMultiAPI | null>(
        "/users/me/simulation-params",
      );
      return res.data ?? null;
    },
    staleTime: 60_000,
  });

  // 서버 데이터 → camelCase store
  const savedStore = useMemo<ScenarioStore | null>(() => {
    if (!savedData) return null;
    try {
      return storeFromAPI(savedData);
    } catch {
      return null;
    }
  }, [savedData]);

  // 로컬 오버라이드 (편집 중인 시나리오 + 활성 ID)
  const [storeOverride, setStoreOverride] = useState<ScenarioStore | null>(
    null,
  );

  const store = storeOverride ?? savedStore ?? defaultStore();
  const dirty = storeOverride !== null;

  const active =
    store.scenarios.find((s) => s.id === store.activeId) ??
    store.scenarios[0]!;

  // 헬퍼: store 전체를 업데이트하고 dirty 표시
  const updateStore = useCallback(
    (updater: (prev: ScenarioStore) => ScenarioStore) => {
      setStoreOverride((prev) => updater(prev ?? savedStore ?? defaultStore()));
    },
    [savedStore],
  );

  // 활성 시나리오만 patch
  const patchActive = useCallback(
    (patch: Partial<Scenario>) => {
      updateStore((prev) => ({
        ...prev,
        scenarios: prev.scenarios.map((s) =>
          s.id === prev.activeId ? { ...s, ...patch } : s,
        ),
      }));
    },
    [updateStore],
  );

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = storeToAPI(store);
      await api.put("/users/me/simulation-params", payload);
      return payload;
    },
    onSuccess: (payload) => {
      queryClient.setQueryData<SimulationDataMultiAPI>(QUERY_KEY, payload);
      setStoreOverride(null);
      toast.success("시뮬레이션을 저장했습니다");
    },
    onError: () => {
      toast.error("저장에 실패했습니다. 다시 시도해주세요");
    },
  });

  // ── 메타 / 행 핸들러 ──────────────────────────────────────────
  const handleMetaChange = useCallback(
    (newMeta: SimulationMeta) => {
      patchActive({ meta: newMeta });
    },
    [patchActive],
  );

  const handleGenerate = useCallback(() => {
    patchActive({ rows: buildRows(active.meta) });
  }, [active.meta, patchActive]);

  const updateRow = useCallback(
    (age: number, patch: { flow?: number; rate?: number }) => {
      updateStore((prev) => ({
        ...prev,
        scenarios: prev.scenarios.map((s) =>
          s.id === prev.activeId
            ? {
                ...s,
                rows: s.rows.map((r) =>
                  r.age === age ? { ...r, ...patch } : r,
                ),
              }
            : s,
        ),
      }));
    },
    [updateStore],
  );

  // ── 시나리오 탭 핸들러 ────────────────────────────────────────
  const handleSelectTab = useCallback(
    (id: string) => {
      updateStore((prev) => ({ ...prev, activeId: id }));
    },
    [updateStore],
  );

  const handleAddScenario = useCallback(() => {
    updateStore((prev) => {
      const next = newScenario(`시나리오 ${prev.scenarios.length + 1}`);
      return {
        scenarios: [...prev.scenarios, next],
        activeId: next.id,
      };
    });
  }, [updateStore]);

  const handleRenameScenario = useCallback(
    (id: string, name: string) => {
      updateStore((prev) => ({
        ...prev,
        scenarios: prev.scenarios.map((s) =>
          s.id === id ? { ...s, name } : s,
        ),
      }));
    },
    [updateStore],
  );

  const handleDeleteScenario = useCallback(
    (id: string) => {
      updateStore((prev) => {
        const remaining = prev.scenarios.filter((s) => s.id !== id);
        if (remaining.length === 0) return prev; // 안전장치
        const nextActive =
          prev.activeId === id ? remaining[0]!.id : prev.activeId;
        return { scenarios: remaining, activeId: nextActive };
      });
    },
    [updateStore],
  );

  const derived = useMemo(
    () => computeDerived(active.rows, active.meta.initialBalance),
    [active.rows, active.meta.initialBalance],
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

      {/* Scenario tabs */}
      {isLoading ? (
        <Skeleton className="h-10 rounded-lg" />
      ) : (
        <ScenarioTabs
          scenarios={store.scenarios}
          activeId={active.id}
          onSelect={handleSelectTab}
          onAdd={handleAddScenario}
          onRename={handleRenameScenario}
          onDelete={handleDeleteScenario}
        />
      )}

      {/* Meta form (active scenario) */}
      {isLoading ? (
        <Skeleton className="h-52 rounded-lg" />
      ) : (
        <SimulationMetaForm
          meta={active.meta}
          onChange={handleMetaChange}
          onGenerate={handleGenerate}
        />
      )}

      {/* Table */}
      {derived.length === 0 ? (
        <div className="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
          {EMPTY_STATE_MSG}
        </div>
      ) : (
        <SimulationTable
          rows={derived}
          retireAge={active.meta.retireAge}
          onUpdateRow={updateRow}
        />
      )}
    </div>
  );
}
