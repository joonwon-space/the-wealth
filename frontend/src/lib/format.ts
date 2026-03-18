/** 금액 포맷 — 천 단위 콤마, 소수점 없음. */
export function formatKRW(value: number | string | null | undefined): string {
  if (value == null) return "—";
  return `₩${Number(value).toLocaleString("ko-KR", { maximumFractionDigits: 0 })}`;
}

/** USD 금액 포맷 — 소수점 둘째자리까지. */
export function formatUSD(value: number | string | null | undefined): string {
  if (value == null) return "—";
  return `$${Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** 통화에 따른 금액 포맷. */
export function formatPrice(
  value: number | string | null | undefined,
  currency: "KRW" | "USD" = "KRW"
): string {
  if (currency === "USD") return formatUSD(value);
  return formatKRW(value);
}

/** 수량 포맷 — 천 단위 콤마, 소수점은 있으면 표시. */
export function formatNumber(value: number | string | null | undefined): string {
  if (value == null) return "—";
  return Number(value).toLocaleString("ko-KR");
}

/** 비율 포맷 — 소수점 둘째자리까지. */
export function formatRate(value: number | string | null | undefined): string {
  if (value == null) return "—";
  return Number(value).toFixed(2);
}

/** 금액 포맷 (부호 포함) — PnL용. */
export function formatPnL(value: number | string | null | undefined): string {
  if (value == null) return "—";
  const n = Number(value);
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toLocaleString("ko-KR", { maximumFractionDigits: 0 })}`;
}
