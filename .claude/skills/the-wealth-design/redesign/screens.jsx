// ============================================================
// redesign/screens.jsx — five mobile hi-fi screens + web home
//  • HomeLong    — 장기 모드 홈 (hero + 목표 링 + 섹터 + 배당 + 벤치)
//  • HomeShort   — 단타 모드 홈 (mover + 미체결 + 실시간 차트)
//  • Portfolio   — 포트폴리오 상세 (holdings table + sector donut)
//  • StockDetail — 종목 상세 (big chart + 52w + PER/PBR + 주문 액션)
//  • Stream      — 알림/스트림 카드 피드
//  • WebHome     — 1440px 데스크탑 대시보드 홈
// ============================================================

const D = window.TW.mockData;

// -------- Hero: mode toggle + today's change --------
function ModeToggle({ mode, setMode, position='inline' }) {
  const modes = [{k:'long', label:'📚 장기'}, {k:'short', label:'⚡ 단타'}];
  if (position === 'header') {
    return (
      <div style={{display:'flex', gap:4, background:'var(--muted)', borderRadius:8, padding:2}}>
        {modes.map(m=>(
          <button key={m.k} onClick={()=>setMode(m.k)} style={{
            padding:'4px 10px', fontSize:11, fontWeight:700, borderRadius:6,
            border:0, cursor:'pointer', fontFamily:'inherit',
            background: mode===m.k ? 'var(--card)' : 'transparent',
            color: mode===m.k ? 'var(--foreground)' : 'var(--muted-foreground)',
            boxShadow: mode===m.k ? 'var(--shadow-sm)' : 'none',
          }}>{m.label}</button>
        ))}
      </div>
    );
  }
  // inline (big segmented control)
  return (
    <div style={{display:'flex', background:'var(--muted)', borderRadius:10, padding:3, margin:'6px 20px 0'}}>
      {modes.map(m=>{
        const active = mode===m.k;
        const activeBg = m.k==='long' ? 'var(--primary)' : 'var(--rise)';
        return (
          <button key={m.k} onClick={()=>setMode(m.k)} style={{
            flex:1, textAlign:'center', padding:'9px 0',
            fontSize:13, fontWeight:700, borderRadius:8, border:0, cursor:'pointer',
            fontFamily:'inherit',
            background: active ? activeBg : 'transparent',
            color: active ? '#fff' : 'var(--muted-foreground)',
            transition:'background 140ms',
          }}>
            {m.label} {active && <span style={{opacity:.7, marginLeft:4, fontWeight:500, fontSize:11}}>{m.k==='long'?'70%':'30%'}</span>}
          </button>
        );
      })}
    </div>
  );
}

