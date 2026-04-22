// ============================================================
// redesign/data.js — realistic mock data derived from audit.md
// schemas (Portfolio / Holding / Transaction / Order / etc.)
// Exposed on window.TW for every other script.
// ============================================================

window.TW = window.TW || {};

window.TW.mockData = (() => {
  const now = new Date('2025-04-22T14:32:00+09:00');

  const portfolios = [
    { id: 'p1', name: '주 계좌 · 한투 ISA', currency: 'KRW', account_type: 'ISA', target_value: 200_000_000, display_order: 1, strategy: 'long' },
    { id: 'p2', name: '단타 계좌', currency: 'KRW', account_type: '일반', target_value: null, display_order: 2, strategy: 'short' },
    { id: 'p3', name: '해외주식', currency: 'USD', account_type: '해외', target_value: null, display_order: 3, strategy: 'long' },
  ];

  const holdings = [
    // Long portfolio (p1)
    { pid: 'p1', ticker: '005930', name: '삼성전자', market: 'KRX', quantity: 430, avg_price: 68500, current_price: 72400, sector: 'IT' },
    { pid: 'p1', ticker: '000660', name: 'SK하이닉스', market: 'KRX', quantity: 95, avg_price: 148000, current_price: 163500, sector: 'IT' },
    { pid: 'p1', ticker: '373220', name: 'LG에너지솔루션', market: 'KRX', quantity: 42, avg_price: 412000, current_price: 384500, sector: '소재' },
    { pid: 'p1', ticker: '207940', name: '삼성바이오로직스', market: 'KRX', quantity: 18, avg_price: 795000, current_price: 842000, sector: '헬스케어' },
    { pid: 'p1', ticker: '035720', name: '카카오', market: 'KRX', quantity: 180, avg_price: 52300, current_price: 48200, sector: 'IT' },
    { pid: 'p1', ticker: '105560', name: 'KB금융', market: 'KRX', quantity: 220, avg_price: 68200, current_price: 71500, sector: '금융' },
    // Short portfolio (p2) — smaller positions, faster turnover
    { pid: 'p2', ticker: '247540', name: '에코프로비엠', market: 'KRX', quantity: 50, avg_price: 182000, current_price: 189500, sector: '소재' },
    { pid: 'p2', ticker: '005380', name: '현대차', market: 'KRX', quantity: 25, avg_price: 245000, current_price: 249500, sector: '경기소비재' },
    // USD portfolio (p3)
    { pid: 'p3', ticker: 'NVDA', name: 'NVIDIA', market: 'NAS', quantity: 45, avg_price: 118.40, current_price: 145.22, sector: 'IT' },
    { pid: 'p3', ticker: 'AAPL', name: 'Apple', market: 'NAS', quantity: 80, avg_price: 195.30, current_price: 212.80, sector: 'IT' },
    { pid: 'p3', ticker: 'MSFT', name: 'Microsoft', market: 'NAS', quantity: 30, avg_price: 420.00, current_price: 438.50, sector: 'IT' },
  ];

  // Derived portfolio-level numbers (pre-computed for simplicity)
  const portfolioSummaries = {
    p1: {
      total_value: 90_615_000,
      principal: 85_204_000,
      day_change_amount: 1_284_500,
      day_change_pct: 1.44,
      ytd_pct: 6.4,
      yoy_pct: 8.2,
      cash: 4_120_000,
      target_progress: 0.647,
    },
    p2: {
      total_value: 38_835_000,
      principal: 37_965_000,
      day_change_amount: 870_200,
      day_change_pct: 2.29,
      ytd_pct: 4.1,
      cash: 1_850_000,
      unfilled_orders: 2,
    },
    p3: {
      total_value: 42_680, // USD
      principal: 33_450,
      day_change_amount: 620, // USD
      day_change_pct: 1.47,
      ytd_pct: 18.4,
      cash: 1_240, // USD
    },
  };

  const dayChangeTotal = 2_340_500;
  const totalValueKRW = 129_450_000; // rolls up p1 + p2 + p3*USDKRW

  // Sector allocation (across all KRW holdings)
  const sectorAllocation = [
    { sector: 'IT',        pct: 0.45, value: 58_252_500, target: 0.30, color: '#1e90ff' },
    { sector: '소재',      pct: 0.22, value: 28_479_000, target: 0.20, color: '#8b5cf6' },
    { sector: '금융',      pct: 0.12, value: 15_534_000, target: 0.15, color: '#f59e0b' },
    { sector: '헬스케어',  pct: 0.11, value: 14_239_500, target: 0.15, color: '#16a34a' },
    { sector: '경기소비재',pct: 0.10, value: 12_945_000, target: 0.20, color: '#06b6d4' },
  ];

  // Monthly returns — for heatmap
  const monthlyReturns = [
    { ym: '2024-11', pct:  2.3 }, { ym: '2024-12', pct: -0.8 },
    { ym: '2025-01', pct:  4.1 }, { ym: '2025-02', pct: -1.2 },
    { ym: '2025-03', pct:  1.8 }, { ym: '2025-04', pct:  1.84 },
  ];

  // Benchmark comparison (portfolio % vs KOSPI200 over 6M)
  const benchmarkSeries = {
    mine:    [0, 0.8, 1.4, 0.9, 2.2, 3.6, 4.8, 5.4, 6.1, 6.4],
    kospi200:[0, 0.5, 0.2, 1.1, 0.8, 1.6, 1.4, 2.1, 2.8, 3.1],
    labels:  ['11월','11월','12월','12월','1월','2월','2월','3월','3월','4월'],
  };

  // Today's movers (across all portfolios)
  const movers = [
    { ticker: 'NVDA',   name: 'NVIDIA',         pct:  3.42, change_value:  580_000, price: '$145.22', up: true },
    { ticker: '005930', name: '삼성전자',        pct:  2.85, change_value:  720_000, price: '72,400',  up: true },
    { ticker: '000660', name: 'SK하이닉스',      pct:  2.10, change_value:  310_000, price: '163,500', up: true },
    { ticker: '373220', name: 'LG에너지솔루션',  pct: -1.85, change_value: -220_000, price: '384,500', up: false },
    { ticker: '035720', name: '카카오',          pct: -2.40, change_value: -180_000, price: '48,200',  up: false },
  ];

  // Pending orders
  const orders = [
    { id: 'o1', ticker: 'NVDA',   name: 'NVIDIA',         type: 'BUY',  qty: 10, limit: 142.00, status: 'pending',  pid: 'p3', ts: '14:12' },
    { id: 'o2', ticker: '005930', name: '삼성전자',        type: 'SELL', qty: 20, limit: 73_000,  status: 'pending',  pid: 'p2', ts: '13:48' },
    { id: 'o3', ticker: '005930', name: '삼성전자',        type: 'BUY',  qty: 10, limit: 72_400,  status: 'filled',   pid: 'p1', ts: '09:12' },
  ];

  // Recent transactions
  const transactions = [
    { id: 't1', ticker: '005930', name: '삼성전자',    type: 'BUY',  qty: 10, price: 72_400,  value: 724_000,  ts: '04-22 09:12', memo: '추매', tags: ['장기','코어'] },
    { id: 't2', ticker: 'NVDA',   name: 'NVIDIA',     type: 'BUY',  qty:  5, price: 142.50,  value: 712_500,  ts: '04-21 23:30', memo: 'AI 테마',     tags: ['장기'] },
    { id: 't3', ticker: '035720', name: '카카오',      type: 'SELL', qty: 50, price: 50_100,  value: 2_505_000, ts: '04-20 14:42', memo: '손절',       tags: ['정리'] },
  ];

  // Upcoming dividends
  const dividends = [
    { ticker: '005930', name: '삼성전자',   ex_date: '04-28', payment_date: '05-18', amount: 36_000,  currency: 'KRW' },
    { ticker: 'AAPL',   name: 'Apple',     ex_date: '05-16', payment_date: '05-23', amount: 12.00,   currency: 'USD' },
    { ticker: '105560', name: 'KB금융',     ex_date: '05-28', payment_date: '06-18', amount: 55_000,  currency: 'KRW' },
  ];

  // Alerts (triggered today)
  const alerts = [
    { id: 'a1', ticker: 'NVDA',   name: 'NVIDIA',    condition: 'above',  threshold: 140, current: 145.22, ts: '14:32' },
    { id: 'a2', ticker: '373220', name: 'LG엔솔',    condition: 'below',  threshold: 390_000, current: 384_500, ts: '10:18' },
  ];

  // Today's tasks (rebalance / dividend / routine)
  const tasks = [
    { icon: '!', color: '#E31F26', title: 'IT 섹터 45% · 목표 30% 초과', sub: '리밸런싱 검토', action: 'rebalance' },
    { icon: '$', color: '#f59e0b', title: '삼성전자 배당락 4/28', sub: '4거래일 남음', action: 'dividend' },
    { icon: '✓', color: '#1e90ff', title: '월 리밸런싱 체크',       sub: '매월 마지막 영업일', action: 'routine' },
  ];

  // 52-week stats for one stock (detail view)
  const stockDetail = {
    ticker: '005930', name: '삼성전자', market: 'KRX',
    current_price: 72_400,
    day_change_amount: 2_000, day_change_pct: 2.85,
    w52_high: 88_800, w52_low: 49_900,
    volume: '18,240,100', market_cap: '432.1조',
    per: 14.2, pbr: 1.35, dividend_yield: 1.98,
  };

  // Intraday tick series (for big chart on home) — 0..1 normalized y
  const intradaySeries = (() => {
    const pts = [];
    const n = 80;
    let y = 0.4;
    for (let i=0; i<n; i++) {
      y += (Math.sin(i*0.18) * 0.04) + ((i/n) * 0.008) + ((Math.random()-0.45)*0.015);
      y = Math.max(0.05, Math.min(0.95, y));
      pts.push(y);
    }
    return pts;
  })();

  // Daily series for 1M view
  const dailySeries = (() => {
    const pts = [];
    let y = 0.35;
    for (let i=0; i<30; i++) {
      y += ((Math.random()-0.4) * 0.04);
      y = Math.max(0.1, Math.min(0.9, y));
      pts.push(y);
    }
    return pts;
  })();

  const fmtKRW  = (n) => n==null?'—':Math.round(n).toLocaleString('ko-KR');
  const fmtPct  = (n, d=2) => (n>=0?'+':'')+n.toFixed(d)+'%';
  const fmtUSD  = (n) => '$'+n.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
  const fmtSignedKRW = (n) => (n>=0?'+':'')+Math.round(n).toLocaleString('ko-KR');

  return {
    now, portfolios, holdings, portfolioSummaries,
    dayChangeTotal, totalValueKRW, sectorAllocation, monthlyReturns,
    benchmarkSeries, movers, orders, transactions, dividends, alerts, tasks,
    stockDetail, intradaySeries, dailySeries,
    fmt: { krw: fmtKRW, pct: fmtPct, usd: fmtUSD, signed: fmtSignedKRW },
  };
})();
