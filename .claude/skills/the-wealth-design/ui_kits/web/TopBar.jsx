const TopBar = ({ onToggleTheme, theme }) => (
  <header className="tw-topbar">
    <div className="tw-topbar-left">
      <div className="tw-logo"><span>W</span></div>
      <div className="tw-wordmark">The Wealth</div>
      <nav className="tw-crumbs">
        <span className="tw-micro">DASHBOARD</span>
      </nav>
    </div>
    <div className="tw-topbar-search">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <input placeholder="종목명 또는 코드 검색" />
      <span className="tw-kbd">⌘K</span>
    </div>
    <div className="tw-topbar-right">
      <button className="tw-iconbtn" title="새로고침">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 0 1-15.36 6.36L3 21"/><polyline points="3 16 3 21 8 21"/><path d="M3 12a9 9 0 0 1 15.36-6.36L21 3"/><polyline points="21 8 21 3 16 3"/></svg>
      </button>
      <button className="tw-iconbtn" title="알림">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
        <span className="tw-dot" />
      </button>
      <button className="tw-iconbtn" onClick={onToggleTheme} title="테마">
        {theme === "dark" ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/></svg>
        )}
      </button>
      <div className="tw-avatar">김</div>
    </div>
  </header>
);
window.TopBar = TopBar;
