const WATCH = [
  { name: "엔비디아", code: "NVDA", price: "$132.40", rate: 2.14 },
  { name: "테슬라", code: "TSLA", price: "$248.10", rate: -1.37 },
  { name: "애플", code: "AAPL", price: "$234.50", rate: 0.58 },
  { name: "카카오뱅크", code: "323410", price: "₩24,100", rate: 0.00 },
];
const Watchlist = () => (
  <div className="tw-card">
    <div className="tw-card-head">
      <div>
        <div className="tw-h3">관심종목</div>
        <div className="tw-small">4종목</div>
      </div>
      <button className="tw-btn tw-btn-ghost">편집</button>
    </div>
    <ul className="tw-watch">
      {WATCH.map(w => {
        const cls = w.rate > 0 ? "text-rise" : w.rate < 0 ? "text-fall" : "text-muted-foreground";
        const sign = w.rate > 0 ? "+" : "";
        return (
          <li key={w.code}>
            <div>
              <div className="tw-holding-name">{w.name}</div>
              <div className="tw-holding-code">{w.code}</div>
            </div>
            <div style={{textAlign:"right"}}>
              <div style={{fontWeight:600, fontVariantNumeric:"tabular-nums"}}>{w.price}</div>
              <div className={cls} style={{fontSize:12, fontVariantNumeric:"tabular-nums"}}>{sign}{w.rate.toFixed(2)}%</div>
            </div>
          </li>
        );
      })}
    </ul>
  </div>
);
window.Watchlist = Watchlist;
