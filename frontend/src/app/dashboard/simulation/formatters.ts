export function krw(n: number, opts: { sign?: boolean } = {}): string {
  if (!isFinite(n)) return "₩—";
  const neg = n < 0;
  const abs = Math.round(Math.abs(n));
  const formatted = "₩" + abs.toLocaleString("ko-KR");
  return (neg ? "-" : opts.sign && n > 0 ? "+" : "") + formatted;
}

export function pct(n: number): string {
  if (!isFinite(n)) return "—";
  return n.toFixed(2) + "%";
}

export function shortKrw(n: number): string {
  if (n === 0) return "0";
  const eok = n / 1e8;
  if (Math.abs(eok) >= 1) return eok.toFixed(eok >= 10 ? 0 : 1) + "억";
  return Math.round(n / 1e4).toLocaleString() + "만";
}
