import { useCallback, useEffect, useMemo, useState } from 'react';
import { analyzeMatch, askAnalyst, getCompetitions, getFixtures, getHealth, getPredictions, isApiConfigured } from './api';

const dLabel = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString('it-IT', { weekday: 'short', day: '2-digit', month: 'short' });
const todayISO = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };
const plusDays = (n) => { const d = new Date(); d.setDate(d.getDate()+n); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };
const formatDate = (iso) => { if (!iso) return 'Orario non disponibile'; const d = new Date(iso); return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('it-IT',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}); };
const pct = (v) => `${Math.round((Number(v)||0)*100)}%`;

const demoFixtures = [];
const oddsRows = [
  {name:'bet365', tone:'lime', values:[1.75,3.90,5.25], trend:[1,1,1]},
  {name:'Betsson', tone:'orange', values:[1.72,4.00,5.40], trend:[1,1,1]},
  {name:'Lottomatica', tone:'white', values:[1.70,3.95,5.60], trend:[-1,-1,-1]},
  {name:'Eurobet', tone:'white', values:[1.73,3.95,5.30], trend:[1,1,1]},
  {name:'GoldBet', tone:'gold', values:[1.76,3.85,5.45], trend:[1,-1,1]},
  {name:'Snai', tone:'white', values:[1.74,3.90,5.35], trend:[-1,-1,1]},
];
const navItems = [
  ['home','⌂','Home'],['picks','✳','Pronostici AI'],['calendar','▦','Calendario'],['live','◉','Diretta'],['odds','⇅','Quote & Mercati'],['reports','▤','Report giornalieri'],['vault','▣','Archivio pronostici'],['performance','▥','Performance Lab'],['simulator','◈','Simulatore'],
];

function TeamMark({name, small=false}) {
  const marks = {'Inter':'IN','Milan':'AC','Manchester City':'MC','Aston Villa':'AV','Real Madrid':'RM','Barcelona':'FC','Bayern Monaco':'BM','Borussia Dortmund':'BD','PSG':'PS','Lione':'OL','Arsenal':'AR','Juventus':'JU'};
  return <span className={`team-mark ${small?'small':''}`} title={name}>{marks[name] || name?.slice(0,2)?.toUpperCase() || 'FC'}</span>;
}
function PanelHead({eyebrow, title, right}) { return <div className="panel-head"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h2>{title}</h2></div>{right}</div>; }
function DemoBadge({children='DEMO'}) { return <span className="demo-badge">{children}</span>; }

