// ============================================================
// redesign/primitives.jsx — shared low-level components
// Icons, StatusBar, TabBar, charts (MiniArea, BigChart, Donut,
// ProgressRing, HeatCell), pills, cards.
// All components are exported to `window` at the end.
// ============================================================

const TWIcons = {
  home:    <svg viewBox="0 0 24 24"><path d="M3 12l9-9 9 9"/><path d="M5 10v10h14V10"/></svg>,
  chart:   <svg viewBox="0 0 24 24"><path d="M3 3v18h18"/><path d="M7 14l4-4 4 3 6-7"/></svg>,
  wallet:  <svg viewBox="0 0 24 24"><rect x="2" y="6" width="20" height="14" rx="2"/><path d="M16 12h4"/></svg>,
  bell:    <svg viewBox="0 0 24 24"><path d="M6 8a6 6 0 0112 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10 21a2 2 0 004 0"/></svg>,
  user:    <svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0116 0"/></svg>,
  search:  <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>,
  arrow:   <svg viewBox="0 0 24 24"><path d="M5 12h14"/><path d="M13 6l6 6-6 6"/></svg>,
  back:    <svg viewBox="0 0 24 24"><path d="M19 12H5"/><path d="M11 18l-6-6 6-6"/></svg>,
  target:  <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>,
  refresh: <svg viewBox="0 0 24 24"><path d="M21 12a9 9 0 11-3-6.7L21 8"/><path d="M21 3v5h-5"/></svg>,
  layers:  <svg viewBox="0 0 24 24"><path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/></svg>,
  plus:    <svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>,
  stream:  <svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h10M4 18h16"/></svg>,
  menu:    <svg viewBox="0 0 24 24"><path d="M3 6h18M3 12h18M3 18h18"/></svg>,
  more:    <svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/></svg>,
  star:    <svg viewBox="0 0 24 24"><path d="M12 2l3.1 6.3 7 1-5 4.9 1.2 7-6.3-3.3-6.3 3.3 1.2-7-5-4.9 7-1z"/></svg>,
  filter:  <svg viewBox="0 0 24 24"><path d="M3 5h18M6 12h12M10 19h4"/></svg>,
  check:   <svg viewBox="0 0 24 24"><path d="M4 12l5 5L20 6"/></svg>,
  alert:   <svg viewBox="0 0 24 24"><path d="M12 2L2 22h20L12 2z"/><path d="M12 9v6M12 18v.5"/></svg>,
  cash:    <svg viewBox="0 0 24 24"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/></svg>,
  flag:    <svg viewBox="0 0 24 24"><path d="M4 22V4h12l-1 4h5v8H9l1 2v4"/></svg>,
};

// Light icon wrapper — consistent 22px SVG w/ stroke-based styling
function Icon({ name, size=22, stroke=2 }) {
  const svg = TWIcons[name] || null;
  if (!svg) return null;
  return (
    <span className="tw-icon" style={{
      width:size, height:size, display:'inline-flex', alignItems:'center', justifyContent:'center',
      '--stroke': stroke,
    }}>
      {React.cloneElement(svg, { style: {width:size, height:size, stroke:'currentColor', fill:'none', strokeWidth:stroke, strokeLinecap:'round', strokeLinejoin:'round'}})}
    </span>
  );
}

// -----------------------------------------------------------
// StatusBar / TabBar / Header
// -----------------------------------------------------------
function StatusBar({ dark=false, time='9:41' }) {
  return (
    <div style={{
      height:44, display:'flex', alignItems:'center', justifyContent:'space-between',
      padding:'0 22px', fontSize:15, fontWeight:600,
      color: dark ? 'var(--foreground)' : 'var(--foreground)',
      flexShrink:0,
    }}>
      <span>{time}</span>
      <span style={{display:'flex', gap:6, fontSize:12, letterSpacing:'-0.02em'}}>●●●● 5G  ▮▮▮</span>
    </div>
  );
}

function TabBar({ active='home', onChange, items }) {
  const list = items || [
    { k:'home',   label:'홈',          icon:'home' },
    { k:'stock',  label:'종목',         icon:'chart' },
    { k:'folio',  label:'포트폴리오',    icon:'wallet' },
    { k:'stream', label:'스트림',       icon:'stream' },
    { k:'me',     label:'내정보',        icon:'user' },
  ];
  return (
    <div style={{
      position:'absolute', bottom:0, left:0, right:0, height:83,
      borderTop:'1px solid var(--border)',
      display:'flex', justifyContent:'space-around', alignItems:'flex-start',
      padding:'8px 0 0',
      background:'color-mix(in srgb, var(--background) 92%, transparent)',
      backdropFilter:'blur(14px)', WebkitBackdropFilter:'blur(14px)',
      zIndex:2,
    }}>
      {list.map(it => {
        const isActive = it.k===active;
        return (
          <button key={it.k} onClick={()=>onChange&&onChange(it.k)} style={{
            display:'flex', flexDirection:'column', alignItems:'center', gap:3,
            fontSize:10, fontWeight:500,
            color: isActive ? 'var(--primary)' : 'var(--muted-foreground)',
            background:'none', border:0, cursor:'pointer', padding:'2px 8px',
            fontFamily:'inherit',
          }}>
            <Icon name={it.icon} size={22} stroke={isActive?2.2:1.8}/>
            <span>{it.label}</span>
          </button>
        );
      })}
    </div>
  );
}

