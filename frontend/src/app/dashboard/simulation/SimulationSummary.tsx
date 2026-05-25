"use client";

import { Card, CardContent } from "@/components/ui/card";
import type { SimulationSummaryData } from "./types";
import { krw, pct } from "./formatters";

interface Props {
  summary: SimulationSummaryData;
  retireAge: number;
}

type ColorVariant = "rise" | "fall" | "neutral";

interface SummaryCard {
  label: string;
  value: string;
  color: ColorVariant;
  sub?: string;
}

function getColorStyle(color: ColorVariant): React.CSSProperties {
  if (color === "rise") return { color: "var(--rise)" };
  if (color === "fall") return { color: "var(--fall)" };
  return {};
}

export function SimulationSummary({ summary, retireAge }: Props) {
  const cards: SummaryCard[] = [
    { label: "종료 시점 잔고", value: krw(summary.endBalance), color: "rise" },
    {
      label: "적립단계 마지막",
      value: krw(summary.lastAccumBalance),
      color: "rise",
      sub: `${retireAge - 1}세 기준`,
    },
    { label: "총 적립액", value: krw(summary.totalContrib), color: "rise" },
    { label: "총 인출액", value: krw(summary.totalWithdraw), color: "fall" },
    { label: "총 운용수익", value: krw(summary.totalGain), color: "rise" },
    { label: "평균 수익률", value: pct(summary.avgRate), color: "neutral" },
  ];

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
      {cards.map((c) => (
        <Card key={c.label} className="shadow-none">
          <CardContent className="p-3">
            <p className="text-xs text-muted-foreground leading-snug">
              {c.label}
            </p>
            {c.sub && (
              <p className="text-[10px] text-muted-foreground/70">{c.sub}</p>
            )}
            <p
              className="mt-1 text-base font-semibold tabular-nums tracking-tight"
              style={getColorStyle(c.color)}
            >
              {c.value}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
