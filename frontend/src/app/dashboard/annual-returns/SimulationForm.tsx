"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { SimulationInput } from "./types";

interface Props {
  initial: Partial<SimulationInput>;
  onRun: (params: SimulationInput) => void;
  running: boolean;
}

const DEFAULTS: SimulationInput = {
  current_value_krw: 0,
  current_age: 30,
  retirement_age: 60,
  end_age: 90,
  annual_contribution_krw: 0,
  annual_withdrawal_krw: 0,
  expected_return_rate: 0.07,
};

interface FieldDef {
  key: keyof SimulationInput;
  label: string;
  step?: number;
  hint?: string;
  isPercent?: boolean;
}

const FIELDS: FieldDef[] = [
  { key: "current_value_krw", label: "현재 평가액 (원)", step: 1_000_000 },
  { key: "current_age", label: "현재 나이", step: 1 },
  { key: "retirement_age", label: "은퇴 나이", step: 1 },
  { key: "end_age", label: "종료 나이", step: 1 },
  { key: "annual_contribution_krw", label: "연 적립액 (원)", step: 100_000 },
  { key: "annual_withdrawal_krw", label: "연 인출액 (원)", step: 100_000 },
  {
    key: "expected_return_rate",
    label: "가정 수익률 (%)",
    step: 0.01,
    isPercent: true,
  },
];

function validate(state: SimulationInput): string | null {
  if (state.current_age < 0 || state.current_age > 120) return "현재 나이가 유효하지 않습니다.";
  if (state.retirement_age < state.current_age) return "은퇴 나이는 현재 나이 이상이어야 합니다.";
  if (state.end_age < state.retirement_age) return "종료 나이는 은퇴 나이 이상이어야 합니다.";
  if (state.current_value_krw < 0) return "현재 평가액은 0 이상이어야 합니다.";
  if (state.annual_contribution_krw < 0) return "연 적립액은 0 이상이어야 합니다.";
  if (state.annual_withdrawal_krw < 0) return "연 인출액은 0 이상이어야 합니다.";
  if (state.expected_return_rate < -0.5 || state.expected_return_rate > 1.0) {
    return "가정 수익률은 -50% ~ 100% 범위여야 합니다.";
  }
  return null;
}

export function SimulationForm({ initial, onRun, running }: Props) {
  const [state, setState] = useState<SimulationInput>({
    ...DEFAULTS,
    ...initial,
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setState((prev) => ({ ...DEFAULTS, ...initial, ...prev }));
  }, [initial]);

  const handleChange = (key: keyof SimulationInput, raw: string, isPercent?: boolean) => {
    const num = Number(raw);
    if (Number.isNaN(num)) return;
    const value = isPercent ? num / 100 : num;
    setState((prev) => ({ ...prev, [key]: value }));
  };

  const handleRun = () => {
    const err = validate(state);
    if (err) {
      toast.error(err);
      return;
    }
    onRun(state);
  };

  const handleSave = async () => {
    const err = validate(state);
    if (err) {
      toast.error(err);
      return;
    }
    setSaving(true);
    try {
      await api.put("/users/me/simulation-params", state);
      toast.success("입력값을 저장했습니다.");
    } catch {
      toast.error("저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardContent className="p-4 space-y-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {FIELDS.map((f) => {
            const raw = state[f.key];
            const display = f.isPercent ? (raw * 100).toFixed(2) : raw;
            return (
              <label key={f.key} className="space-y-1.5 text-sm">
                <span className="text-muted-foreground">{f.label}</span>
                <Input
                  type="number"
                  step={f.step ?? 1}
                  value={display}
                  onChange={(e) => handleChange(f.key, e.target.value, f.isPercent)}
                />
              </label>
            );
          })}
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRun} disabled={running}>
            {running ? "계산 중..." : "시뮬레이션 실행"}
          </Button>
          <Button variant="outline" onClick={handleSave} disabled={saving}>
            {saving ? "저장 중..." : "입력값 저장"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
