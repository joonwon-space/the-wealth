"use client";

interface Props {
  value: number;
  showSign?: boolean;
  suffix?: string;
}

/**
 * 한국 증시 컬러 컨벤션: 상승 = 빨간색, 하락 = 파란색
 */
export function PnLBadge({ value, showSign = true, suffix = "" }: Props) {
  const isPositive = value > 0;
  const isZero = value === 0;
  const color = isZero ? "text-foreground" : isPositive ? "text-[#e31f26]" : "text-[#1a56db]";
  const sign = showSign && !isZero ? (isPositive ? "+" : "") : "";

  return (
    <span className={`font-semibold tabular-nums ${color}`}>
      {sign}
      {value.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}
      {suffix}
    </span>
  );
}
