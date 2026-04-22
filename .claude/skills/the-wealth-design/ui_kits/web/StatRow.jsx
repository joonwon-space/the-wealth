const Stat = ({ label, value, delta, deltaDir, sub }) => (
  <div className="tw-stat">
    <div className="tw-stat-label">{label}</div>
    <div className="tw-stat-val">{value}</div>
    <div className={"tw-stat-delta " + (deltaDir === "up" ? "text-rise" : deltaDir === "down" ? "text-fall" : "text-muted-foreground")}>
      {delta}
    </div>
    {sub && <div className="tw-stat-sub">{sub}</div>}
  </div>
);
const StatRow = () => (
  <div className="tw-statrow">
    <Stat label="총 평가금액" value="₩42,180,500" delta="+₩1,204,000 (+2.94%)" deltaDir="up" sub="보유 종목 12개" />
    <Stat label="평가손익" value="+₩3,210,400" delta="+8.23%" deltaDir="up" sub="평균 매입가 대비" />
    <Stat label="일간 수익률" value="+0.83%" delta="KOSPI +0.51%" deltaDir="up" sub="최근 30초 갱신" />
    <Stat label="실현손익 (YTD)" value="−₩680,200" delta="거래 18건" deltaDir="down" sub="52거래일" />
  </div>
);
window.StatRow = StatRow;