// -----------------------------------------------------------
// Charts
// -----------------------------------------------------------
function AreaChart({ data, up=true, width=350, height=120, showGrid=true, showDot=true, padTop=12, padBottom=8 }) {
  if (!data || !data.length) return null;
  const color = up ? 'var(--rise)' : 'var(--fall)';
  const n = data.length;
  const sx = (i) => (i/(n-1)) * width;
  const sy = (v) => padTop + (1 - v) * (height - padTop - padBottom);
  const path = data.map((v,i) => (i===0?'M':'L') + sx(i).toFixed(1) + ',' + sy(v).toFixed(1)).join(' ');
  const area = path + ` L${width},${height} L0,${height} Z`;
  const gid = 'area-' + Math.random().toString(36).slice(2,8);
  const lastY = sy(data[n-1]);
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} preserveAspectRatio="none">
      <defs>
        <linearGradient id={gid} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.28"/>
          <stop offset="1" stopColor={color} stopOpacity="0"/>
        </linearGradient>
      </defs>
      {showGrid && [0.25,0.5,0.75].map(f => {
        const y = padTop + f*(height-padTop-padBottom);
        return <line key={f} x1="0" x2={width} y1={y} y2={y} stroke="var(--border)" strokeDasharray="2 4" strokeWidth="1"/>;
      })}
      <path d={area} fill={`url(#${gid})`}/>
      <path d={path} fill="none" stroke={color} strokeWidth="2"/>
      {showDot && (<>
        <circle cx={width-2} cy={lastY} r="8" fill={color} opacity="0.25"/>
        <circle cx={width-2} cy={lastY} r="3.5" fill={color}/>
      </>)}
    </svg>
  );
}

function MiniArea({ data, up=true, width=120, height=32 }) {
  return <AreaChart data={data||[0.4,0.5,0.45,0.6,0.55,0.7,0.72,0.8]} up={up} width={width} height={height} showGrid={false} showDot={false} padTop={2} padBottom={2}/>;
}

function SparkBars({ data, up=true, height=28 }) {
  const color = up ? 'var(--rise)' : 'var(--fall)';
  return (
    <div style={{display:'flex', alignItems:'flex-end', gap:2, height, width:'100%'}}>
      {(data||[0.3,0.5,0.4,0.7,0.6,0.85,0.9]).map((v,i)=>(
        <span key={i} style={{flex:1, height:`${v*100}%`, background:color, opacity:.75, borderRadius:1.5}}/>
      ))}
    </div>
  );
}

// Donut with optional center label
function Donut({ segments, size=96, thickness=12, center }) {
  const r = (size/2) - thickness/2 - 2;
  const C = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div style={{position:'relative', width:size, height:size, flexShrink:0}}>
      <svg width={size} height={size}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--muted)" strokeWidth={thickness}/>
        {segments.map((s,i)=>{
          const len = C*s.pct;
          const el = <circle key={i} cx={size/2} cy={size/2} r={r} fill="none" stroke={s.color} strokeWidth={thickness}
            strokeDasharray={`${len} ${C-len}`} strokeDashoffset={-offset}
            transform={`rotate(-90 ${size/2} ${size/2})`}/>;
          offset += len;
          return el;
        })}
      </svg>
      {center && (
        <div style={{position:'absolute', inset:0, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', textAlign:'center'}}>
          {center}
        </div>
      )}
    </div>
  );
}

