"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import type { SimulationMeta } from "./types";
import { DEFAULT_META } from "./SimulationEngine";

interface Props {
  meta: SimulationMeta;
  onChange: (meta: SimulationMeta) => void;
  onGenerate: () => void;
}

interface FieldConfig {
  label: string;
  fieldKey: keyof SimulationMeta;
  suffix?: string;
}

const FIELDS: FieldConfig[] = [
  { label: "현재 나이", fieldKey: "currentAge", suffix: "세" },
  { label: "시작 연도", fieldKey: "startYear" },
  { label: "종료 나이", fieldKey: "endAge", suffix: "세" },
  { label: "은퇴 나이", fieldKey: "retireAge", suffix: "세" },
  { label: "초기 잔고", fieldKey: "initialBalance", suffix: "원" },
  { label: "연 적립액", fieldKey: "contribution", suffix: "원" },
  { label: "연 인출액", fieldKey: "withdrawal", suffix: "원" },
  { label: "기본 수익률", fieldKey: "defaultRate", suffix: "%" },
];

export function SimulationMetaForm({ meta, onChange, onGenerate }: Props) {
  const [confirmOpen, setConfirmOpen] = useState(false);

  const update = (key: keyof SimulationMeta, raw: string) => {
    const v = raw.replace(/[^\d.-]/g, "");
    const n = v === "" || v === "-" ? 0 : Number(v);
    if (isFinite(n)) onChange({ ...meta, [key]: n });
  };

  const yearCount = meta.endAge - meta.currentAge + 1;

  return (
    <>
      <Card className="shadow-none">
        <CardHeader className="pb-3 pt-4 px-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold">입력 메타</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                8개 값을 입력하고 [행 생성]을 누르면 표가 채워집니다
              </p>
            </div>
            <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
              {yearCount}개년
            </span>
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {FIELDS.map(({ label, fieldKey, suffix }) => (
              <div key={fieldKey} className="space-y-1.5">
                <label
                  htmlFor={`sim-field-${fieldKey}`}
                  className="block text-xs font-medium"
                >
                  {label}
                </label>
                <div className="relative">
                  <Input
                    id={`sim-field-${fieldKey}`}
                    type="text"
                    inputMode="numeric"
                    value={(meta[fieldKey] as number).toLocaleString("ko-KR")}
                    onChange={(e) => update(fieldKey, e.target.value)}
                    className={suffix ? "pr-8" : ""}
                  />
                  {suffix && (
                    <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                      {suffix}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onChange(DEFAULT_META)}
            >
              초기값
            </Button>
            <Button size="sm" onClick={() => setConfirmOpen(true)}>
              행 생성
            </Button>
          </div>
        </CardContent>
      </Card>

      <AlertDialog
        open={confirmOpen}
        onOpenChange={(open) => {
          if (!open) setConfirmOpen(false);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>기존 행을 덮어쓰시겠습니까?</AlertDialogTitle>
            <AlertDialogDescription>
              메타 값으로 {yearCount}개 행을 다시 생성합니다. 셀에서 편집한 값은
              모두 초기화됩니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                onGenerate();
                setConfirmOpen(false);
              }}
            >
              덮어쓰기
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
