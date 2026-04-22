// ============================================================
// redesign/web.jsx — Desktop dashboard (1440px) HomeWeb
// ============================================================
const DW = window.TW.mockData;

function WebHome({ dark=false }) {
  return (
    <div data-theme={dark?'dark':'light'} style={{
      width:1440, height:900, background:'var(--background)', color:'var(--foreground)',
      display:'flex', fontFamily:'var(--font-sans)', overflow:'hidden',
    }}>
      {/* Sidebar */}
      <aside style={{width:220, borderRight:'1px solid var(--border)', padding:'22px 16px', display:'flex', flexDirection:'column', gap:4, background:'var(--card)'}}>
        <div style={{display:'flex', alignItems:'center', gap:10, padding:'0 8px 18px'}}>
          <div style={{width:28, height:28, borderRadius:7, background:'var(--primary)', color:'#fff', display:'flex', alignItems:'center', justifyContent:'center', fontWeight:800}}>W</div>
          <span style={{fontSize:16, fontWeight:800, letterSpacing:'-0.02em'}}>The Wealth</span>
        </div>
        {[
          {k:'home', l:'홈', icon:'home', active:true},
          {k:'folio', l:'포트폴리오', icon:'wallet'},
          {k:'stock', l:'종목', icon:'chart'},
          {k:'stream', l:'스트림', icon:'stream'},
          {k:'rebal', l:'리밸런싱', icon:'layers'},
          {k:'journal', l:'투자일지', icon:'flag'},
          {k:'me', l:'설정', icon:'user'},
        ].map(it=>(
          <div key={it.k} style={{
            display:'flex', alignItems:'center', gap:10, padding:'9px 10px', borderRadius:8,
            fontSize:13, fontWeight:it.active?700:500,
            background: it.active?'color-mix(in srgb, var(--primary) 12%, transparent)':'transparent',
            color: it.active?'var(--primary)':'var(--foreground)',
          }}>
            <Icon name={it.icon} size={18}/>
            <span>{it.l}</span>
          </div>
        ))}
        <div style={{marginTop:'auto', padding:12, borderRadius:10, background:'var(--muted)', fontSize:11}}>
          <div style={{color:'var(--muted-foreground)'}}>KIS 연동</div>
          <div style={{color:'var(--rise)', fontWeight:700, marginTop:2}}>● 실시간 연결</div>
        </div>
      </aside>

      {/* Main */}
      <div style={{flex:1, overflow:'hidden', display:'flex', flexDirection:'column'}}>
        {/* Topbar */}
        <header style={{height:60, borderBottom:'1px solid var(--border)', display:'flex', alignItems:'center', padding:'0 32px', gap:16}}>
          <h1 style={{fontSize:18, fontWeight:700, margin:0, letterSpacing:'-0.01em'}}>홈</h1>
          <div style={{display:'flex', gap:4, background:'var(--muted)', borderRadius:8, padding:2, marginLeft:12}}>
            <span style={{padding:'4px 12px', fontSize:12, fontWeight:700, borderRadius:6, background:'var(--card)'}}>📚 장기 70%</span>
            <span style={{padding:'4px 12px', fontSize:12, fontWeight:500, color:'var(--muted-foreground)'}}>⚡ 단타 30%</span>
          </div>
          <div style={{flex:1, maxWidth:360, marginLeft:24, position:'relative'}}>
            <Icon name="search" size={16}/>
            <input placeholder="종목/티커 검색" style={{
              width:'100%', padding:'8px 12px 8px 34px', borderRadius:8, border:'1px solid var(--border)',
              background:'var(--muted)', fontSize:13, fontFamily:'inherit', color:'var(--foreground)',
            }}/>
            <div style={{position:'absolute', left:10, top:9, color:'var(--muted-foreground)'}}><Icon name="search" size={16}/></div>
          </div>
          <div style={{marginLeft:'auto', display:'flex', gap:12, alignItems:'center'}}>
            <Icon name="bell" size={20}/>
            <div style={{width:32, height:32, borderRadius:16, background:'var(--muted)'}}/>
          </div>
        </header>

        <div style={{flex:1, overflow:'auto', padding:'24px 32px 40px'}}>
          {/* Hero row: total + chart + goal */}
          <div style={{display:'grid', gridTemplateColumns:'1.6fr 1fr', gap:16}}>
            <Card padding="22px 26px">
              <div className="tw-micro" style={{fontSize:11, color:'var(--muted-foreground)'}}>총 평가금액 · KRW</div>
              <div style={{display:'flex', alignItems:'baseline', gap:16, marginTop:4}}>
                <span style={{fontSize:40, fontWeight:800, letterSpacing:'-0.025em', fontVariantNumeric:'tabular-nums'}}>{DW.fmt.krw(DW.totalValueKRW)}</span>
                <span style={{color:'var(--rise)', fontSize:17, fontWeight:700, fontVariantNumeric:'tabular-nums'}}>+{DW.fmt.krw(DW.dayChangeTotal)}</span>
                <Pill tone="rise">+1.84% 오늘</Pill>
              </div>
              <div style={{marginTop:18}}>
                <AreaChart data={DW.dailySeries} up={true} height={160} width={800}/>
                <div style={{display:'flex', gap:6, justifyContent:'center', marginTop:8}}>
                  {['1일','1주','1달','3달','1년','전체'].map((l,i)=>(
                    <span key={l} style={{padding:'4px 12px', fontSize:12, fontWeight:600, borderRadius:6,
                      background: i===2?'var(--primary)':'transparent', color: i===2?'#fff':'var(--muted-foreground)'}}>{l}</span>
                  ))}
                </div>
              </div>
            </Card>
            <div style={{display:'flex', flexDirection:'column', gap:16}}>
              <Card padding="18px 20px" style={{display:'flex', gap:16, alignItems:'center'}}>
                <ProgressRing pct={0.647} size={88} thickness={10} label="64.7%"/>
                <div>
                  <div className="tw-micro" style={{fontSize:11, color:'var(--muted-foreground)'}}>2억 목표 · 진척도</div>
                  <div style={{fontSize:20, fontWeight:700, marginTop:2, fontVariantNumeric:'tabular-nums'}}>남은 70,550,000</div>
                  <div style={{fontSize:12, color:'var(--muted-foreground)'}}>예상 14개월 · 월 5M 기준</div>
                </div>
              </Card>
              <Card padding="18px 20px">
                <div className="tw-micro" style={{fontSize:11, color:'var(--muted-foreground)'}}>vs KOSPI200 (6개월)</div>
                <div style={{display:'flex', alignItems:'baseline', gap:8, marginTop:4}}>
                  <span style={{fontSize:22, fontWeight:700, color:'var(--rise)', fontVariantNumeric:'tabular-nums'}}>+3.3%p</span>
                  <span style={{fontSize:12, color:'var(--muted-foreground)'}}>내 +6.4% · KOSPI200 +3.1%</span>
                </div>
                <svg viewBox="0 0 300 40" width="100%" height="40" style={{marginTop:6}}>
                  <polyline points={DW.benchmarkSeries.kospi200.map((v,i,a)=>`${i/(a.length-1)*300},${40 - v*5}`).join(' ')}
                    fill="none" stroke="var(--muted-foreground)" strokeWidth="1.5" strokeDasharray="2 2" opacity=".6"/>
                  <polyline points={DW.benchmarkSeries.mine.map((v,i,a)=>`${i/(a.length-1)*300},${40 - v*4.5}`).join(' ')}
                    fill="none" stroke="var(--rise)" strokeWidth="2"/>
                </svg>
              </Card>
            </div>
          </div>

          {/* Row 2: Tasks + Sector + Dividend */}
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:16, marginTop:16}}>
            <Card padding="18px 20px">
              <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom:12}}>
                <span className="tw-micro" style={{fontSize:11, fontWeight:700}}>오늘 할 것 · 3</span>
                <span style={{fontSize:11, color:'var(--primary)', fontWeight:600}}>전체 →</span>
              </div>
              <div style={{display:'flex', flexDirection:'column', gap:10}}>
                {DW.tasks.map((t,i)=>(
                  <div key={i} style={{display:'flex', gap:10, alignItems:'center'}}>
                    <div style={{width:28, height:28, borderRadius:8, background:`color-mix(in srgb, ${t.color} 15%, transparent)`, color:t.color, display:'flex', alignItems:'center', justifyContent:'center', fontWeight:800, fontSize:13, flexShrink:0}}>{t.icon}</div>
                    <div style={{flex:1, minWidth:0}}>
                      <div style={{fontSize:13, fontWeight:600}}>{t.title}</div>
                      <div style={{fontSize:11, color:'var(--muted-foreground)'}}>{t.sub}</div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
            <Card padding="18px 20px">
              <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom:12}}>
                <span className="tw-micro" style={{fontSize:11, fontWeight:700}}>섹터 배분</span>
                <span style={{fontSize:11, color:'var(--primary)', fontWeight:600}}>리밸런싱 →</span>
              </div>
              <div style={{display:'flex', gap:14, alignItems:'center'}}>
                <Donut size={92} thickness={14} segments={DW.sectorAllocation.map(s=>({pct:s.pct, color:s.color}))}/>
                <div style={{flex:1, fontSize:12, display:'grid', gap:5}}>
                  {DW.sectorAllocation.slice(0,4).map((r,i)=>(
                    <div key={i} style={{display:'flex', gap:6, alignItems:'center'}}>
                      <span style={{width:8, height:8, borderRadius:2, background:r.color}}/>
                      <span style={{flex:1}}>{r.sector}</span>
                      <span style={{fontWeight:700, fontVariantNumeric:'tabular-nums'}}>{(r.pct*100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
            <Card padding="18px 20px">
              <div className="tw-micro" style={{fontSize:11, fontWeight:700, marginBottom:12}}>다음 배당 · {DW.dividends.length}</div>
              <div style={{display:'flex', flexDirection:'column', gap:8}}>
                {DW.dividends.map((d,i)=>(
                  <div key={i} style={{display:'flex', justifyContent:'space-between', fontSize:13, padding:'4px 0', borderTop: i===0?0:'1px solid var(--border)'}}>
                    <div>
                      <div style={{fontWeight:600}}>{d.name}</div>
                      <div style={{fontSize:10, color:'var(--muted-foreground)', fontVariantNumeric:'tabular-nums'}}>{d.ex_date} · {d.payment_date}</div>
                    </div>
                    <span style={{fontWeight:700, color:'var(--rise)', fontVariantNumeric:'tabular-nums'}}>+{d.currency==='KRW'?d.amount.toLocaleString():'$'+d.amount.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Row 3: Holdings table + movers */}
          <div style={{display:'grid', gridTemplateColumns:'1.8fr 1fr', gap:16, marginTop:16}}>
            <Card padding="0">
              <div style={{display:'flex', justifyContent:'space-between', padding:'16px 20px 10px', alignItems:'baseline'}}>
                <span className="tw-micro" style={{fontSize:11, fontWeight:700}}>보유 종목 · 6 (주 계좌)</span>
                <span style={{fontSize:11, color:'var(--primary)'}}>상세 →</span>
              </div>
              <table style={{width:'100%', fontSize:13, borderCollapse:'collapse'}}>
                <thead>
                  <tr style={{fontSize:10, color:'var(--muted-foreground)', textAlign:'left', letterSpacing:'0.04em', textTransform:'uppercase'}}>
                    <th style={{padding:'8px 20px'}}>종목</th>
                    <th style={{textAlign:'right', padding:'8px 8px'}}>수량</th>
                    <th style={{textAlign:'right', padding:'8px 8px'}}>평단</th>
                    <th style={{textAlign:'right', padding:'8px 8px'}}>현재가</th>
                    <th style={{textAlign:'right', padding:'8px 8px'}}>평가</th>
                    <th style={{textAlign:'right', padding:'8px 20px'}}>손익%</th>
                  </tr>
                </thead>
                <tbody>
                  {DW.holdings.filter(h=>h.pid==='p1').map((h,i)=>{
                    const val = h.quantity*h.current_price;
                    const pct = ((h.current_price-h.avg_price)/h.avg_price)*100;
                    return (
                      <tr key={h.ticker} style={{borderTop:'1px solid var(--border)', fontVariantNumeric:'tabular-nums'}}>
                        <td style={{padding:'11px 20px', fontWeight:600}}>{h.name}</td>
                        <td style={{textAlign:'right'}}>{h.quantity}</td>
                        <td style={{textAlign:'right'}}>{h.avg_price.toLocaleString()}</td>
                        <td style={{textAlign:'right'}}>{h.current_price.toLocaleString()}</td>
                        <td style={{textAlign:'right'}}>{val.toLocaleString()}</td>
                        <td style={{textAlign:'right', padding:'11px 20px', color: pct>=0?'var(--rise)':'var(--fall)', fontWeight:700}}>{(pct>=0?'+':'')+pct.toFixed(2)}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Card>
            <Card padding="18px 20px">
              <div className="tw-micro" style={{fontSize:11, fontWeight:700, marginBottom:12}}>Top mover · 오늘</div>
              <div style={{display:'flex', flexDirection:'column', gap:2}}>
                {DW.movers.map((m,i)=>(
                  <div key={m.ticker} style={{borderTop: i===0?0:'1px solid var(--border)'}}>
                    <HoldingRow name={m.name} ticker={m.ticker}
                      pct={(m.pct>=0?'+':'')+m.pct.toFixed(2)+'%'} price={m.price} up={m.up}
                      sparkData={m.up?[0.3,0.4,0.35,0.5,0.55,0.7,0.8]:[0.8,0.7,0.65,0.55,0.5,0.4,0.3]} dense/>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { WebHome });
