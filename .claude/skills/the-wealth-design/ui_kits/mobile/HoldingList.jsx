const ITEMS = [
  { name: "삼성전자", code: "005930", price: "₩71,200", rate: 1.71 },
  { name: "NAVER", code: "035420", price: "₩186,500", rate: -1.11 },
  { name: "SK하이닉스", code: "000660", price: "₩158,000", rate: 0.0 },
  { name: "카카오", code: "035720", price: "₩52,300", rate: 2.41 },
  { name: "현대차", code: "005380", price: "₩234,500", rate: 3.10 },
];
const HoldingList = () => (
  <div className="tw-list">
    {ITEMS.map(it => {
      const cls = it.rate > 0 ? "text-rise" : it.rate < 0 ? "text-fall" : "text-muted-foreground";
      const sign = it.rate > 0 ? "+" : "";
      return (
        <div key={it.code} className="tw-list-item">
          <div>
            <div className="name">{it.name}</div>
            <div className="code">{it.code}</div>
          </div>
          <div className="right">
            <div className="price">{it.price}</div>
            <div className={"rate " + cls}>{sign}{it.rate.toFixed(2)}%</div>
          </div>
        </div>
      );
    })}
  </div>
);
window.HoldingList = HoldingList;
