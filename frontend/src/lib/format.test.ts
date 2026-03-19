import { describe, it, expect } from "vitest";
import {
  formatKRW,
  formatUSD,
  formatPrice,
  formatNumber,
  formatRate,
  formatPnL,
} from "./format";

describe("formatKRW", () => {
  it("formats positive integer with won sign", () => {
    expect(formatKRW(1000)).toBe("₩1,000");
  });

  it("formats large numbers with commas", () => {
    expect(formatKRW(1234567)).toBe("₩1,234,567");
  });

  it("rounds fractional values to 0 decimals", () => {
    expect(formatKRW(1234.5)).toBe("₩1,235");
  });

  it("formats zero", () => {
    expect(formatKRW(0)).toBe("₩0");
  });

  it("formats negative values with won sign before the minus", () => {
    // toLocaleString puts the currency symbol before the minus in ko-KR
    expect(formatKRW(-5000)).toBe("₩-5,000");
  });

  it("accepts string input", () => {
    expect(formatKRW("2000")).toBe("₩2,000");
  });

  it("returns em-dash for null", () => {
    expect(formatKRW(null)).toBe("—");
  });

  it("returns em-dash for undefined", () => {
    expect(formatKRW(undefined)).toBe("—");
  });

  it("returns em-dash for NaN string", () => {
    expect(formatKRW("not-a-number")).toBe("—");
  });
});

describe("formatUSD", () => {
  it("formats positive value with dollar sign and 2 decimals", () => {
    expect(formatUSD(100)).toBe("$100.00");
  });

  it("formats value with cents", () => {
    expect(formatUSD(1.5)).toBe("$1.50");
  });

  it("formats large value with commas", () => {
    expect(formatUSD(1234567.89)).toBe("$1,234,567.89");
  });

  it("accepts string input", () => {
    expect(formatUSD("50.00")).toBe("$50.00");
  });

  it("returns em-dash for null", () => {
    expect(formatUSD(null)).toBe("—");
  });

  it("returns em-dash for undefined", () => {
    expect(formatUSD(undefined)).toBe("—");
  });
});

describe("formatPrice", () => {
  it("defaults to KRW format", () => {
    expect(formatPrice(1000)).toBe("₩1,000");
  });

  it("formats USD when currency is USD", () => {
    expect(formatPrice(100, "USD")).toBe("$100.00");
  });

  it("formats KRW when currency is KRW", () => {
    expect(formatPrice(2000, "KRW")).toBe("₩2,000");
  });

  it("returns em-dash for null", () => {
    expect(formatPrice(null)).toBe("—");
  });
});

describe("formatNumber", () => {
  it("formats integer with Korean locale commas", () => {
    expect(formatNumber(1000000)).toBe("1,000,000");
  });

  it("shows decimals when present", () => {
    // ko-KR locale may render decimal differently; check it doesn't lose digits
    const result = formatNumber(1.5);
    expect(result).toContain("1");
    expect(result).toContain("5");
  });

  it("returns em-dash for null", () => {
    expect(formatNumber(null)).toBe("—");
  });

  it("returns em-dash for undefined", () => {
    expect(formatNumber(undefined)).toBe("—");
  });

  it("accepts string input", () => {
    expect(formatNumber("500")).toBe("500");
  });
});

describe("formatRate", () => {
  it("formats rate to 2 decimal places", () => {
    expect(formatRate(1.234)).toBe("1.23");
  });

  it("pads to 2 decimals", () => {
    expect(formatRate(5)).toBe("5.00");
  });

  it("handles negative rate", () => {
    expect(formatRate(-3.5)).toBe("-3.50");
  });

  it("returns em-dash for null", () => {
    expect(formatRate(null)).toBe("—");
  });

  it("returns em-dash for undefined", () => {
    expect(formatRate(undefined)).toBe("—");
  });

  it("accepts string input", () => {
    expect(formatRate("2.5")).toBe("2.50");
  });
});

describe("formatPnL", () => {
  it("adds plus sign for positive value", () => {
    expect(formatPnL(5000)).toBe("+5,000");
  });

  it("no sign prefix for negative value (negative sign is part of number)", () => {
    expect(formatPnL(-3000)).toBe("-3,000");
  });

  it("formats zero without sign", () => {
    expect(formatPnL(0)).toBe("0");
  });

  it("accepts string input", () => {
    expect(formatPnL("1000")).toBe("+1,000");
  });

  it("returns em-dash for null", () => {
    expect(formatPnL(null)).toBe("—");
  });

  it("returns em-dash for undefined", () => {
    expect(formatPnL(undefined)).toBe("—");
  });
});
