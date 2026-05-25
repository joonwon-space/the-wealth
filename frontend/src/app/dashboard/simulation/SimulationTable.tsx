"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { DerivedRow } from "./types";
import { krw, pct } from "./formatters";

interface Props {
  rows: DerivedRow[];
  retireAge: number;
  onUpdateRow: (age: number, patch: { flow?: number; rate?: number }) => void;
}

interface EditableCellProps {
  value: number;
  onCommit: (v: number) => void;
  format: (v: number) => React.ReactNode;
  parse?: (s: string) => number;
  className?: string;
}

function EditableCell({
  value,
  onCommit,
  format,
  parse,
  className,
}: EditableCellProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
      inputRef.current.scrollIntoView({ block: "nearest" });
    }
  }, [editing]);

  const startEdit = () => {
    setDraft(String(value));
    setEditing(true);
  };

  const commit = () => {
    const n = parse ? parse(draft) : Number(draft);
    if (isFinite(n)) onCommit(n);
    setEditing(false);
  };

  const cancel = () => setEditing(false);

  return (
    <td
      onClick={() => {
        if (!editing) startEdit();
      }}
      className={cn(
        "relative cursor-text px-3 py-2 text-right tabular-nums border-b border-border/40",
        "hover:bg-muted/60",
        editing && "!p-0",
        className,
      )}
    >
      {editing ? (
        <input
          ref={inputRef}
          type="text"
          inputMode="decimal"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              commit();
            }
            if (e.key === "Escape") {
              e.preventDefault();
              cancel();
            }
          }}
          className="h-full w-full border-0 bg-transparent p-2 text-right font-[inherit] text-sm tabular-nums outline-none"
        />
      ) : (
        format(value)
      )}
    </td>
  );
}

export function SimulationTable({ rows, retireAge, onUpdateRow }: Props) {
  const formatFlow = useCallback((v: number) => {
    if (v === 0) return <span>₩0</span>;
    return (
      <span style={{ color: v > 0 ? "var(--rise)" : "var(--fall)" }}>
        {krw(v, { sign: true })}
      </span>
    );
  }, []);

  const formatRate = useCallback((v: number) => pct(v), []);

  if (!rows.length) return null;

  return (
    <Card className="overflow-hidden shadow-none">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div>
          <p className="text-sm font-semibold">연도별 흐름</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            <span style={{ color: "var(--rise)" }}>●</span> 적립 ·{" "}
            <span style={{ color: "var(--fall)" }}>●</span> 인출 · 셀 클릭으로
            편집
          </p>
        </div>
        <span className="text-xs text-muted-foreground tabular-nums">
          {rows.length}개 행
        </span>
      </div>
      <div className="overflow-auto" style={{ maxHeight: 600 }}>
        <table className="w-full border-collapse text-sm tabular-nums">
          <thead>
            <tr className="sticky top-0 z-10">
              <th className="sticky left-0 z-20 bg-muted/60 px-3 py-2.5 text-left text-xs font-medium text-muted-foreground min-w-[48px] border-b">
                나이
              </th>
              <th className="bg-muted/60 px-3 py-2.5 text-left text-xs font-medium text-muted-foreground min-w-[60px] border-b">
                연도
              </th>
              <th className="bg-muted/60 px-3 py-2.5 text-right text-xs font-medium text-muted-foreground min-w-[130px] border-b">
                적립 금액
              </th>
              <th className="bg-muted/60 px-3 py-2.5 text-right text-xs font-medium text-muted-foreground min-w-[80px] border-b">
                수익률
              </th>
              <th className="bg-muted/60 px-3 py-2.5 text-right text-xs font-medium text-muted-foreground min-w-[140px] border-b">
                총 금액
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const isWithdraw = r.age >= retireAge;
              const isRetireLine = r.age === retireAge;
              return (
                <tr
                  key={r.age}
                  className={cn(isWithdraw && "bg-muted/20")}
                  style={
                    isRetireLine
                      ? { boxShadow: "inset 0 2px 0 0 var(--rise)" }
                      : undefined
                  }
                >
                  <td className="sticky left-0 bg-[inherit] px-3 py-2 text-left font-medium border-b border-border/40 z-[1]">
                    {r.age}
                  </td>
                  <td className="px-3 py-2 text-left text-muted-foreground border-b border-border/40">
                    {r.year}
                  </td>
                  <EditableCell
                    value={r.flow}
                    onCommit={(v) => onUpdateRow(r.age, { flow: v })}
                    format={formatFlow}
                  />
                  <EditableCell
                    value={r.rate}
                    onCommit={(v) => onUpdateRow(r.age, { rate: v })}
                    format={formatRate}
                    parse={(s) => Number(s.replace(/%/g, ""))}
                  />
                  <td className="px-3 py-2 text-right font-semibold border-b border-border/40">
                    {krw(r.end)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
