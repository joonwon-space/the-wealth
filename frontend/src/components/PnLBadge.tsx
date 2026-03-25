"use client";

import { formatPnL, formatRate } from "@/lib/format";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface Props {
  value: number | string | null;
  showSign?: boolean;
  suffix?: string;
}

/**
 * 한국 증시 컬러 컨벤션: 상승 = 빨간색, 하락 = 파란색
 * Accessibility: ▲/▼ directional icons accompany color indicators.
 */
export function PnLBadge({ value, showSign = true, suffix = "" }: Props) {
  if (value == null) return <span className="text-muted-foreground">—</span>;

  const n = Number(value);
  const isPositive = n > 0;
  const isNegative = n < 0;
  const isZero = n === 0;
  const color = isZero ? "text-foreground" : isPositive ? "text-rise" : "text-fall";

  const formatted = suffix === "%" ? formatRate(n) : formatPnL(n);
  const display = suffix === "%" && showSign && n > 0 ? `+${formatted}` : formatted;

  const Icon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus;
  const iconLabel = isPositive ? "상승" : isNegative ? "하락" : "보합";

  return (
    <span className={`inline-flex items-center gap-0.5 font-semibold tabular-nums ${color}`}>
      <Icon className="h-3.5 w-3.5 shrink-0" aria-label={iconLabel} />
      <span>
        {display}
        {suffix}
      </span>
    </span>
  );
}
