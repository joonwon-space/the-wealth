"use client";

import { formatPnL, formatRate } from "@/lib/format";

interface Props {
  value: number | string | null;
  showSign?: boolean;
  suffix?: string;
}

/**
 * 한국 증시 컬러 컨벤션: 상승 = 빨간색, 하락 = 파란색
 */
export function PnLBadge({ value, showSign = true, suffix = "" }: Props) {
  if (value == null) return <span className="text-muted-foreground">—</span>;

  const n = Number(value);
  const isPositive = n > 0;
  const isZero = n === 0;
  const color = isZero ? "text-foreground" : isPositive ? "text-[#e31f26]" : "text-[#1a56db]";

  const formatted = suffix === "%" ? formatRate(n) : formatPnL(n);
  const display = suffix === "%" && showSign && n > 0 ? `+${formatted}` : formatted;

  return (
    <span className={`font-semibold tabular-nums ${color}`}>
      {display}
      {suffix}
    </span>
  );
}
