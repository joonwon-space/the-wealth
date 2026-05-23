"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CalendarRange } from "lucide-react";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AnnualSummaryCards } from "./AnnualSummaryCards";
import { AnnualReturnsTable } from "./AnnualReturnsTable";
import { AnnualReturnsChart } from "./AnnualReturnsChart";
import { SimulationForm } from "./SimulationForm";
import { SimulationResult } from "./SimulationResult";
import { BirthYearDialog } from "./BirthYearDialog";
import type {
  AnnualReturnRow,
  SimulationInput,
  SimulationPoint,
} from "./types";

interface UserMe {
  id: number;
  email: string;
  birth_year: number | null;
  simulation_params: SimulationInput | null;
}

export default function AnnualReturnsPage() {
  const [birthDialogDismissed, setBirthDialogDismissed] = useState(false);
  const [simPoints, setSimPoints] = useState<SimulationPoint[]>([]);
  const [retirementAgeUsed, setRetirementAgeUsed] = useState<number>(60);

  const {
    data: me,
    isLoading: meLoading,
    refetch: refetchMe,
  } = useQuery<UserMe>({
    queryKey: ["users", "me"],
    queryFn: () => api.get<UserMe>("/users/me").then((r) => r.data),
    staleTime: 60_000,
  });

  const {
    data: rows = [],
    isLoading: rowsLoading,
  } = useQuery<AnnualReturnRow[]>({
    queryKey: ["analytics", "annual-returns"],
    queryFn: () =>
      api.get<AnnualReturnRow[]>("/analytics/annual-returns").then((r) => r.data),
    staleTime: 3_600_000,
  });

  const birthDialogOpen =
    !meLoading && me != null && me.birth_year == null && !birthDialogDismissed;

  const simMutation = useMutation({
    mutationFn: (params: SimulationInput) =>
      api
        .post<SimulationPoint[]>("/analytics/retirement-simulation", params)
        .then((r) => r.data),
    onSuccess: (data, vars) => {
      setSimPoints(data);
      setRetirementAgeUsed(vars.retirement_age);
    },
  });

  const initialFormState = useMemo<Partial<SimulationInput>>(() => {
    if (me?.simulation_params) return me.simulation_params;
    const latestEop = rows.length > 0 ? rows[rows.length - 1].eop_value_krw : 0;
    const currentAge =
      me?.birth_year ? new Date().getFullYear() - me.birth_year : 30;
    return {
      current_value_krw: latestEop,
      current_age: currentAge,
    };
  }, [me, rows]);

  return (
    <div className="space-y-8">
      <header className="flex items-center gap-2">
        <CalendarRange className="size-5" />
        <h1 className="text-xl font-semibold">연간 수익률</h1>
      </header>

      <ErrorBoundary>
        {rowsLoading ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-20 rounded-lg" />
            ))}
          </div>
        ) : (
          <AnnualSummaryCards rows={rows} />
        )}
      </ErrorBoundary>

      <section className="space-y-3">
        <h2 className="text-base font-semibold">연도별 추이</h2>
        {rowsLoading ? (
          <Skeleton className="h-[280px] rounded-lg" />
        ) : (
          <>
            <AnnualReturnsChart rows={rows} />
            <AnnualReturnsTable rows={rows} />
          </>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold">은퇴 시뮬레이션</h2>
        <SimulationForm
          initial={initialFormState}
          onRun={(p) => simMutation.mutate(p)}
          running={simMutation.isPending}
        />
        <SimulationResult points={simPoints} retirementAge={retirementAgeUsed} />
      </section>

      <BirthYearDialog
        open={birthDialogOpen}
        onClose={() => setBirthDialogDismissed(true)}
        onSaved={() => {
          setBirthDialogDismissed(true);
          refetchMe();
        }}
      />
    </div>
  );
}
