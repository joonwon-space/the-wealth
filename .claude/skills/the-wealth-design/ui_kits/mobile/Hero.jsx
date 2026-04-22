const Hero = () => (
  <div className="tw-hero">
    <div className="lbl">총 평가금액</div>
    <div className="val">₩42,180,500</div>
    <div className="delta text-rise">+₩1,204,000 · +2.94%</div>
    <div className="row">
      <div className="mini"><div className="mlbl">일간</div><div className="mval text-rise">+0.83%</div></div>
      <div className="mini"><div className="mlbl">월간</div><div className="mval text-rise">+4.12%</div></div>
      <div className="mini"><div className="mlbl">YTD</div><div className="mval text-fall">−1.61%</div></div>
    </div>
  </div>
);
window.Hero = Hero;
