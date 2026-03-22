/**
 * MSW request handlers for unit/integration tests.
 * Add handlers here to mock backend API responses in tests.
 */
import { http, HttpResponse } from "msw";

const API_BASE = "http://localhost:8000/api/v1";

export const handlers = [
  // Dashboard summary
  http.get(`${API_BASE}/dashboard/summary`, () => {
    return HttpResponse.json({
      total_asset: 10000000,
      total_invested: 8000000,
      total_pnl_amount: 2000000,
      total_pnl_rate: 25.0,
      kis_status: "ok",
      holdings: [
        {
          id: 1,
          ticker: "005930",
          name: "삼성전자",
          quantity: 10,
          avg_price: 70000,
          current_price: 75000,
          market_value: 750000,
          market_value_krw: 750000,
          pnl_amount: 50000,
          pnl_rate: 7.14,
          day_change_rate: 1.2,
          currency: "KRW" as const,
          week52_high: 80000,
          week52_low: 60000,
        },
        {
          id: 2,
          ticker: "AAPL",
          name: "Apple Inc.",
          quantity: 5,
          avg_price: 150.0,
          current_price: 170.0,
          market_value: 850.0,
          market_value_krw: 1105000,
          pnl_amount: 100.0,
          pnl_rate: 13.33,
          day_change_rate: -0.5,
          currency: "USD" as const,
          week52_high: 200.0,
          week52_low: 130.0,
        },
      ],
      allocation: [
        { ticker: "005930", name: "삼성전자", value: 750000, ratio: 40.5 },
        { ticker: "AAPL", name: "Apple Inc.", value: 1105000, ratio: 59.5 },
      ],
    });
  }),

  // Analytics metrics
  http.get(`${API_BASE}/analytics/metrics`, () => {
    return HttpResponse.json({
      total_return_rate: 25.0,
      cagr: 12.5,
      mdd: 8.3,
      sharpe_ratio: 1.42,
    });
  }),

  // Analytics monthly returns
  http.get(`${API_BASE}/analytics/monthly-returns`, () => {
    return HttpResponse.json([
      { year: 2025, month: 1, return_rate: 2.1 },
      { year: 2025, month: 2, return_rate: -1.3 },
      { year: 2025, month: 3, return_rate: 3.5 },
    ]);
  }),

  // Analytics portfolio history
  http.get(`${API_BASE}/analytics/portfolio-history`, () => {
    return HttpResponse.json([
      { date: "2025-01-01", value: 8000000 },
      { date: "2025-02-01", value: 8500000 },
      { date: "2025-03-01", value: 10000000 },
    ]);
  }),

  // Analytics sector allocation
  http.get(`${API_BASE}/analytics/sector-allocation`, () => {
    return HttpResponse.json([
      { sector: "Technology", value: 1855000, weight: 100.0 },
    ]);
  }),

  // Portfolios list
  http.get(`${API_BASE}/portfolios`, () => {
    return HttpResponse.json([
      { id: 1, name: "메인 포트폴리오", description: "주식 포트폴리오" },
    ]);
  }),

  // Watchlist
  http.get(`${API_BASE}/watchlist`, () => {
    return HttpResponse.json([]);
  }),

  // Alerts
  http.get(`${API_BASE}/alerts`, () => {
    return HttpResponse.json([]);
  }),

  // Notifications
  http.get(`${API_BASE}/notifications`, () => {
    return HttpResponse.json([]);
  }),
];