export default function App() {
  const [page,setPage] = useState('home');
  const [moreOpen,setMoreOpen] = useState(false);
  const [matchTab,setMatchTab] = useState('Riassunto');
  const [market,setMarket] = useState('1X2');
  const [dateMode,setDateMode] = useState('Oggi');
  const [query,setQuery] = useState('');
  const [health,setHealth] = useState(null);
  const [competitions,setCompetitions] = useState([]);
  const [fixtures,setFixtures] = useState([]);
  const [history,setHistory] = useState([]);
  const [selected,setSelected] = useState(null);
  const [analysis,setAnalysis] = useState(null);
  const [analysisLoading,setAnalysisLoading] = useState(false);
  const [error,setError] = useState('');
  const [competition,setCompetition] = useState('');
  const [from,setFrom] = useState(todayISO());
  const [to,setTo] = useState(plusDays(7));
  const [odds,setOdds] = useState({home:'',draw:'',away:''});
  const [favorites,setFavorites] = useState([]);
  const [question,setQuestion] = useState('Quali sono i fattori più importanti per questa partita e quali limiti ha l’analisi?');
  const [answer,setAnswer] = useState('');
  const [chatLoading,setChatLoading] = useState(false);
  const [teamFilter,setTeamFilter] = useState('Tutte');
  const [timeFilter,setTimeFilter] = useState('Partita');
  const [simHome,setSimHome] = useState(65);
  const [simAway,setSimAway] = useState(58);
  const [simRest,setSimRest] = useState(4);
  const [reportTime,setReportTime] = useState('07:00');
  const [pushEnabled,setPushEnabled] = useState(false);
  const [connected,setConnected] = useState(false);
  const [toast,setToast] = useState('');

  const loadData = useCallback(async () => {
    setError('');

    // Vite injects VITE_API_URL at build time. Do not silently point production
    // visitors at their own localhost when the backend URL is missing.
    if (!isApiConfigured) {
      setConnected(false);
      setHealth({data_provider:'demo locale',ai_provider:'demo'});
      setCompetitions([]);
      setHistory([]);
      setFixtures([]);
      setSelected(null);
      setError('API non configurata: questa versione mostra solo dati dimostrativi. Pubblica il backend FastAPI e imposta VITE_API_URL nelle variabili Vercel, poi ridistribuisci.');
      return;
    }

    const [healthResult, competitionsResult, predictionsResult, fixturesResult] = await Promise.allSettled([
      getHealth(),
      getCompetitions(),
      getPredictions(),
      getFixtures(from,to,competition),
    ]);

    const failures = [];
    const healthOk = healthResult.status === 'fulfilled' && healthResult.value?.status === 'ok';
    if (healthOk) {
      setHealth(healthResult.value);
    } else {
      setHealth({data_provider:'backend non raggiungibile',ai_provider:'—'});
      failures.push('connessione API');
    }
    setConnected(healthOk);

    if (competitionsResult.status === 'fulfilled') {
      setCompetitions(competitionsResult.value.items || []);
    } else {
      setCompetitions([]);
      failures.push('competizioni');
    }

    if (predictionsResult.status === 'fulfilled') {
      setHistory(predictionsResult.value.items || []);
    } else {
      setHistory([]);
      failures.push('archivio pronostici');
    }

    if (fixturesResult.status === 'fulfilled') {
      const nextFixtures = fixturesResult.value.items || [];
      setFixtures(nextFixtures);
      setSelected(current => nextFixtures.find(f=>f.id===current?.id) || nextFixtures[0] || null);
    } else {
      failures.push('calendario partite');
    }

    if (failures.length) {
      setError(`Servizi non disponibili: ${failures.join(', ')}. Controlla l'URL del backend, la configurazione CORS e i log del servizio.`);
    }
  },[from,to,competition]);

  useEffect(() => { loadData(); },[loadData]); // Refresh data when date or competition filters change
  const visibleFixtures = useMemo(() => {
    const q = query.trim().toLowerCase();
    return fixtures.filter(f => (!competition || f.competition_id===competition) && (!q || `${f.home_team} ${f.away_team} ${f.competition_name}`.toLowerCase().includes(q)));
  },[fixtures,competition,query]);
  const grouped = useMemo(() => visibleFixtures.reduce((a,f)=>{(a[f.competition_name] ||= []).push(f);return a;},{}),[visibleFixtures]);
  const selectFixture = (f) => { setSelected(f); setAnalysis(null); setAnswer(''); setMatchTab('Riassunto'); setPage('home'); setOdds({home:'',draw:'',away:''}); };
  const toggleFavorite = (id) => setFavorites(xs => xs.includes(id) ? xs.filter(x=>x!==id) : [...xs,id]);
  const notify = (text) => { setToast(text); window.setTimeout(()=>setToast(''),2400); };

  async function runAnalysis() {
    if (!selected) {
      setError('Seleziona una partita prima di avviare l’analisi.');
      return;
    }
    if (!connected) {
      setAnalysis(null);
      setError(selected.is_demo
        ? 'Analisi non eseguita: la partita è dimostrativa oppure il backend non è collegato. Nessuna probabilità viene inventata.'
        : 'Analisi non eseguita: il backend non è collegato.');
      return;
    }
    if (selected.is_demo) {
      setAnalysis(null);
      setError('Analisi non eseguita: la partita selezionata è un esempio dimostrativo. Seleziona una partita fornita dal backend.');
      return;
    }

    setAnalysisLoading(true); setError(''); setAnswer('');
    try {
      const result = await analyzeMatch(selected,odds);
      setAnalysis(result);
      const predictions = await getPredictions();
      setHistory(predictions.items || []);
    } catch(e) {
      setAnalysis(null);
      setError(`Analisi non disponibile: ${e.message}`);
    } finally {
      setAnalysisLoading(false);
    }
  }
  async function ask() {
    if (!question.trim() || !selected) return;
    setChatLoading(true); setAnswer('');
    try { if (!connected) throw new Error('Anteprima dimostrativa'); const result=await askAnalyst(question,selected,analysis); setAnswer(`${result.answer}\n\nMotore: ${result.provider}${result.fallback?' · fallback':''}`); }
    catch { setAnswer('Per questa partita dimostrativa possiamo descrivere solo i limiti: servono risultati verificati, formazioni, assenze e quote con timestamp prima di formulare un giudizio attendibile. Quando il backend e i provider saranno configurati, la spiegazione userà solo i dati effettivamente disponibili.'); }
    finally { setChatLoading(false); }
  }

  const pageTitle = navItems.find(n=>n[0]===page)?.[2] || 'Home';
  const sourceBadgeLabel = !connected ? 'API NON COLLEGATA' : health?.data_provider === 'openfootball_remote' ? 'OPEN DATA' : health?.data_provider === 'demo' ? 'DEMO' : 'FONTE COLLEGATA';
  return <div className="app-shell">
    <aside className="sidebar">
      <button className="brand" onClick={()=>setPage('home')} aria-label="Torna alla Home"><span className="brand-mark">✳</span><span className="brand-type"><strong>MatchMind <i>AI</i></strong><small>FOOTBALL INTELLIGENCE</small></span></button>
      <div className="sidebar-caption">WORKSPACE</div>
      <nav className="side-nav">{navItems.map(([id,ico,label])=><button key={id} className={`nav-item ${page===id?'active':''}`} onClick={()=>setPage(id)}><span className="nav-icon">{ico}</span><span>{label}</span>{id==='live'&&<span className="live-dot"/>}</button>)}</nav>
      <div className="side-spacer"/>
      <button className={`nav-item ${page==='settings'?'active':''}`} onClick={()=>setPage('settings')}><span className="nav-icon">⚙</span><span>Impostazioni</span></button>
      <div className="provider-card"><span className={`connection-dot ${connected?'ok':''}`}/><div><strong>{connected?'API connessa':'API non collegata'}</strong><small>{health?.data_provider || 'nessuna fonte dati'}</small></div><button aria-label="Aggiorna connessione" onClick={loadData}>↻</button></div>
      <div className="sidebar-disclaimer">Le previsioni sono stime, non garanzie di risultato.</div>
    </aside>

    <main className="main-content">
      <header className="topbar">
        <div className="mobile-brand"><span className="brand-mark">✳</span><strong>MatchMind <i>AI</i></strong></div>
        <label className="global-search"><span>⌕</span><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Cerca una partita, una squadra o un campionato…"/><kbd>⌘ K</kbd></label>
        <div className="top-actions"><span className="system-pill"><span className={`connection-dot ${connected?'ok':''}`}/>{connected?'API connessa':'API non collegata'}</span><button className="icon-button" aria-label="Notifiche" onClick={()=>notify('Nessuna nuova notifica')}>♧<span className="notification-dot"/></button><button className="avatar-button" onClick={()=>setPage('settings')}>MM</button></div>
      </header>

      {error && <div className="notice-banner"><span>ⓘ</span><p>{error}</p><button onClick={()=>setError('')}>×</button></div>}
      {page==='home' && <>
        <div className="page-heading"><div><p className="eyebrow">MATCHMIND / OVERVIEW</p><h1>Buongiorno, analista <span>✦</span></h1><p>Il tuo centro di controllo per partite, quote e previsioni.</p></div><div className="heading-actions"><DemoBadge>{sourceBadgeLabel}</DemoBadge><button className="button secondary" onClick={loadData}>↻ Aggiorna dati</button></div></div>
        <section className="kpi-grid">
          <div className="kpi-card"><div className="kpi-top"><span>Partite monitorate</span><span className="kpi-icon blue">▦</span></div><strong>{fixtures.length.toString().padStart(2,'0')}</strong><small><span className="tiny-green">●</span> nell’intervallo selezionato</small></div>
          <div className="kpi-card"><div className="kpi-top"><span>Analisi archiviate</span><span className="kpi-icon purple">✳</span></div><strong>{history.length.toString().padStart(2,'0')}</strong><small>registro della fonte connessa</small></div>
          <div className="kpi-card"><div className="kpi-top"><span>Competizioni</span><span className="kpi-icon orange">♜</span></div><strong>{competitions.length.toString().padStart(2,'0')}</strong><small>disponibilità legata al provider</small></div>
          <div className="kpi-card"><div className="kpi-top"><span>Modello attivo</span><span className="kpi-icon green">⌁</span></div><strong className="model-number">Poisson <em>v1</em></strong><small>baseline sperimentale</small></div>
        </section>

        <div className="dashboard-grid">
          <section className="panel fixtures-panel">
            <PanelHead eyebrow="MATCH SCHEDULE" title="Partite" right={<button className="text-action" onClick={()=>setPage('calendar')}>Calendario completo ↗</button>}/>
            <div className="date-switcher">{['Ieri','Oggi','Domani'].map((d,i)=><button key={d} className={dateMode===d?'selected':''} onClick={()=>{setDateMode(d);setFrom(plusDays(i-1));setTo(plusDays(i-1));}}>{d}<small>{dLabel(plusDays(i-1))}</small></button>)}</div>
            <div className="competition-filter"><span>Competizioni</span><button onClick={()=>setCompetition('')}>Tutte <span>⌄</span></button></div>
            <div className="league-list">{competitions.slice(0,6).map((league,i)=><button key={league.id} className="league-chip" onClick={()=>{setCompetition(league.id);setPage('calendar');}}><span className={`league-icon league-${i}`}>{({'it.1':'🇮🇹','en.1':'🇬🇧','en.2':'🏴','es.1':'🇪🇸','de.1':'🇩🇪','fr.1':'🇫🇷','nl.1':'🇳🇱','pt.1':'🇵🇹'})[league.id] || '⚽'}</span><span>{league.name}</span><span className="league-count">{visibleFixtures.filter(f=>f.competition_id===league.id).length}</span></button>)}</div>
            <div className="fixture-section-title"><span>In evidenza</span><span>{visibleFixtures.length} partite</span></div>
            <div className="fixture-mini-list">{visibleFixtures.slice(0,5).map(f=><button key={f.id} className={`fixture-mini ${selected?.id===f.id?'chosen':''}`} onClick={()=>selectFixture(f)}><div className="fixture-mini-top"><span>{f.competition_name}</span>{f.status==='LIVE'?<span className="live-pill"><i/> LIVE</span>:<time>{formatDate(f.kickoff).split(',').pop()}</time>}</div><div className="fixture-teams"><span><TeamMark name={f.home_team} small/>{f.home_team}</span><b>{f.home_score!=null?f.home_score:'—'} <small>:</small> {f.away_score!=null?f.away_score:'—'}</b><span><TeamMark name={f.away_team} small/>{f.away_team}</span></div><div className="fixture-mini-bottom"><span>{f.status==='LIVE'?(f.minute||'In corso'):'Calcio d’inizio · '+formatDate(f.kickoff)}</span><span className="fixture-open">↗</span></div></button>)}</div>
            <div className="source-note"><span>ⓘ</span> <span>Fonte: <b>{health?.data_provider || 'non collegata'}</b>. Il dataset pubblica calendari e risultati, non eventi live o quote bookmaker.</span></div>
          </section>

          <section className="center-column">
            <MatchHero fixture={selected} onOpenOdds={()=>{setPage('odds');setMatchTab('Quote');}}/>
            <section className="panel match-tabs-panel">
              <div className="match-tabs">{['Riassunto','Sintesi','Statistiche','Formazioni','Stats giocatore','Quote'].map(t=><button key={t} className={matchTab===t?'active':''} onClick={()=>{setMatchTab(t);if(t==='Quote')setPage('odds');}}>{t}</button>)}</div>
              {matchTab==='Statistiche' ? <StatsView timeFilter={timeFilter} setTimeFilter={setTimeFilter}/> : matchTab==='Formazioni' ? <FormationView/> : matchTab==='Stats giocatore' ? <PlayerStats/> : matchTab==='Sintesi' ? <Editorial/> : matchTab==='Quote' ? <OddsTable market={market} setMarket={setMarket}/> : <>
                <div className="match-content-grid"><EventTimeline fixture={selected}/><StatsBars/></div>
                <div className="ai-pick-panel"><div className="ai-pick-title"><div><span className="ai-spark">✳</span><div><h3>Analisi AI della partita</h3><p>Probabilità statistiche e fattori da verificare.</p></div></div><button className="button primary" onClick={runAnalysis} disabled={analysisLoading}>{analysisLoading?'Analisi…':'Genera analisi ↗'}</button></div>
                  {analysis ? <div className="analysis-inline"><div className="prob-strip">{[['1',analysis.probabilities?.home],['X',analysis.probabilities?.draw],['2',analysis.probabilities?.away]].map(([k,v])=><div key={k}><span>{k}</span><b>{pct(v)}</b></div>)}</div><p className="disclaimer-text"><DemoBadge/> {analysis.data_quality?.note || 'Qualità e copertura dati da verificare.'} {analysis.demo?'La stima visualizzata è dimostrativa.':''}</p></div> : <div className="prediction-teaser"><div className="teaser-segment"><span>Mercato</span><strong>1X2 · probabilità</strong></div><div className="teaser-segment"><span>Dati recenti</span><strong>Da verificare</strong></div><div className="teaser-segment"><span>Qualità</span><strong className="text-amber">Non validata</strong></div></div>}
                </div>
              </>}
            </section>
            {matchTab==='Riassunto' && <section className="panel bottom-article-grid"><Editorial compact/><PlayerStats compact/></section>}
          </section>

          <aside className="right-column">
            <section className="panel odds-panel"><PanelHead eyebrow="ODDS INTELLIGENCE" title="Confronto quote" right={<button className="arrow-link" onClick={()=>setPage('odds')}>↗</button>}/><MarketPills market={market} setMarket={setMarket}/><OddsTable market={market} setMarket={setMarket} compact/><div className="odds-foot"><span><i className="tiny-green"/> movimento illustrativo</span><button className="text-action" onClick={()=>setPage('odds')}>Tutte le quote →</button></div><p className="mini-disclaimer">Quote di esempio, non aggiornate e non riferite a un feed reale.</p></section>
            <section className="panel formation-panel"><PanelHead eyebrow="TACTICAL VIEW" title="Formazioni" right={<button className="arrow-link" onClick={()=>setMatchTab('Formazioni')}>↗</button>}/><div className="formation-head"><span><TeamMark name={selected?.home_team||'Inter'}/><b>{selected?.home_team||'Inter'}</b></span><small>4-3-3</small><small>4-2-3-1</small><span><b>{selected?.away_team||'Milan'}</b><TeamMark name={selected?.away_team||'Milan'}/></span></div><MiniPitch/><div className="formation-foot"><span><i/> valutazioni illustrative</span><button className="text-action" onClick={()=>setMatchTab('Formazioni')}>Formazioni complete ↗</button></div><p className="mini-disclaimer">Formazioni e rating reali disponibili solo con una fonte abilitata.</p></section>
            <section className="panel picks-panel"><PanelHead eyebrow="PREDICTION VAULT" title="Ultime analisi" right={<button className="text-action" onClick={()=>setPage('vault')}>Vedi tutte →</button>}/><PredictionRows history={history}/><button className="button secondary full" onClick={()=>setPage('vault')}>Apri archivio</button></section>
          </aside>
        </div>
      </>}

      {page!=='home' && <PageView page={page} pageTitle={pageTitle} sourceBadgeLabel={sourceBadgeLabel} fixtures={visibleFixtures} selected={selected} selectFixture={selectFixture} competitions={competitions} history={history} connected={connected} market={market} setMarket={setMarket} analysis={analysis} runAnalysis={runAnalysis} analysisLoading={analysisLoading} odds={odds} setOdds={setOdds} from={from} setFrom={setFrom} to={to} setTo={setTo} competition={competition} setCompetition={setCompetition} timeFilter={timeFilter} setTimeFilter={setTimeFilter} teamFilter={teamFilter} setTeamFilter={setTeamFilter} simHome={simHome} setSimHome={setSimHome} simAway={simAway} setSimAway={setSimAway} simRest={simRest} setSimRest={setSimRest} reportTime={reportTime} setReportTime={setReportTime} pushEnabled={pushEnabled} setPushEnabled={setPushEnabled} loadData={loadData} notify={notify}/>}
      <footer className="app-footer"><span>MatchMind AI <b>·</b> Prototipo privato</span><span><i className="connection-dot"/> Dati demo separati dai dati verificati</span><span>Gioca responsabilmente · Nessuna previsione garantisce vincite</span></footer>
    </main>

    {moreOpen && <><button className="more-backdrop" aria-label="Chiudi menu" onClick={()=>setMoreOpen(false)}/><div className="mobile-more-menu"><div className="more-menu-head"><strong>Altre sezioni</strong><button onClick={()=>setMoreOpen(false)} aria-label="Chiudi">×</button></div>{[['odds','⇅','Quote & Mercati'],['reports','▤','Report giornalieri'],['vault','▣','Archivio pronostici'],['performance','▥','Performance Lab'],['simulator','◈','Simulatore'],['settings','⚙','Impostazioni']].map(([id,ico,label])=><button key={id} className={page===id?'active':''} onClick={()=>{setPage(id);setMoreOpen(false);}}><span>{ico}</span>{label}<b>›</b></button>)}</div></>}
    <nav className="mobile-nav">{[['home','⌂','Home'],['picks','✳','Pronostici'],['live','◉','Diretta'],['calendar','▦','Calendario']].map(([id,ico,label])=><button key={id} className={page===id?'active':''} onClick={()=>{setPage(id);setMoreOpen(false);}}><span>{ico}</span><small>{label}</small></button>)}<button className={moreOpen||['odds','reports','vault','performance','simulator','settings'].includes(page)?'active':''} onClick={()=>setMoreOpen(!moreOpen)}><span>···</span><small>Altro</small></button></nav>
    {toast && <div className="toast">✓ {toast}</div>}
  </div>;
}

