const TABS = [
  { id: "home", label: "홈", icon: (<svg viewBox="0 0 24 24"><path d="M3 10.5 12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1z"/></svg>) },
  { id: "portfolio", label: "포트폴리오", icon: (<svg viewBox="0 0 24 24"><path d="M21 12V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2"/><path d="M16 12h6"/></svg>) },
  { id: "watch", label: "관심", icon: (<svg viewBox="0 0 24 24"><polygon points="12 2 15 9 22 9.5 17 14.5 18.5 22 12 18 5.5 22 7 14.5 2 9.5 9 9"/></svg>) },
  { id: "alerts", label: "알림", icon: (<svg viewBox="0 0 24 24"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>) },
  { id: "me", label: "내 정보", icon: (<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>) },
];
const TabBar = ({ active, onSelect }) => (
  <nav className="tw-tabbar">
    {TABS.map(t => (
      <button key={t.id} className={active === t.id ? "active" : ""} onClick={() => onSelect(t.id)}>
        {t.icon}
        <span>{t.label}</span>
      </button>
    ))}
  </nav>
);
window.TabBar = TabBar;
