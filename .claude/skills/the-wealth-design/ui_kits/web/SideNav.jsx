const NAV = [
  { id: "dashboard", label: "대시보드", icon: (<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>) },
  { id: "portfolio", label: "포트폴리오", icon: (<svg viewBox="0 0 24 24"><path d="M21 12V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2"/><path d="M16 12h6"/></svg>) },
  { id: "returns", label: "수익률 분석", icon: (<svg viewBox="0 0 24 24"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>) },
  { id: "sectors", label: "섹터 배분", icon: (<svg viewBox="0 0 24 24"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/></svg>) },
  { id: "watchlist", label: "관심종목", icon: (<svg viewBox="0 0 24 24"><polygon points="12 2 15 9 22 9.5 17 14.5 18.5 22 12 18 5.5 22 7 14.5 2 9.5 9 9"/></svg>) },
  { id: "alerts", label: "가격 알림", icon: (<svg viewBox="0 0 24 24"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>) },
  { id: "settings", label: "설정", icon: (<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9c0 .66.39 1.25 1 1.51h.09a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/></svg>) },
];
const SideNav = ({ active, onSelect }) => (
  <aside className="tw-side">
    <ul>
      {NAV.map(n => (
        <li key={n.id}
            className={active === n.id ? "tw-side-item tw-side-active" : "tw-side-item"}
            onClick={() => onSelect(n.id)}>
          {n.icon}
          <span>{n.label}</span>
        </li>
      ))}
    </ul>
    <div className="tw-side-footer">
      <div className="tw-side-sync">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"><circle cx="12" cy="12" r="2" fill="currentColor"/></svg>
        <div>
          <div className="tw-micro">KIS 동기화</div>
          <div style={{fontSize:12,color:"var(--muted-foreground)"}}>1시간 전</div>
        </div>
      </div>
    </div>
  </aside>
);
window.SideNav = SideNav;
