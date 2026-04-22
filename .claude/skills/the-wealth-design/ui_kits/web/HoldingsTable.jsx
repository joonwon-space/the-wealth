const HOLDINGS = [
  { name: "삼성전자", code: "005930", qty: 125, price: 71200, value: 8900000, rate: 1.71, sector: "반도체" },
  { name: "NAVER", code: "035420", qty: 30, price: 186500, value: 5595000, rate: -1.11, sector: "IT서비스" },
  { name: "SK하이닉스", code: "000660", qty: 40, price: 158000, value: 6320000, rate: 0.0, sector: "반도체" },
  { name: "카카오", code: "035720", qty: 80, price: 52300, value: 4184000, rate: 2.41, sector: "IT서비스" },
  { name: "LG에너지솔루션", code: "373220", qty: 10, price: 412000, value: 4120000, rate: -0.85, sector: "이차전지" },
  { name: "현대차", code: "005380", qty: 20, price: 234500, value: 4690000, rate: 3.10, sector: "자동차" },
  { name: "셀트리온", code: "068270", qty: 25, price: 181200, value: 4530000, rate: -0.42, sector: "바이오" },
  { name: "KB금융", code: "105560", qty: 60, price: 66800, value: 4008000, rate: 0.75, sector: "금융" },
];
const fmt = (n) => "₩" + n.toLocaleString("ko-KR");
const HoldingsTable = () => (
  <div className="tw-card">
    <div className="tw-card-head">
      <div>
        <div className="tw-h3">보유 종목</div>
        <div className="tw-small">8종목 · 총 ₩42,347,000</div>
      </div>
      <div className="tw-card-actions">
        <button className="tw-btn tw-btn-ghost">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"><path d="M12 3v12M6 9l6 6 6-6"/><path d="M5 21h14"/></svg>
          CSV 내보내기
        </button>
        <button className="tw-btn tw-btn-primary">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 5v14M5 12h14"/></svg>
          추가
        </button>
      </div>
    </div>
    <table className="tw-table">
      <thead>
        <tr>
          <th style={{textAlign:"left"}}>종목</th>
          <th>수량</th>
          <th>현재가</th>
          <th>평가금액</th>
          <th>수익률</th>
          <th style={{textAlign:"left"}}>섹터</th>
        </tr>
      </thead>
      <tbody>
        {HOLDINGS.map(h => {
          const cls = h.rate > 0 ? "text-rise" : h.rate < 0 ? "text-fall" : "text-muted-foreground";
          const sign = h.rate > 0 ? "+" : "";
          return (
            <tr key={h.code}>
              <td style={{textAlign:"left"}}>
                <div className="tw-holding-name">{h.name}</div>
                <div className="tw-holding-code">{h.code}</div>
              </td>
              <td>{h.qty.toLocaleString("ko-KR")}주</td>
              <td>{fmt(h.price)}</td>
              <td>{fmt(h.value)}</td>
              <td className={cls}>{sign}{h.rate.toFixed(2)}%</td>
              <td style={{textAlign:"left"}}><span className="tw-chip">{h.sector}</span></td>
            </tr>
          );
        })}
      </tbody>
    </table>
  </div>
);
window.HoldingsTable = HoldingsTable;
