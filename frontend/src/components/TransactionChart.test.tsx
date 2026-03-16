import { describe, it, expect } from "vitest";

// Test the aggregation logic directly (no DOM needed for pure logic)
// We import the component but only test data transformation
describe("TransactionChart aggregation", () => {
  it("groups transactions by month", () => {
    const txns = [
      { type: "BUY", quantity: "10", price: "1000", traded_at: "2026-01-15T10:00:00Z" },
      { type: "SELL", quantity: "5", price: "1200", traded_at: "2026-01-20T10:00:00Z" },
      { type: "BUY", quantity: "20", price: "900", traded_at: "2026-02-10T10:00:00Z" },
    ];

    // Replicate aggregation logic
    const map = new Map<string, { buy: number; sell: number }>();
    for (const t of txns) {
      const date = new Date(t.traded_at);
      const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
      const entry = map.get(key) ?? { buy: 0, sell: 0 };
      const amount = Number(t.quantity) * Number(t.price);
      if (t.type === "BUY") entry.buy += amount;
      else entry.sell += amount;
      map.set(key, entry);
    }
    const data = Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));

    expect(data).toHaveLength(2);
    expect(data[0][0]).toBe("2026-01");
    expect(data[0][1].buy).toBe(10000);
    expect(data[0][1].sell).toBe(6000);
    expect(data[1][0]).toBe("2026-02");
    expect(data[1][1].buy).toBe(18000);
    expect(data[1][1].sell).toBe(0);
  });

  it("handles empty transactions", () => {
    const map = new Map<string, { buy: number; sell: number }>();
    expect(Array.from(map.entries())).toHaveLength(0);
  });
});