function MatchHero({fixture,onOpenOdds}) {
  if (!fixture) return <section className="panel hero-panel no-selection"><span className="hero-label">MATCH CENTER</span><h2>Nessuna partita selezionata</h2><p>Scegli una partita dal calendario per aprire il centro analisi.</p></section>;
  const live = fixture.status==='LIVE';
  return <section className="hero-panel"><div className="hero-topline"><span className="hero-label"><span>◉</span> {fixture.competition_name} · Match Center</span>{fixture.is_demo&&<DemoBadge/>}{live&&<span className="live-pill"><i/> LIVE</span>}</div><div className="hero-matchup"><div className="hero-team"><TeamMark name={fixture.home_team}/><h2>{fixture.home_team}</h2><small>Casa</small></div><div className="score-block"><div className="scoreline"><strong>{fixture.home_score??'—'}</strong><span>:</span><strong>{fixture.away_score??'—'}</strong></div><span className={`match-status ${live?'is-live':''}`}>{live?(fixture.minute||'LIVE'):'IN PROGRAMMA'}</span><small>{formatDate(fixture.kickoff)}</small></div><div className="hero-team"><TeamMark name={fixture.away_team}/><h2>{fixture.away_team}</h2><small>Trasferta</small></div></div><div className="hero-bottom"><span>⌖ {fixture.country||'Competizione selezionata'}</span><span>☁ Meteo non collegato</span><button onClick={onOpenOdds}>Confronta quote ↗</button></div></section>;
}
function EventTimeline({fixture}) {
  const live=fixture?.status==='LIVE';
  const events=[['03′','⚑','Calcio d’angolo',fixture?.home_team||'Squadra di casa','event-yellow'],['12′','▰','Ammonizione', 'Giocatore da confermare','event-yellow'],['28′','⚽','Gol (esempio)',fixture?.home_team||'Squadra di casa','event-goal'],['34′','⇄','Sostituzione','Dati non disponibili','event-sub'],['41′','▰','Ammonizione','Giocatore da confermare','event-yellow'],[live?'45′':'HT','◷',live?'Intervallo in corso':'Fine primo tempo','', 'event-time']];
  return <div className="subpanel timeline-panel"><div className="subpanel-head"><h3>Cronologia eventi</h3><button className="quiet-action">⋯</button></div><div className="period-switch"><button className="active">1° Tempo</button><button>2° Tempo</button></div><div className="timeline-list">{events.map((e,i)=><div key={i} className="timeline-item"><time>{e[0]}</time><span className={`event-icon ${e[4]}`}>{e[1]}</span><div><strong>{e[2]}</strong>{e[3]&&<small>{e[3]}</small>}</div></div>)}</div><div className="data-caveat">Eventi illustrativi: la timeline live richiede un provider eventi.</div></div>;
}
function StatsBars() {
  const stats=[['Possesso palla',56,44],['Tiri totali',8,5],['Tiri in porta',4,2],['Calci d’angolo',5,3],['Passaggi riusciti',82,76],['Cartellini gialli',1,1]];
  return <div className="subpanel stats-bars-panel"><div className="subpanel-head"><h3>Statistiche live</h3><button className="quiet-action">···</button></div><div className="stats-legend"><span><i className="home-color"/> Casa</span><span><i className="away-color"/> Trasferta</span></div>{stats.map(([label,h,a])=><div className="stat-bar-row" key={label}><div className="stat-values"><b>{h}{label.includes('Possesso')||label.includes('riusciti')?'%':''}</b><span>{label}</span><b>{a}{label.includes('Possesso')||label.includes('riusciti')?'%':''}</b></div><div className="dual-track"><span style={{width:`${(h/(h+a))*100}%`}}/><span style={{width:`${(a/(h+a))*100}%`}}/></div></div>)}<div className="data-caveat">Valori d’esempio, non statistiche ufficiali.</div></div>;
}
function MarketPills({market,setMarket}) { return <div className="market-pills">{['1X2','O/U','Gol/No Gol','Doppia Chance'].map(m=><button key={m} className={market===m?'active':''} onClick={()=>setMarket(m)}>{m}</button>)}</div>; }
function OddsTable({market,setMarket,compact=false}) {
  const index=market==='1X2'?0:market==='O/U'?1:market==='Gol/No Gol'?2:0;
  return <div className={`odds-table-wrap ${compact?'compact':''}`}><table className="odds-table"><thead><tr><th>Bookmaker</th><th>{market==='1X2'?'1':market==='O/U'?'Over 2.5':market==='Gol/No Gol'?'Gol':'1X'}</th><th>{market==='1X2'?'X':market==='O/U'?'Under 2.5':market==='Gol/No Gol'?'No Gol':'12'}</th><th>{market==='1X2'?'2':'Trend'}</th>{!compact&&<th>Agg.</th>}</tr></thead><tbody>{oddsRows.map((r,i)=>{const vals=market==='1X2'?r.values:market==='O/U'?[1.88+i*.02,1.92+i*.015,0]:market==='Gol/No Gol'?[1.84+i*.03,1.93+i*.02,0]:[1.23+i*.01,1.18+i*.01,0];return <tr key={r.name}><td><strong className={`bookmaker-name ${r.tone}`}>{r.name}</strong></td><td><b className={i===4?'best-odd':''}>{vals[0].toFixed(2)}</b><span className={`trend ${r.trend[index]===-1?'down':'up'}`}>{r.trend[index]===-1?'↓':'↑'}</span></td><td><b>{vals[1].toFixed(2)}</b><span className={`trend ${r.trend[1]===-1?'down':'up'}`}>{r.trend[1]===-1?'↓':'↑'}</span></td><td><b>{market==='1X2'?vals[2].toFixed(2):r.trend[2]===-1?'↓':'↑'}</b>{market==='1X2'&&<span className={`trend ${r.trend[2]===-1?'down':'up'}`}>{r.trend[2]===-1?'↓':'↑'}</span>}</td>{!compact&&<td><span className="source-unknown">Demo</span></td>}</tr>})}</tbody></table>{!compact&&<p className="table-caveat">Tutte le quote e le frecce in questa schermata sono dimostrative. Nessun feed bookmaker è connesso.</p>}</div>;
}
function MiniPitch() {
  const home=[['12%', '13%','7.4'],['29%','13%','7.6'],['45%','13%','7.3'],['62%','13%','7.1'],['82%','13%','7.2'],['21%','40%','7.5'],['43%','40%','7.8'],['67%','40%','7.1'],['27%','68%','7.4'],['60%','68%','7.6'],['45%','85%','7.3']];
  const away=[['14%','13%','6.8'],['34%','13%','6.5'],['60%','13%','7.0'],['82%','13%','7.1'],['32%','40%','6.7'],['66%','40%','6.9'],['20%','68%','6.6'],['42%','68%','6.8'],['62%','68%','7.1'],['83%','68%','6.7'],['48%','85%','6.4']];
  return <div className="mini-pitch"><div className="pitch-lines"><span/><i/><b/><em/></div>{home.map((p,i)=><div key={`h${i}`} className="pitch-player home-player" style={{left:p[0],top:p[1]}}><span>{i===10?'GK':i+1}</span><b>{p[2]}</b></div>)}{away.map((p,i)=><div key={`a${i}`} className="pitch-player away-player" style={{left:p[0],top:p[1]}}><span>{i===10?'GK':i+1}</span><b>{p[2]}</b></div>)}</div>;
}
function FormationView() { return <div className="tab-content"><div className="formation-header-wide"><div><h3>Formazioni tattiche</h3><p>Campo dimostrativo · nessuna distinta ufficiale connessa</p></div><div className="formation-controls"><button className="active">Panoramica</button><button>Valore</button><button>Età</button><button>Altezza</button></div></div><div className="big-pitch"><MiniPitch/></div><div className="player-rating-legend"><span><i className="home-color"/> Squadra casa · 4-3-3</span><span><i className="away-color"/> Squadra ospite · 4-2-3-1</span><span>Rating dimostrativi</span></div></div>; }
function StatsView({timeFilter,setTimeFilter}) { const stats=[['Goal previsti (xG)','1.62','0.78',67,33],['Possesso palla','56%','44%',56,44],['Tiri totali','8','5',62,38],['Tiri in porta','4','2',67,33],['Grandi occasioni','2','1',67,33],['Calci d’angolo','5','3',63,37],['Passaggi completati','82%','76%',52,48],['Cartellini gialli','1','1',50,50]]; return <div className="tab-content"><div className="tab-toolbar"><h3>Statistiche partita</h3><div className="segmented">{['Partita','1° Tempo','2° Tempo'].map(v=><button key={v} className={timeFilter===v?'active':''} onClick={()=>setTimeFilter(v)}>{v}</button>)}</div></div><div className="advanced-stat-list">{stats.map(([label,h,a,hp,ap])=><div className="advanced-stat" key={label}><div className="advanced-stat-numbers"><b>{h}</b><span>{label}</span><b>{a}</b></div><div className="advanced-track"><span className="home-track" style={{width:`${hp}%`}}/><span className="away-track" style={{width:`${ap}%`}}/></div></div>)}</div><p className="table-caveat">Metriche illustrative per il progetto UI. xG e statistiche reali saranno mostrate solo quando offerte dal provider scelto.</p></div>; }
function PlayerStats({compact=false}) { const [category,setCategory]=useState('Top'); const cats=['Top','Tiri','Attacco','Passaggi','Difesa']; const players=[['Lautaro Martínez','Inter','ATT','8.3','9'],['Nicolò Barella','Inter','CEN','7.9','7'],['Hakan Çalhanoğlu','Inter','CEN','7.7','5'],['Rafael Leão','Milan','ATT','7.1','4'],['Theo Hernández','Milan','DIF','6.8','2']]; return <div className={`player-stats ${compact?'compact':''}`}><div className="subpanel-head"><h3>{compact?'Top giocatori':'Stats giocatore'}</h3>{!compact&&<select aria-label="Squadra" defaultValue="Tutte"><option>Tutte</option><option>Casa</option><option>Ospite</option></select>}</div><div className="player-categories">{cats.map(c=><button key={c} className={category===c?'active':''} onClick={()=>setCategory(c)}>{c}</button>)}</div><div className="players-list">{players.slice(0,compact?3:5).map((p,i)=><div className="player-row" key={p[0]}><span className="player-rank">{i+1}</span><span className={`player-face face-${i}`}>{p[0].split(' ').map(x=>x[0]).join('').slice(0,2)}</span><div className="player-details"><strong>{p[0]}</strong><small>{p[1]} · {p[2]}</small></div><b className="player-rating">{category==='Tiri'?p[4]:p[3]}</b></div>)}</div><p className="mini-disclaimer">Nomi e voti esemplificativi, non rating verificati.</p></div>; }
function Editorial({compact=false}) { return <div className={`editorial ${compact?'compact':''}`}><div className="editorial-cover"><span>MM</span><small>TACTICAL BRIEFING</small></div><div className="editorial-body"><div className="eyebrow">SINTESI · ESEMPIO</div><h3>La chiave tattica: controllo del centro e transizioni</h3><p>Una sintesi editoriale sarà generata dopo la partita usando eventi verificati e fonti autorizzate. In questa anteprima non vengono riportate notizie reali.</p><div className="editorial-meta"><span>Redazione MatchMind</span><span>·</span><span>Anteprima UI</span></div></div></div>; }
function PredictionRows() { const rows=[['Inter · Milan','1X2 — Inter','68%','In attesa','home'],['Real Madrid · Barcelona','Over 2.5','72%','In attesa','away'],['Bayern · Dortmund','1X2 — Bayern','65%','In attesa','home'],['PSG · Lione','Gol Sì','58%','In attesa','away']];return <div className="prediction-rows">{rows.slice(0,3).map((r,i)=><div className="prediction-row" key={r[0]}><TeamMark name={r[4]==='home'?'Inter':'Real Madrid'} small/><div className="prediction-details"><strong>{r[0]}</strong><small>{r[1]}</small></div><div className="prediction-outcome"><b>{r[2]}</b><small>Demo</small></div></div>)}</div>; }