// =============================================================
// Screen 1 · Home · Long mode  (HYBRID: D1 hero + D3 goal + D4 tasks + bench)
// =============================================================
function HomeLong({ setScreen, setMode }) {
  const s = D.portfolioSummaries.p1;
  return (
    <>
      <StatusBar/>
      <div style={{padding:'0 20px', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <div style={{display:'flex', gap:10, alignItems:'baseline'}}>
          <span style={{fontSize:22, fontWeight:800, letterSpacing:'-0.02em'}}>The Wealth</span>
          <span style={{fontSize:11, color:'var(--muted-foreground)'}}>14:32 · 실시간</span>
        </div>
        <div style={{display:'flex', gap:8, alignItems:'center'}}>
          <ModeToggle mode="long" setMode={setMode} position="header"/>
        </div>
      </div>

      <div style={{flex:1, overflow:'hidden auto', padding:'0 20px 110px'}}>
        {/* HERO — total + today change (D1 북극성) */}
        <div style={{padding:'18px 0 4px'}}>
          <div className="tw-micro" style={{fontSize:11, color:'var(--muted-foreground)'}}>총 평가금액 · KRW</div>
          <div style={{fontSize:36, fontWeight:800, letterSpacing:'-0.025em', marginTop:2, fontVariantNumeric:'tabular-nums'}}>
            {D.fmt.krw(D.totalValueKRW)}
          </div>
          <div style={{display:'flex', alignItems:'center', gap:8, marginTop:4}}>
            <span style={{color:'var(--rise)', fontSize:15, fontWeight:700, fontVariantNumeric:'tabular-nums'}}>
              +{D.fmt.krw(D.dayChangeTotal)}
            </span>
            <Pill tone="rise">+1.84% 오늘</Pill>
          </div>
        </div>

        {/* Chart — 1M daily line */}
        <div style={{margin:'14px -6px 0'}}>
          <AreaChart data={D.dailySeries} up={true} height={120} width={360}/>
          <div style={{display:'flex', gap:4, justifyContent:'center', marginTop:6}}>
            {['1일','1주','1달','3달','1년','전체'].map((l,i)=>(
              <span key={l} style={{
                padding:'4px 10px', fontSize:11, fontWeight:600, borderRadius:6,
                background: i===2 ? 'var(--primary)' : 'transparent',
                color: i===2 ? '#fff' : 'var(--muted-foreground)',
              }}>{l}</span>
            ))}
          </div>
        </div>

        {/* Goal ring (D3) + Benchmark mini (D2) — dual card row */}
        <SectionLabel>목표 · 벤치마크</SectionLabel>
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:10}}>
          <Card padding="14px" style={{display:'flex', gap:12, alignItems:'center'}}>
            <ProgressRing pct={s.target_progress} size={64} thickness={7} label={(s.target_progress*100).toFixed(0)+'%'}/>
            <div style={{minWidth:0}}>
              <div className="tw-micro" style={{fontSize:10, color:'var(--muted-foreground)'}}>2억 목표</div>
              <div style={{fontSize:13, fontWeight:700, fontVariantNumeric:'tabular-nums'}}>남은 70,550k</div>
              <div style={{fontSize:10, color:'var(--muted-foreground)'}}>예상 14개월</div>
            </div>
          </Card>
          <Card padding="14px">
            <div className="tw-micro" style={{fontSize:10, color:'var(--muted-foreground)'}}>vs KOSPI200</div>
            <div style={{display:'flex', alignItems:'baseline', gap:6, marginTop:2}}>
              <span style={{fontSize:18, fontWeight:700, color:'var(--rise)', fontVariantNumeric:'tabular-nums'}}>+3.3%p</span>
            </div>
            <div style={{fontSize:10, color:'var(--muted-foreground)'}}>내 +6.4% · 벤치 +3.1% (6M)</div>
            <div style={{marginTop:6, height:22}}>
              <svg viewBox="0 0 140 22" width="100%" height="22" preserveAspectRatio="none">
                <polyline points={D.benchmarkSeries.kospi200.map((v,i,a)=>`${i/(a.length-1)*140},${22 - v*3}`).join(' ')}
                  fill="none" stroke="var(--muted-foreground)" strokeWidth="1.4" strokeDasharray="2 2" opacity=".6"/>
                <polyline points={D.benchmarkSeries.mine.map((v,i,a)=>`${i/(a.length-1)*140},${22 - v*2.5}`).join(' ')}
                  fill="none" stroke="var(--rise)" strokeWidth="2"/>
              </svg>
            </div>
          </Card>
        </div>

        {/* Today tasks (D4 카드 피드의 홈 에디션) */}
        <SectionLabel action={<span style={{fontSize:11, color:'var(--primary)', fontWeight:600}}>모두 보기</span>}>
          오늘 할 것 · 3
        </SectionLabel>
        <div style={{display:'flex', flexDirection:'column', gap:8}}>
          {D.tasks.map((t,i)=>(
            <Card key={i} padding="12px 14px">
              <div style={{display:'flex', gap:12, alignItems:'center'}}>
                <div style={{width:32, height:32, borderRadius:8,
                  background:`color-mix(in srgb, ${t.color} 15%, transparent)`,
                  color:t.color, display:'flex', alignItems:'center', justifyContent:'center', fontWeight:800, fontSize:15, flexShrink:0}}>{t.icon}</div>
                <div style={{flex:1, minWidth:0}}>
                  <div style={{fontSize:13, fontWeight:600, letterSpacing:'-0.01em'}}>{t.title}</div>
                  <div style={{fontSize:11, color:'var(--muted-foreground)', marginTop:1}}>{t.sub}</div>
                </div>
                <Icon name="arrow" size={16}/>
              </div>
            </Card>
          ))}
        </div>

        {/* Sector donut (D3) */}
        <SectionLabel>자산 배분</SectionLabel>
        <Card padding="14px" style={{display:'flex', gap:14, alignItems:'center'}}>
          <Donut
            size={96} thickness={14}
            segments={D.sectorAllocation.map(s=>({pct:s.pct, color:s.color}))}
            center={<div><div style={{fontSize:10, color:'var(--muted-foreground)', letterSpacing:'0.04em'}}>섹터</div><div style={{fontSize:13, fontWeight:700}}>{D.sectorAllocation.length}</div></div>}
          />
          <div style={{flex:1, display:'grid', gridTemplateColumns:'1fr', gap:6}}>
            {D.sectorAllocation.slice(0,4).map((r,i)=>(
              <div key={i} style={{display:'flex', alignItems:'center', gap:8, fontSize:12}}>
                <span style={{width:8, height:8, borderRadius:2, background:r.color, flexShrink:0}}/>
                <span style={{flex:1, whiteSpace:'nowrap'}}>{r.sector}</span>
                <span style={{fontWeight:700, fontVariantNumeric:'tabular-nums'}}>{(r.pct*100).toFixed(0)}%</span>
                {r.pct > r.target + 0.03 && <Pill tone="rise" style={{fontSize:9, padding:'1px 5px'}}>+{((r.pct-r.target)*100).toFixed(0)}%p</Pill>}
              </div>
            ))}
          </div>
        </Card>

        {/* Top movers (D1) */}
        <SectionLabel action={<span style={{fontSize:11, color:'var(--primary)', fontWeight:600}}>전체</span>}>
          오늘의 mover
        </SectionLabel>
        <Card padding="4px 14px">
          {D.movers.slice(0,4).map((m,i)=>(
            <div key={m.ticker} style={{borderTop: i===0?0:'1px solid var(--border)'}}>
              <HoldingRow
                name={m.name} ticker={m.ticker}
                pct={(m.pct>=0?'+':'')+m.pct.toFixed(2)+'%'}
                price={m.price} up={m.up} sub={m.ticker}
                onClick={()=>setScreen('stock')}
              />
            </div>
          ))}
        </Card>

        {/* Dividends */}
        <SectionLabel>다음 배당 · {D.dividends.length}</SectionLabel>
        <Card padding="4px 14px">
          {D.dividends.map((d,i)=>(
            <div key={d.ticker} style={{
              display:'flex', alignItems:'center', justifyContent:'space-between',
              padding:'10px 0', borderTop: i===0?0:'1px solid var(--border)',
            }}>
              <div>
                <div style={{fontSize:13, fontWeight:600}}>{d.name}</div>
                <div style={{fontSize:11, color:'var(--muted-foreground)', fontVariantNumeric:'tabular-nums'}}>배당락 {d.ex_date} · 지급 {d.payment_date}</div>
              </div>
              <div style={{fontSize:13, fontWeight:700, color:'var(--rise)', fontVariantNumeric:'tabular-nums'}}>
                +{d.currency==='KRW' ? d.amount.toLocaleString() : '$'+d.amount.toFixed(2)}
              </div>
            </div>
          ))}
        </Card>
      </div>
    </>
  );
}

