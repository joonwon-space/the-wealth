"use client";

import { formatRate } from "@/lib/format";

interface Props {
  /** 전일 대비 변동률 (%). null이면 배지를 표시하지 않음. */
  pct: number | null | undefined;
}

/**
 * 전일 대비 배지 — ▲ +2.3% / ▼ -1.5% 형식.
 * 한국 증시 컬러: 상승 = text-rise (var(--rise)), 하락 = text-fall (var(--fall)).
 * pct가 null/undefined면 null을 반환하여 아무것도 렌더링하지 않음.
 */
export function DayChangeBadge({ pct }: Props) {
  if (pct == null) return null;

  const n = Number(pct);
  const isPositive = n > 0;
  const isNegative = n < 0;

  const color = isPositive
    ? "text-rise"
    : isNegative
      ? "text-fall"
      : "text-foreground";

  const arrow = isPositive ? "▲" : isNegative ? "▼" : "";
  const sign = isPositive ? "+" : "";
  const formatted = `${arrow} ${sign}${formatRate(Math.abs(n))}%`;

  return (
    <span className={`font-semibold tabular-nums text-xs ${color}`}>
      {formatted}
    </span>
  );
}