function PageView(props) {
  const {page,pageTitle,sourceBadgeLabel,fixtures,selected,selectFixture,competitions,history,connected,market,setMarket,analysis,runAnalysis,analysisLoading,odds,setOdds,from,setFrom,to,setTo,competition,setCompetition,timeFilter,setTimeFilter,teamFilter,setTeamFilter,simHome,setSimHome,simAway,setSimAway,simRest,setSimRest,reportTime,setReportTime,pushEnabled,setPushEnabled,loadData,notify}=props;
  return <div className="secondary-page"><div className="page-heading"><div><p className="eyebrow">MATCHMIND / WORKSPACE</p><h1>{pageTitle}</h1><p>{({picks:'Pronostici ordinati, con provenienza e qualità dei dati.',calendar:'Il calendario delle competizioni disponibili al provider.',live:'Match Center: eventi e dati live solo se supportati dalla fonte.',odds:'Confronto quote e mercati. Le quote reali richiedono un feed autorizzato.',reports:'Report giornalieri consultabili per data e versione.',vault:'Registro delle analisi. I dati dimostrativi non sono risultati verificati.',performance:'Metriche di validazione: servono dati storici e test fuori campione.',simulator:'Esplora scenari ipotetici, senza confonderli con previsioni reali.',settings:'Preferenze, connessione dati e automazioni.'})[page]}</p></div><div className="heading-actions"><DemoBadge>{sourceBadgeLabel}</DemoBadge><button className="button secondary" onClick={loadData}>↻ Sincronizza</button></div></div>
    {page==='picks'&&<div className="page-two-col"><section className="panel page-panel"><PanelHead eyebrow="AI PICKS" title="Pronostici in evidenza"/><div className="filters-row"><select value={competition} onChange={e=>setCompetition(e.target.value)}><option value="">Tutte le competizioni</option>{competitions.map(c=><option value={c.id} key={c.id}>{c.name}</option>)}</select><select defaultValue="ranked"><option value="ranked">Ordinamento: ranking</option><option value="probability">Probabilità</option><option value="value">Valore teorico</option></select></div>{fixtures.map(f=><button className="pick-card" key={f.id} onClick={()=>selectFixture(f)}><span className="pick-competition">{f.competition_name} {f.is_demo&&<DemoBadge/>}</span><div className="pick-match"><span><TeamMark name={f.home_team}/>{f.home_team}</span><b>vs</b><span><TeamMark name={f.away_team}/>{f.away_team}</span></div><div className="pick-card-footer"><span>Analisi: <b>non validata</b></span><span>Seleziona per analizzare ↗</span></div></button>)}</section><section className="panel page-panel"><PanelHead eyebrow="ANALYSIS" title="Analizza una partita"/><p className="body-muted">Seleziona una partita e avvia il motore statistico configurato.</p>{selected&&<div className="selected-detail"><div><TeamMark name={selected.home_team}/><b>{selected.home_team}</b></div><span>VS</span><div><TeamMark name={selected.away_team}/><b>{selected.away_team}</b></div></div>}<button className="button primary full" onClick={runAnalysis} disabled={analysisLoading}>{analysisLoading?'Calcolo…':'Calcola probabilità'}</button>{analysis&&<div className="analysis-page-results">{[['1',analysis.probabilities?.home],['X',analysis.probabilities?.draw],['2',analysis.probabilities?.away]].map(([k,v])=><div key={k}><span>{k}</span><b>{pct(v)}</b></div>)}<p>{analysis.data_quality?.note} {analysis.demo?'Risultato dimostrativo.':''}</p></div>}</section></div>}
    {page==='calendar'&&<section className="panel page-panel"><PanelHead eyebrow="FIXTURE LIST" title="Calendario partite" right={<span className="muted-count">{fixtures.length} disponibili</span>}/><div className="calendar-filters"><label>Dal<input type="date" value={from} onChange={e=>setFrom(e.target.value)}/></label><label>Al<input type="date" value={to} onChange={e=>setTo(e.target.value)}/></label><label>Campionato<select value={competition} onChange={e=>setCompetition(e.target.value)}><option value="">Tutti</option>{competitions.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label><button className="button primary" onClick={loadData}>Applica filtri</button></div><div className="calendar-list">{fixtures.map(f=><button key={f.id} onClick={()=>selectFixture(f)} className="calendar-fixture"><span className="calendar-time">{formatDate(f.kickoff)}</span><span className="calendar-league">{f.competition_name}</span><div className="calendar-team"><TeamMark name={f.home_team}/><b>{f.home_team}</b></div><span className="calendar-score">{f.home_score??'—'} : {f.away_score??'—'}</span><div className="calendar-team"><TeamMark name={f.away_team}/><b>{f.away_team}</b></div><DemoBadge/></button>)}</div><p className="table-caveat">Il catalogo include solo le competizioni raggiunte dalla fonte configurata; “tutti i campionati” non è garantito da provider gratuiti.</p></section>}
    {page==='live'&&<div className="page-two-col live-page"><section className="panel page-panel"><PanelHead eyebrow="LIVE DESK" title="Partite in diretta" right={<span className="live-pill"><i/> ESEMPI</span>}/>{fixtures.filter(f=>f.status==='LIVE').concat(fixtures.filter(f=>f.status!=='LIVE').slice(0,2)).map(f=><button key={f.id} className="live-match-card" onClick={()=>selectFixture(f)}><div><span className="eyebrow">{f.competition_name}</span><strong>{f.home_team} <em>{f.home_score??'—'} : {f.away_score??'—'}</em> {f.away_team}</strong><small>{f.status==='LIVE'?'LIVE dimostrativo':'Non iniziata'}</small></div><span>Apri ↗</span></button>)}</section><section className="panel page-panel"><PanelHead eyebrow="MATCH CENTER" title="Cronologia e statistiche"/><EventTimeline fixture={selected||demoFixtures[0]}/><StatsBars/></section></div>}
    {page==='odds'&&<div className="page-two-col"><section className="panel page-panel"><PanelHead eyebrow="MARKET MONITOR" title="Confronto multi-bookmaker" right={<span className="pill-muted">6 bookmaker demo</span>}/><div className="market-heading"><div><strong>{selected?.home_team||'Squadra casa'} <small>vs</small> {selected?.away_team||'Squadra ospite'}</strong><span>{selected?.competition_name||'Partita selezionata'} · {selected?formatDate(selected.kickoff):'—'}</span></div><DemoBadge>QUOTE DEMO</DemoBadge></div><MarketPills market={market} setMarket={setMarket}/><OddsTable market={market} setMarket={setMarket}/><div className="trend-note"><strong>Come leggere i trend</strong><span>↑ quota in aumento · ↓ quota in diminuzione. In questa demo i trend sono illustrativi e non sono aggiornamenti in tempo reale.</span></div></section><section className="panel page-panel"><PanelHead eyebrow="PRICE CHECK" title="Quota e valore teorico"/><p className="body-muted">Inserisci le quote che hai raccolto manualmente. Il valore atteso è significativo solo con una probabilità attendibile e quote aggiornate.</p><div className="manual-odds-form">{[['home','1 — Casa'],['draw','X — Pareggio'],['away','2 — Trasferta']].map(([k,l])=><label key={k}>{l}<input inputMode="decimal" value={odds[k]} onChange={e=>setOdds({...odds,[k]:e.target.value})}/></label>)}</div><button className="button primary full" onClick={runAnalysis} disabled={analysisLoading}>{analysisLoading?'Calcolo…':'Calcola stima'}</button>{analysis&&<div className="analysis-page-results">{[['1',analysis.probabilities?.home,odds.home],['X',analysis.probabilities?.draw,odds.draw],['2',analysis.probabilities?.away,odds.away]].map(([k,p,o])=>{const ev=Number(o)>1?(Number(p)||0)*Number(o)-1:null;return <div key={k}><span>{k} · quota {o||'—'}</span><b className={ev!==null&&ev>0?'positive':''}>{ev===null?'—':`${ev>=0?'+':''}${(ev*100).toFixed(1)}%`}</b></div>})}<p>Valore teorico basato sull'analisi mostrata; non corregge necessariamente margine e incertezza.</p></div>}</section></div>}
    {page==='reports'&&<div className="page-two-col"><section className="panel page-panel"><PanelHead eyebrow="DAILY INTELLIGENCE" title="Report giornalieri" right={<DemoBadge>PREVIEW</DemoBadge>}/><div className="report-card"><div className="report-date"><span>OGGI</span><strong>{new Date().toLocaleDateString('it-IT',{day:'2-digit',month:'long'})}</strong></div><div className="report-copy"><h3>Il report non è ancora stato generato</h3><p>Quando i provider saranno configurati, il report verrà generato in base ai dati disponibili. Se nessuna selezione supera le soglie definite, il report potrà contenere zero pronostici.</p><small>Europe/Rome · versioni consultabili nello storico</small></div><button className="button secondary" onClick={()=>notify('Report dimostrativo: nessuna previsione è stata pubblicata')}>Anteprima report</button></div><div className="archived-reports"><h3>Versioni precedenti</h3><div className="empty-block">Nessun report salvato nel backend al momento.</div></div></section><section className="panel page-panel"><PanelHead eyebrow="SCHEDULE" title="Programmazione"/><label className="settings-line"><span><b>Generazione quotidiana</b><small>Fuso orario Europe/Rome</small></span><input type="time" value={reportTime} onChange={e=>setReportTime(e.target.value)}/></label><button className="button primary full" onClick={()=>notify(`Orario salvato nell'anteprima: ${reportTime} Europe/Rome`)}>Salva preferenza</button><p className="mini-disclaimer">La pianificazione effettiva richiede un worker/scheduler persistente in cloud. Salvare l'orario qui non attiva ancora un job server.</p></section></div>}
    {page==='vault'&&<section className="panel page-panel"><PanelHead eyebrow="APPEND-ONLY LOG" title="Archivio pronostici" right={<button className="button secondary" onClick={()=>notify('Esportazione disponibile dopo il collegamento del registro backend')}>Esporta ↗</button>}/><div className="vault-summary"><div><span>Analisi salvate</span><b>{history.length}</b></div><div><span>Esiti verificati</span><b>—</b></div><div><span>ROI validato</span><b>—</b></div><div><span>Modalità</span><b className="text-amber">Preview</b></div></div>{history.length>0?<div className="vault-list">{history.map((p,i)=><div className="vault-row" key={p.id||i}><div><strong>{p.home_team} — {p.away_team}</strong><small>{p.source} · {p.created_at?formatDate(p.created_at):'timestamp non disponibile'} · {p.model_version}</small></div><div className="vault-probs"><span>1 {pct(p.probabilities?.home)}</span><span>X {pct(p.probabilities?.draw)}</span><span>2 {pct(p.probabilities?.away)}</span></div><DemoBadge/></div>)}</div>:<div className="empty-block">Nessuna analisi disponibile nel registro collegato. Genera una analisi con il backend attivo per salvarla.</div>}<p className="table-caveat">Per essere immutabile, lo storico di produzione dovrà salvare versioni, timestamp, quote, dati sorgente e regolamento di liquidazione senza sovrascrivere il passato.</p></section>}
    {page==='performance'&&<><div className="kpi-grid performance-kpis">{[['Brier score','—','Serve storico probabilistico'],['Log loss','—','Serve storico probabilistico'],['ROI simulato','—','Non ancora calcolato'],['Calibrazione','Da validare','Backtest cronologico']].map(([a,b,c])=><div className="kpi-card" key={a}><div className="kpi-top"><span>{a}</span><span className="kpi-icon purple">↗</span></div><strong className={b.length>5?'model-number':''}>{b}</strong><small>{c}</small></div>)}</div><section className="panel page-panel"><PanelHead eyebrow="MODEL VALIDATION" title="Qualità e performance"/><div className="empty-block large-empty"><span className="empty-icon">▥</span><h3>Nessun risultato di performance affidabile</h3><p>Prima dei grafici servono predizioni registrate prima degli eventi, esiti verificati, quote timestamped e test fuori campione. Non mostriamo rendimenti inventati.</p></div><div className="validation-checks"><span>✓ Storico versionato</span><span>✓ Fonte ed timestamp</span><span>◷ Settlement automatico da collegare</span><span>◷ Backtest out-of-sample da completare</span></div></section></>}
    {page==='simulator'&&<div className="page-two-col"><section className="panel page-panel"><PanelHead eyebrow="WHAT-IF LAB" title="Simulatore di scenari" right={<DemoBadge>IPOTETICO</DemoBadge>}/><p className="body-muted">Modifica i parametri per esplorare uno scenario. Questi controlli non aggiornano un modello calibrato e il risultato è puramente dimostrativo.</p><Range label="Forza relativa casa" value={simHome} setValue={setSimHome} min={20} max={95}/><Range label="Forza relativa trasferta" value={simAway} setValue={setSimAway} min={20} max={95}/><Range label="Giorni di riposo casa" value={simRest} setValue={setSimRest} min={0} max={10}/><button className="button secondary full" onClick={()=>{setSimHome(65);setSimAway(58);setSimRest(4);}}>Ripristina scenario</button></section><section className="panel page-panel"><PanelHead eyebrow="SCENARIO OUTPUT" title="Lettura qualitativa"/><div className="scenario-result"><div className="scenario-circle">{Math.max(5,Math.min(95,Math.round(50+(simHome-simAway)*.45+(simRest-4)*.7)))}<small>Indice casa</small></div><div><h3>{simHome>simAway+10?'Vantaggio relativo casa':simAway>simHome+10?'Vantaggio relativo trasferta':'Scenario bilanciato'}</h3><p>La differenza tra parametri impostati è usata solo per mostrare un comportamento interattivo della UI. Non è una probabilità di vittoria.</p><span className="demo-badge">NON È UN PRONOSTICO</span></div></div><div className="scenario-bar"><i style={{width:`${simHome}%`}}/><span style={{width:`${simAway}%`}}/></div><div className="scenario-labels"><span>Casa · {simHome}/100</span><span>Trasferta · {simAway}/100</span></div></section></div>}
    {page==='settings'&&<div className="page-two-col"><section className="panel page-panel"><PanelHead eyebrow="PREFERENCES" title="Preferenze applicazione"/><label className="settings-line"><span><b>Tema scuro</b><small>Interfaccia antracite ad alto contrasto</small></span><span className="switch active">ON</span></label><label className="settings-line"><span><b>Fuso orario</b><small>Usato per report e orari partite</small></span><strong>Europe/Rome</strong></label><label className="settings-line"><span><b>Notifiche in-app</b><small>Avvisi per aggiornamenti e report</small></span><span className="switch active">ON</span></label><label className="settings-line"><span><b>Web push</b><small>Richiede supporto iOS e installazione in Home</small></span><button className={`switch ${pushEnabled?'active':''}`} onClick={()=>setPushEnabled(!pushEnabled)}>{pushEnabled?'ON':'OFF'}</button></label><button className="button primary full" onClick={()=>notify('Preferenze aggiornate in questa sessione')}>Salva preferenze</button></section><section className="panel page-panel"><PanelHead eyebrow="DATA SOURCES" title="Connessione e copertura"/><div className="provider-status"><span className={`connection-dot ${connected?'ok':''}`}/><div><b>{connected?'Backend raggiungibile':'Backend non collegato'}</b><small>Fonte dati: {health?.data_provider||'demo locale'}</small><small>Motore AI: {health?.ai_provider||'fallback dimostrativo'}</small></div><button className="button secondary" onClick={loadData}>Testa connessione</button></div><div className="settings-info"><b>Fonti da configurare</b><p>Calendario/risultati, quote multi-bookmaker, dati live, formazioni, xG, infortuni, immagini e notizie sono integrazioni separate; richiedono verifica di copertura, licenze e costi.</p></div><div className="settings-info"><b>Privacy e accesso</b><p>Questa build è un prototipo, non pubblicarlo aperto: prima del deploy servono autenticazione, autorizzazioni lato server, secret management, backup e policy privacy.</p></div></section></div>}
    </div>;
}
function Range({label,value,setValue,min,max}) { return <label className="range-control"><span><b>{label}</b><strong>{value}</strong></span><input type="range" min={min} max={max} value={value} onChange={e=>setValue(Number(e.target.value))}/><small>Parametro ipotetico · {min}–{max}</small></label>; }