// =============================================================
// Screen 2 · Home · Short mode
// =============================================================
function HomeShort({ setScreen, setMode }) {
  const s = D.portfolioSummaries.p2;
  return (
    <>
      <StatusBar/>
      <div style={{padding:'0 20px', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <div style={{display:'flex', gap:10, alignItems:'baseline'}}>
          <span style={{fontSize:22, fontWeight:800, letterSpacing:'-0.02em'}}>The Wealth</span>
          <Pill tone="rise" solid style={{fontSize:9, padding:'2px 6px'}}>LIVE</Pill>
        </div>
        <ModeToggle mode="short" setMode={setMode} position="header"/>
      </div>

      <div style={{flex:1, overflow:'hidden auto', padding:'0 20px 110px'}}>
        {/* HERO — aggressive realtime framing */}
        <div style={{padding:'18px 0 4px'}}>
          <div className="tw-micro" style={{fontSize:11, color:'var(--muted-foreground)'}}>단타 계좌 · 오늘</div>
          <div style={{fontSize:36, fontWeight:800, letterSpacing:'-0.025em', color:'var(--rise)', fontVariantNumeric:'tabular-nums'}}>
            +{D.fmt.krw(s.day_change_amount)}
          </div>
          <div style={{display:'flex', alignItems:'center', gap:8, marginTop:4}}>
            <span style={{color:'var(--rise)', fontSize:15, fontWeight:700}}>+{s.day_change_pct}%</span>
            <span style={{fontSize:12, color:'var(--muted-foreground)', fontVariantNumeric:'tabular-nums'}}>
              총 {D.fmt.krw(s.total_value)}
            </span>
          </div>
        </div>

        {/* Intraday realtime chart */}
        <div style={{margin:'12px -6px 0'}}>
          <AreaChart data={D.intradaySeries} up={true} height={140} width={360}/>
          <div style={{display:'flex', justifyContent:'space-between', fontSize:10, color:'var(--muted-foreground)', padding:'2px 6px', fontVariantNumeric:'tabular-nums'}}>
            <span>09:00</span><span>10:30</span><span>12:00</span><span>13:30</span><span>현재</span>
          </div>
        </div>

        {/* Quick action row */}
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr 1fr', gap:8, marginTop:14}}>
          {[
            {label:'매수', tone:'rise', solid:true},
            {label:'매도', tone:'fall', solid:true},
            {label:'알림', tone:'primary'},
            {label:'전체', tone:'neutral'},
          ].map(a=>(
            <button key={a.label} style={{
              padding:'10px 0', borderRadius:10, border:0, cursor:'pointer',
              fontFamily:'inherit', fontWeight:700, fontSize:13,
              background: a.solid ? (a.tone==='rise'?'var(--rise)':'var(--fall)')
                : a.tone==='primary' ? 'color-mix(in srgb, var(--primary) 14%, transparent)' : 'var(--muted)',
              color: a.solid ? '#fff' : (a.tone==='primary'?'var(--primary)':'var(--foreground)'),
            }}>{a.label}</button>
          ))}
        </div>

        {/* Pending orders */}
        <SectionLabel action={<Pill tone="warn">{s.unfilled_orders}건 대기</Pill>}>
          미체결 주문
        </SectionLabel>
        <Card padding="4px 14px">
          {D.orders.filter(o=>o.status==='pending').map((o,i)=>(
            <div key={o.id} style={{
              display:'flex', alignItems:'center', gap:10, padding:'12px 0',
              borderTop: i===0?0:'1px solid var(--border)',
            }}>
              <Pill tone={o.type==='BUY'?'rise':'fall'} solid style={{fontSize:10, padding:'3px 7px', minWidth:30, justifyContent:'center'}}>
                {o.type==='BUY'?'매수':'매도'}
              </Pill>
              <div style={{flex:1, minWidth:0}}>
                <div style={{fontSize:13, fontWeight:600}}>{o.name}</div>
                <div style={{fontSize:11, color:'var(--muted-foreground)', fontVariantNumeric:'tabular-nums'}}>
                  {o.qty}주 @ {typeof o.limit === 'number' && o.limit<1000?'$'+o.limit.toFixed(2):o.limit.toLocaleString()}
                </div>
              </div>
              <span style={{fontSize:11, color:'#b45309', fontWeight:700}}>● 대기 {o.ts}</span>
            </div>
          ))}
        </Card>

        {/* Top movers */}
        <SectionLabel action={<Icon name="filter" size={16}/>}>
          Top mover
        </SectionLabel>
        <Card padding="4px 14px">
          {D.movers.map((m,i)=>(
            <div key={m.ticker} style={{borderTop: i===0?0:'1px solid var(--border)'}}>
              <HoldingRow
                name={m.name} ticker={m.ticker}
                pct={(m.pct>=0?'+':'')+m.pct.toFixed(2)+'%'}
                price={m.price} up={m.up}
                sparkData={m.up?[0.3,0.4,0.35,0.5,0.55,0.7,0.75,0.85]:[0.8,0.75,0.7,0.6,0.55,0.45,0.4,0.3]}
                onClick={()=>setScreen('stock')}
              />
            </div>
          ))}
        </Card>

        {/* Triggered alerts */}
        <SectionLabel>알림 · 오늘 {D.alerts.length}건</SectionLabel>
        <Card padding="4px 14px">
          {D.alerts.map((a,i)=>(
            <div key={a.id} style={{
              display:'flex', alignItems:'center', gap:10, padding:'10px 0',
              borderTop: i===0?0:'1px solid var(--border)',
            }}>
              <Icon name="alert" size={18}/>
              <div style={{flex:1}}>
                <div style={{fontSize:12, fontWeight:600}}>
                  {a.name} — {a.condition==='above'?'이상':'이하'} {typeof a.threshold==='number'&&a.threshold<1000?'$'+a.threshold:a.threshold.toLocaleString()} 도달
                </div>
                <div style={{fontSize:10, color:'var(--muted-foreground)', fontVariantNumeric:'tabular-nums'}}>{a.ts} · 현재 {typeof a.current==='number'&&a.current<1000?'$'+a.current:a.current.toLocaleString()}</div>
              </div>
            </div>
          ))}
        </Card>
      </div>
    </>
  );
}

// =============================================================
// Screen 3 · Portfolio detail
// =============================================================
function PortfolioScreen({ setScreen, setMode }) {
  const folio = D.portfolios[0];
  const holdings = D.holdings.filter(h=>h.pid==='p1').map(h=>{
    const val = h.quantity * h.current_price;
    const principal = h.quantity * h.avg_price;
    const gain = val - principal;
    const pct = (gain/principal) * 100;
    return {...h, value: val, principal, gain, pct};
  }).sort((a,b)=> b.value - a.value);
  const total = holdings.reduce((s,h)=>s+h.value, 0);

  return (
    <>
      <StatusBar/>
      <div style={{padding:'0 20px', display:'flex', alignItems:'center', gap:8}}>
        <button onClick={()=>setScreen('home')} style={{background:'none',border:0,padding:4,cursor:'pointer',color:'var(--foreground)'}}><Icon name="back" size={22}/></button>
        <div style={{flex:1, minWidth:0}}>
          <div style={{fontSize:11, color:'var(--muted-foreground)', letterSpacing:'0.04em'}}>포트폴리오 · ISA</div>
          <div style={{fontSize:16, fontWeight:700, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis'}}>{folio.name}</div>
        </div>
        <Icon name="more" size={22}/>
      </div>
      <div style={{flex:1, overflow:'hidden auto', padding:'0 20px 110px'}}>
        {/* Summary strip */}
        <Card padding="16px" style={{marginTop:12}}>
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline'}}>
            <span className="tw-micro" style={{fontSize:10, color:'var(--muted-foreground)'}}>평가금액</span>
            <span style={{fontSize:11, color:'var(--muted-foreground)', fontVariantNumeric:'tabular-nums'}}>원금 85,204k</span>
          </div>
          <div style={{fontSize:28, fontWeight:800, letterSpacing:'-0.02em', fontVariantNumeric:'tabular-nums', marginTop:2}}>
            {D.fmt.krw(90_615_000)}
          </div>
          <div style={{display:'flex', gap:16, marginTop:10, paddingTop:10, borderTop:'1px solid var(--border)'}}>
            <div>
              <div style={{fontSize:10, color:'var(--muted-foreground)'}}>총 손익</div>
              <div style={{fontSize:14, fontWeight:700, color:'var(--rise)', fontVariantNumeric:'tabular-nums'}}>+5,411k</div>
              <div style={{fontSize:10, color:'var(--rise)'}}>+6.35%</div>
            </div>
            <div>
              <div style={{fontSize:10, color:'var(--muted-foreground)'}}>오늘</div>
              <div style={{fontSize:14, fontWeight:700, color:'var(--rise)', fontVariantNumeric:'tabular-nums'}}>+1,284k</div>
              <div style={{fontSize:10, color:'var(--rise)'}}>+1.44%</div>
            </div>
            <div style={{marginLeft:'auto', display:'flex', alignItems:'center'}}>
              <div style={{width:50, height:30}}><MiniArea data={D.dailySeries.slice(-15)} up={true} height={30}/></div>
            </div>
          </div>
        </Card>

        {/* Sector mini with progress vs target */}
        <SectionLabel action={<span style={{fontSize:11, color:'var(--primary)', fontWeight:600}}>리밸런싱 →</span>}>
          섹터 현재 vs 목표
        </SectionLabel>
        <Card padding="14px 16px">
          <div style={{display:'flex', flexDirection:'column', gap:10}}>
            {D.sectorAllocation.slice(0,4).map((r,i)=>(
              <div key={i}>
                <div style={{display:'flex', justifyContent:'space-between', fontSize:12, marginBottom:4, fontVariantNumeric:'tabular-nums'}}>
                  <span style={{fontWeight:600}}>{r.sector}</span>
                  <span>
                    <span style={{fontWeight:700}}>{(r.pct*100).toFixed(0)}%</span>
                    <span style={{color:'var(--muted-foreground)'}}> / 목표 {(r.target*100).toFixed(0)}%</span>
                  </span>
                </div>
                <div style={{position:'relative', height:6, background:'var(--muted)', borderRadius:3, overflow:'hidden'}}>
                  <div style={{position:'absolute', left:0, top:0, bottom:0, width:`${r.pct*100}%`, background:r.color, borderRadius:3}}/>
                  <div style={{position:'absolute', left:`${r.target*100}%`, top:-2, bottom:-2, width:2, background:'var(--foreground)', opacity:.5}}/>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Holdings */}
        <SectionLabel action={<span style={{fontSize:11, color:'var(--muted-foreground)'}}>가치 순</span>}>
          보유 {holdings.length}종목
        </SectionLabel>
        <Card padding="4px 14px">
          {holdings.map((h,i)=>{
            const weight = h.value/total;
            return (
              <div key={h.ticker} style={{
                padding:'10px 0', borderTop: i===0?0:'1px solid var(--border)',
                display:'flex', alignItems:'center', gap:10,
              }} onClick={()=>setScreen('stock')}>
                <div style={{width:34, height:34, borderRadius:8, background:'var(--muted)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:11, fontWeight:700, color:'var(--muted-foreground)', flexShrink:0}}>{h.name[0]}</div>
                <div style={{flex:1, minWidth:0}}>
                  <div style={{fontSize:13, fontWeight:600, letterSpacing:'-0.01em'}}>
                    {h.name}
                    <span style={{marginLeft:6, fontSize:10, color:'var(--muted-foreground)', fontWeight:500, fontVariantNumeric:'tabular-nums'}}>{(weight*100).toFixed(0)}%</span>
                  </div>
                  <div style={{fontSize:11, color:'var(--muted-foreground)', fontVariantNumeric:'tabular-nums'}}>{h.quantity}주 · 평단 {h.avg_price.toLocaleString()}</div>
                </div>
                <div style={{textAlign:'right', minWidth:80}}>
                  <div style={{fontSize:13, fontWeight:700, fontVariantNumeric:'tabular-nums'}}>{h.current_price.toLocaleString()}</div>
                  <div style={{fontSize:11, fontWeight:700, color: h.pct>=0?'var(--rise)':'var(--fall)', fontVariantNumeric:'tabular-nums'}}>
                    {(h.pct>=0?'+':'')+h.pct.toFixed(2)+'%'}
                  </div>
                </div>
              </div>
            );
          })}
        </Card>

        {/* Monthly heatmap */}
        <SectionLabel>월별 수익률</SectionLabel>
        <Card padding="14px 16px">
          <div style={{display:'grid', gridTemplateColumns:'repeat(6, 1fr)', gap:6}}>
            {D.monthlyReturns.map((m,i)=>(
              <div key={i} style={{display:'flex', flexDirection:'column', alignItems:'center', gap:4}}>
                <HeatCell pct={m.pct} width={44} height={36}/>
                <div style={{fontSize:10, color:'var(--muted-foreground)', fontVariantNumeric:'tabular-nums'}}>{m.ym.slice(-2)}월</div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </>
  );
}

// =============================================================
// Screen 4 · Stock detail (big chart + actions)
// =============================================================
function StockDetail({ setScreen }) {
  const s = D.stockDetail;
  const rangePos = (s.current_price - s.w52_low) / (s.w52_high - s.w52_low);
  return (
    <>
      <StatusBar/>
      <div style={{padding:'0 20px', display:'flex', alignItems:'center', gap:8}}>
        <button onClick={()=>setScreen('home')} style={{background:'none',border:0,padding:4,cursor:'pointer',color:'var(--foreground)'}}><Icon name="back" size={22}/></button>
        <div style={{flex:1, minWidth:0}}>
          <div style={{fontSize:15, fontWeight:700}}>{s.name}</div>
          <div style={{fontSize:11, color:'var(--muted-foreground)', fontVariantNumeric:'tabular-nums'}}>{s.ticker} · {s.market}</div>
        </div>
        <Icon name="star" size={22}/>
        <Icon name="alert" size={22}/>
      </div>

      <div style={{flex:1, overflow:'hidden auto', padding:'0 20px 170px'}}>
        {/* Price hero */}
        <div style={{padding:'16px 0 4px'}}>
          <div style={{fontSize:32, fontWeight:800, letterSpacing:'-0.025em', fontVariantNumeric:'tabular-nums'}}>
            {s.current_price.toLocaleString()}<span style={{fontSize:16, fontWeight:500, color:'var(--muted-foreground)', marginLeft:4}}>KRW</span>
          </div>
          <div style={{display:'flex', alignItems:'center', gap:8, marginTop:4}}>
            <span style={{color:'var(--rise)', fontSize:14, fontWeight:700, fontVariantNumeric:'tabular-nums'}}>+{s.day_change_amount.toLocaleString()}</span>
            <Pill tone="rise">+{s.day_change_pct}%</Pill>
            <span style={{fontSize:11, color:'var(--muted-foreground)'}}>오늘</span>
          </div>
        </div>

        {/* Big chart */}
        <div style={{margin:'10px -6px 0'}}>
          <AreaChart data={D.intradaySeries} up={true} height={180} width={360}/>
          <div style={{display:'flex', gap:4, justifyContent:'center', marginTop:6}}>
            {['1일','1주','1달','3달','1년','전체'].map((l,i)=>(
              <span key={l} style={{
                padding:'5px 12px', fontSize:12, fontWeight:600, borderRadius:6,
                background: i===0 ? 'var(--primary)' : 'transparent',
                color: i===0 ? '#fff' : 'var(--muted-foreground)',
              }}>{l}</span>
            ))}
          </div>
        </div>

        {/* 52w range */}
        <SectionLabel>52주 레인지</SectionLabel>
        <Card padding="14px 16px">
          <div style={{position:'relative', height:6, background:'var(--muted)', borderRadius:3}}>
            <div style={{position:'absolute', left:0, top:0, bottom:0, width:`${rangePos*100}%`,
              background:'linear-gradient(90deg, var(--fall), var(--flat), var(--rise))', borderRadius:3, opacity:.8}}/>
            <div style={{position:'absolute', left:`calc(${rangePos*100}% - 8px)`, top:-5, width:16, height:16, borderRadius:8, background:'var(--foreground)', border:'3px solid var(--card)', boxShadow:'var(--shadow-sm)'}}/>
          </div>
          <div style={{display:'flex', justifyContent:'space-between', marginTop:8, fontSize:11, fontVariantNumeric:'tabular-nums'}}>
            <div><div style={{color:'var(--muted-foreground)', fontSize:10}}>저가</div><div style={{color:'var(--fall)', fontWeight:700}}>{s.w52_low.toLocaleString()}</div></div>
            <div style={{textAlign:'center'}}><div style={{color:'var(--muted-foreground)', fontSize:10}}>현재</div><div style={{fontWeight:700}}>{s.current_price.toLocaleString()}</div></div>
            <div style={{textAlign:'right'}}><div style={{color:'var(--muted-foreground)', fontSize:10}}>고가</div><div style={{color:'var(--rise)', fontWeight:700}}>{s.w52_high.toLocaleString()}</div></div>
          </div>
        </Card>

        {/* Key metrics grid */}
        <SectionLabel>핵심 지표</SectionLabel>
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:8}}>
          {[
            {l:'시가총액', v:s.market_cap},
            {l:'거래량', v:s.volume},
            {l:'PER', v:s.per.toFixed(1)},
            {l:'PBR', v:s.pbr.toFixed(2)},
            {l:'배당률', v:s.dividend_yield.toFixed(2)+'%'},
            {l:'섹터', v:'IT'},
          ].map((m,i)=>(
            <Card key={i} padding="10px 12px">
              <div style={{fontSize:10, color:'var(--muted-foreground)', letterSpacing:'0.04em'}}>{m.l}</div>
              <div style={{fontSize:14, fontWeight:700, marginTop:2, fontVariantNumeric:'tabular-nums'}}>{m.v}</div>
            </Card>
          ))}
        </div>

        {/* My holding in this stock */}
        <SectionLabel>내 보유</SectionLabel>
        <Card padding="14px 16px" style={{display:'flex', gap:16}}>
          <div style={{flex:1}}>
            <div style={{fontSize:10, color:'var(--muted-foreground)'}}>수량 · 평단</div>
            <div style={{fontSize:15, fontWeight:700, fontVariantNumeric:'tabular-nums'}}>430주 · 68,500</div>
          </div>
          <div style={{flex:1, textAlign:'right'}}>
            <div style={{fontSize:10, color:'var(--muted-foreground)'}}>평가손익</div>
            <div style={{fontSize:15, fontWeight:700, color:'var(--rise)', fontVariantNumeric:'tabular-nums'}}>+1,677,000</div>
            <div style={{fontSize:11, color:'var(--rise)'}}>+5.69%</div>
          </div>
        </Card>
      </div>

      {/* Sticky buy/sell */}
      <div style={{position:'absolute', left:0, right:0, bottom:83, padding:'10px 20px 12px',
        background:'color-mix(in srgb, var(--background) 92%, transparent)', backdropFilter:'blur(14px)',
        borderTop:'1px solid var(--border)',
        display:'flex', gap:10, zIndex:1}}>
        <button style={{flex:1, padding:'14px 0', borderRadius:12, border:0, background:'var(--rise)', color:'#fff', fontSize:15, fontWeight:700, fontFamily:'inherit', cursor:'pointer'}}>매수</button>
        <button style={{flex:1, padding:'14px 0', borderRadius:12, border:0, background:'var(--fall)', color:'#fff', fontSize:15, fontWeight:700, fontFamily:'inherit', cursor:'pointer'}}>매도</button>
      </div>
    </>
  );
}

// =============================================================
// Screen 5 · Stream / notifications feed
// =============================================================
function StreamScreen({ setScreen }) {
  const filters = ['전체','알림','체결','리밸런싱','배당'];
  return (
    <>
      <StatusBar/>
      <div style={{padding:'0 20px', display:'flex', alignItems:'center', gap:8}}>
        <span style={{fontSize:22, fontWeight:800, letterSpacing:'-0.02em', flex:1}}>스트림</span>
        <Icon name="filter" size={22}/>
        <Icon name="search" size={22}/>
      </div>
      {/* Filter chips */}
      <div style={{padding:'10px 20px 4px', display:'flex', gap:6, overflowX:'auto', flexShrink:0}}>
        {filters.map((f,i)=>(
          <span key={f} style={{
            padding:'6px 12px', fontSize:12, fontWeight:600, borderRadius:999,
            background: i===0 ? 'var(--foreground)' : 'var(--muted)',
            color: i===0 ? 'var(--background)' : 'var(--muted-foreground)',
            flexShrink:0,
          }}>{f}</span>
        ))}
      </div>

      <div style={{flex:1, overflow:'hidden auto', padding:'12px 20px 110px', display:'flex', flexDirection:'column', gap:10}}>
        {/* Card: alert triggered */}
        <Card padding="12px 14px" style={{borderLeft:'3px solid var(--rise)'}}>
          <div style={{display:'flex', alignItems:'center', gap:6, marginBottom:6}}>
            <Pill tone="rise" solid style={{fontSize:10}}>🔔 목표가 도달</Pill>
            <span style={{fontSize:10, color:'var(--muted-foreground)', marginLeft:'auto', fontVariantNumeric:'tabular-nums'}}>14:32 · 방금</span>
          </div>
          <div style={{fontSize:14, fontWeight:700}}>NVIDIA — $145 돌파</div>
          <div style={{fontSize:11, color:'var(--muted-foreground)', marginTop:2, fontVariantNumeric:'tabular-nums'}}>목표 $140 이상 · 현재 $145.22 (+3.42%)</div>
          <div style={{display:'flex', gap:6, marginTop:10}}>
            <button style={{flex:1, padding:'8px 0', fontSize:12, fontWeight:600, borderRadius:8, border:'1px solid var(--border)', background:'var(--card)', color:'var(--foreground)', cursor:'pointer'}}>종목 보기</button>
            <button style={{flex:1, padding:'8px 0', fontSize:12, fontWeight:700, borderRadius:8, border:0, background:'var(--rise)', color:'#fff', cursor:'pointer'}}>매도 주문</button>
          </div>
        </Card>

        {/* Card: rebalancing */}
        <Card padding="12px 14px">
          <div style={{display:'flex', alignItems:'center', gap:6, marginBottom:6}}>
            <Pill tone="warn">⚖ 리밸런싱 제안</Pill>
            <span style={{fontSize:10, color:'var(--muted-foreground)', marginLeft:'auto'}}>09:00 · 5시간 전</span>
          </div>
          <div style={{fontSize:14, fontWeight:700}}>IT 섹터 45% · 목표 30% 초과</div>
          <div style={{fontSize:11, color:'var(--muted-foreground)', marginTop:2}}>15%p 차이 · 삼성전자 일부 정리 권장</div>
          <div style={{marginTop:10, height:8, background:'var(--muted)', borderRadius:4, position:'relative', overflow:'hidden'}}>
            <div style={{position:'absolute', left:0, top:0, bottom:0, width:'45%', background:'var(--rise)', opacity:.8, borderRadius:4}}/>
            <div style={{position:'absolute', left:'30%', top:-2, bottom:-2, width:2, background:'var(--foreground)', opacity:.6}}/>
          </div>
        </Card>

        {/* Card: order filled */}
        <Card padding="12px 14px">
          <div style={{display:'flex', alignItems:'center', gap:6, marginBottom:6}}>
            <Pill tone="ok">✓ 체결 완료</Pill>
            <span style={{fontSize:10, color:'var(--muted-foreground)', marginLeft:'auto'}}>09:12 · 오늘</span>
          </div>
          <div style={{display:'flex', alignItems:'center'}}>
            <div style={{flex:1}}>
              <div style={{fontSize:14, fontWeight:700}}>삼성전자 매수</div>
              <div style={{fontSize:11, color:'var(--muted-foreground)', fontVariantNumeric:'tabular-nums'}}>10주 @ 72,400</div>
            </div>
            <span style={{fontSize:14, fontWeight:700, fontVariantNumeric:'tabular-nums'}}>724,000</span>
          </div>
        </Card>

        {/* Card: dividend upcoming */}
        <Card padding="12px 14px">
          <div style={{display:'flex', alignItems:'center', gap:6, marginBottom:6}}>
            <Pill tone="primary">💰 배당 예정</Pill>
            <span style={{fontSize:10, color:'var(--muted-foreground)', marginLeft:'auto'}}>4/28 예정</span>
          </div>
          <div style={{display:'flex', alignItems:'center'}}>
            <div style={{flex:1}}>
              <div style={{fontSize:14, fontWeight:700}}>삼성전자 분기배당</div>
              <div style={{fontSize:11, color:'var(--muted-foreground)'}}>430주 보유 · 배당락 4거래일</div>
            </div>
            <span style={{fontSize:14, fontWeight:700, color:'var(--rise)', fontVariantNumeric:'tabular-nums'}}>+36,000</span>
          </div>
        </Card>

        {/* Card: routine */}
        <Card padding="12px 14px" style={{background:'var(--muted)', border:'1px dashed var(--border)'}}>
          <div style={{display:'flex', alignItems:'center', gap:6, marginBottom:6}}>
            <Pill tone="neutral">📋 루틴</Pill>
            <span style={{fontSize:10, color:'var(--muted-foreground)', marginLeft:'auto'}}>매월 말일</span>
          </div>
          <div style={{fontSize:13, fontWeight:600}}>월 리밸런싱 체크</div>
          <div style={{fontSize:11, color:'var(--muted-foreground)', marginTop:2}}>포트폴리오 3개 · 섹터 비중 · 투자일지 정리</div>
          <button style={{marginTop:10, padding:'8px 14px', fontSize:12, fontWeight:700, borderRadius:8, border:0, background:'var(--primary)', color:'#fff', cursor:'pointer'}}>체크 시작</button>
        </Card>
      </div>
    </>
  );
}

Object.assign(window, { ModeToggle, HomeLong, HomeShort, PortfolioScreen, StockDetail, StreamScreen });