function ProgressRing({ pct=0.5, size=76, thickness=8, color='var(--primary)', label }) {
  const r = (size/2)-thickness/2-1;
  const C = 2*Math.PI*r;
  return (
    <div style={{position:'relative', width:size, height:size, flexShrink:0}}>
      <svg width={size} height={size}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--muted)" strokeWidth={thickness}/>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={thickness}
          strokeDasharray={`${C*pct} ${C}`} strokeLinecap="round"
          transform={`rotate(-90 ${size/2} ${size/2})`}/>
      </svg>
      <div style={{position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center', fontSize:size*0.21, fontWeight:800, letterSpacing:'-0.02em'}}>
        {label!==undefined ? label : (pct*100).toFixed(1)+'%'}
      </div>
    </div>
  );
}

function HeatCell({ pct, width=40, height=32 }) {
  // map -5..+5 % to soft fall..rise bg
  const clamped = Math.max(-5, Math.min(5, pct));
  const intensity = Math.abs(clamped)/5;
  const color = clamped >= 0 ? 'var(--rise)' : 'var(--fall)';
  const alpha = 0.12 + intensity*0.55;
  return (
    <div style={{
      width, height, display:'flex', alignItems:'center', justifyContent:'center',
      fontSize:11, fontWeight:700, fontVariantNumeric:'tabular-nums',
      background:`color-mix(in srgb, ${color} ${alpha*100}%, transparent)`,
      color: Math.abs(clamped) > 3 ? '#fff' : color,
      borderRadius:6,
    }}>
      {(clamped>=0?'+':'')+clamped.toFixed(1)}
    </div>
  );
}

// -----------------------------------------------------------
// Cards / Pills / Rows
// -----------------------------------------------------------
function Card({ children, style, padding='14px 16px', className='' }) {
  return (
    <div className={className} style={{
      background:'var(--card)', border:'1px solid var(--border)',
      borderRadius:'var(--radius-xl)', padding, ...style,
    }}>{children}</div>
  );
}

function Pill({ children, tone='neutral', solid=false, style }) {
  const tones = {
    neutral: {bg:'var(--muted)', fg:'var(--foreground)'},
    rise:    {bg:'color-mix(in srgb, var(--rise) 14%, transparent)', fg:'var(--rise)'},
    fall:    {bg:'color-mix(in srgb, var(--fall) 14%, transparent)', fg:'var(--fall)'},
    warn:    {bg:'color-mix(in srgb, #f59e0b 16%, transparent)', fg:'#b45309'},
    ok:      {bg:'color-mix(in srgb, #16a34a 14%, transparent)', fg:'#166534'},
    primary: {bg:'color-mix(in srgb, var(--primary) 14%, transparent)', fg:'var(--primary)'},
  };
  const t = tones[tone] || tones.neutral;
  const s = solid ? { background: t.fg, color:'#fff' } : { background: t.bg, color: t.fg };
  return (
    <span style={{
      display:'inline-flex', alignItems:'center', gap:4,
      padding:'3px 8px', borderRadius:999, fontSize:11, fontWeight:600,
      lineHeight:1.3,
      ...s, ...style,
    }}>{children}</span>
  );
}

// Horizontal row with avatar + text stack + right-aligned value
function HoldingRow({ ticker, name, pct, price, up, sub, sparkData, currency='KRW', dense=false, onClick }) {
  const padding = dense ? '8px 0' : '10px 0';
  return (
    <div onClick={onClick} style={{
      display:'flex', alignItems:'center', gap:12, padding,
      cursor: onClick?'pointer':'default',
    }}>
      <div style={{
        width:36, height:36, borderRadius:8, background:'var(--muted)',
        display:'flex', alignItems:'center', justifyContent:'center',
        fontSize:12, fontWeight:700, color:'var(--muted-foreground)',
        flexShrink:0,
      }}>{name?.[0]||ticker?.[0]}</div>
      <div style={{flex:1, minWidth:0}}>
        <div style={{fontSize:14, fontWeight:600, letterSpacing:'-0.01em', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis'}}>{name}</div>
        <div style={{fontSize:11, color:'var(--muted-foreground)', fontVariantNumeric:'tabular-nums'}}>{sub||ticker}</div>
      </div>
      {sparkData && <div style={{width:64, flexShrink:0}}><MiniArea data={sparkData} up={up} height={22}/></div>}
      <div style={{textAlign:'right', flexShrink:0, minWidth:72}}>
        <div style={{fontSize:14, fontWeight:700, fontVariantNumeric:'tabular-nums',
          color: up?'var(--rise)':'var(--fall)'}}>{pct}</div>
        {price && <div style={{fontSize:11, color:'var(--muted-foreground)', fontVariantNumeric:'tabular-nums'}}>{price}</div>}
      </div>
    </div>
  );
}

// -----------------------------------------------------------
// Phone Frame
// -----------------------------------------------------------
function PhoneFrame({ children, dark=false, width=390, height=844 }) {
  return (
    <div data-theme={dark?'dark':'light'} style={{
      width, height,
      background:'var(--background)', color:'var(--foreground)',
      display:'flex', flexDirection:'column', position:'relative',
      overflow:'hidden',
      fontFamily:'var(--font-sans)',
      fontFeatureSettings:'"tnum"',
      borderRadius: 0, // design_canvas artboard already clips
    }}>{children}</div>
  );
}

// Section label — small uppercase kicker
function SectionLabel({ children, action, style }) {
  return (
    <div style={{
      display:'flex', alignItems:'center', justifyContent:'space-between',
      margin:'22px 0 10px', ...style,
    }}>
      <span className="tw-micro" style={{
        fontSize:11, fontWeight:700, letterSpacing:'0.08em',
        textTransform:'uppercase', color:'var(--muted-foreground)',
      }}>{children}</span>
      {action}
    </div>
  );
}

Object.assign(window, {
  TWIcons, Icon,
  StatusBar, TabBar, PhoneFrame,
  AreaChart, MiniArea, SparkBars, Donut, ProgressRing, HeatCell,
  Card, Pill, HoldingRow, SectionLabel,
});
