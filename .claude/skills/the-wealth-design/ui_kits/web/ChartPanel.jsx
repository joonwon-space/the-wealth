const PortfolioChart = () => {
  // Generate a simple sparkline-like SVG path
  const pts = [40, 42, 41, 45, 47, 46, 49, 52, 50, 54, 57, 55, 58, 62, 60, 63, 66, 64, 67, 70];
  const max = Math.max(...pts), min = Math.min(...pts);
  const W = 560, H = 200, P = 8;
  const step = (W - P*2) / (pts.length - 1);
  const path = pts.map((v, i) => {
    const x = P + i * step;
    const y = P + (H - P*2) * (1 - (v - min) / (max - min));
    return `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
  const area = path + ` L ${W-P} ${H-P} L ${P} ${H-P} Z`;
  return (
    <div className="tw-card">
      <div className="tw-card-head">
        <div>
          <div className="tw-h3">포트폴리오 히스토리</div>
          <div className="tw-small">최근 90일 · 평가금액</div>
        </div>
        <div className="tw-tabs">
          {["1W","1M","3M","6M","1Y","ALL"].map((t, i) => (
            <button key={t} className={"tw-tab " + (i === 2 ? "tw-tab-active" : "")}>{t}</button>
          ))}
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="200">
        <defs>
          <linearGradient id="g1" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--chart-1)" stopOpacity="0.25"/>
            <stop offset="100%" stopColor="var(--chart-1)" stopOpacity="0"/>
          </linearGradient>
        </defs>
        <path d={area} fill="url(#g1)" />
        <path d={path} fill="none" stroke="var(--chart-1)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    </div>
  );
};

const SectorDonut = () => {
  const data = [
    { label: "반도체", value: 36, color: "var(--chart-1)" },
    { label: "IT서비스", value: 21, color: "var(--chart-5)" },
    { label: "자동차", value: 14, color: "var(--chart-7)" },
    { label: "금융", value: 12, color: "var(--chart-6)" },
    { label: "이차전지", value: 10, color: "var(--chart-3)" },
    { label: "바이오", value: 7, color: "var(--chart-4)" },
  ];
  const R = 60, C = 80, T = 24;
  let offset = 0;
  const total = data.reduce((s,d) => s+d.value, 0);
  const circ = 2 * Math.PI * R;
  return (
    <div className="tw-card">
      <div className="tw-card-head">
        <div>
          <div className="tw-h3">섹터 배분</div>
          <div className="tw-small">비중 %</div>
        </div>
      </div>
      <div style={{display:"flex", alignItems:"center", gap: 20}}>
        <svg width={C*2} height={C*2} viewBox={`0 0 ${C*2} ${C*2}`}>
          <circle cx={C} cy={C} r={R} fill="none" stroke="var(--muted)" strokeWidth={T}/>
          {data.map((d, i) => {
            const frac = d.value / total;
            const seg = circ * frac;
            const el = (
              <circle key={i} cx={C} cy={C} r={R} fill="none"
                stroke={d.color} strokeWidth={T}
                strokeDasharray={`${seg} ${circ - seg}`}
                strokeDashoffset={-offset}
                transform={`rotate(-90 ${C} ${C})`}/>
            );
            offset += seg;
            return el;
          })}
          <text x={C} y={C-4} textAnchor="middle" fontSize="11" fill="var(--muted-foreground)">비중</text>
          <text x={C} y={C+14} textAnchor="middle" fontSize="18" fontWeight="700" fill="var(--foreground)">100%</text>
        </svg>
        <ul className="tw-legend">
          {data.map(d => (
            <li key={d.label}>
              <span className="tw-legend-dot" style={{background: d.color}}/>
              <span>{d.label}</span>
              <span className="tw-legend-val">{d.value}%</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
window.PortfolioChart = PortfolioChart;
window.SectorDonut = SectorDonut;
