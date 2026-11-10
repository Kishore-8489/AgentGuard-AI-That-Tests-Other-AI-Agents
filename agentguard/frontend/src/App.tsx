import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity, ArrowDownRight, ArrowUpRight, CheckCircle2, ChevronRight,
  CircleDot, Code2, GitCompareArrows, GitFork, LockKeyhole, Play,
  RefreshCcw, Shield, ShieldAlert, ShieldCheck, Terminal, XCircle,
} from 'lucide-react';
import { api, type Comparison, type DemoConfig, type Finding, type Result, type Run, type TraceEvent } from './api';

type Profile = 'vulnerable' | 'hardened';
const profileFor = (run: Run, demo: DemoConfig | null): Profile | undefined =>
  run.agent_version_id === demo?.versions.vulnerable ? 'vulnerable' :
    run.agent_version_id === demo?.versions.hardened ? 'hardened' : undefined;

function App() {
  const [demo, setDemo] = useState<DemoConfig | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [activeRun, setActiveRun] = useState<Run | null>(null);
  const [results, setResults] = useState<Result[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [selected, setSelected] = useState<Result | null>(null);
  const [trace, setTrace] = useState<TraceEvent[]>([]);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const reload = useCallback(async () => {
    const all = await api.runs();
    setRuns(all);
    return all;
  }, []);

  useEffect(() => {
    let live = true;
    api.bootstrap().then(async (data) => {
      if (!live) return;
      setDemo(data);
      const all = await api.runs();
      if (!live) return;
      setRuns(all);
      setActiveRun(all[0] ?? null);
    }).catch((e: Error) => live && setError(e.message));
    return () => { live = false; };
  }, []);

  useEffect(() => {
    if (!activeRun) { setResults([]); setFindings([]); return; }
    let live = true;
    Promise.all([api.results(activeRun.id), api.findings(activeRun.id)]).then(([r, f]) => {
      if (live) { setResults(r); setFindings(f); setSelected(null); setTrace([]); }
    }).catch((e: Error) => live && setError(e.message));
    return () => { live = false; };
  }, [activeRun?.id, activeRun?.status]);

  useEffect(() => {
    if (!activeRun || ['completed', 'failed', 'cancelled'].includes(activeRun.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const fresh = await api.run(activeRun.id);
        setActiveRun(fresh);
        if (['completed', 'failed', 'cancelled'].includes(fresh.status)) await reload();
      } catch (e) { setError((e as Error).message); }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [activeRun?.id, activeRun?.status, reload]);

  const launch = async (profile: Profile) => {
    if (!demo || busy) return;
    setBusy(true); setError(''); setComparison(null);
    try {
      const run = await api.start(demo, profile);
      setActiveRun(run);
      await reload();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };

  const inspect = async (result: Result) => {
    setSelected(result);
    try { setTrace(await api.trace(result.id)); }
    catch (e) { setError((e as Error).message); }
  };

  const compare = async () => {
    if (!demo) return;
    const baseline = runs.find((r) => r.status === 'completed' && profileFor(r, demo) === 'vulnerable');
    const candidate = runs.find((r) => r.status === 'completed' && profileFor(r, demo) === 'hardened');
    if (!baseline || !candidate) { setError('Run both versions first to compare them.'); return; }
    try { setComparison(await api.compare(baseline.id, candidate.id)); setError(''); }
    catch (e) { setError((e as Error).message); }
  };

  const success = useMemo(() => results.filter((r) => r.status === 'passed').length, [results]);
  const critical = useMemo(() => findings.filter((f) => f.severity === 'critical').length, [findings]);
  const activeProfile = activeRun ? profileFor(activeRun, demo) : undefined;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-icon"><Shield size={21} strokeWidth={2.5} /></div><div>AgentGuard<small>AGENT RELIABILITY</small></div></div>
        <div className="side-group"><div className="side-label">WORKSPACE</div>
          <div className="side-link current"><Activity size={16} /> Overview</div>
          <div className="side-link"><ShieldCheck size={16} /> Test campaigns</div>
          <div className="side-link"><GitFork size={16} /> Agent versions</div>
          <div className="side-link"><Terminal size={16} /> Execution traces</div>
        </div>
        <div className="side-group"><div className="side-label">PLATFORM</div>
          <div className="side-link"><LockKeyhole size={16} /> Policy engine</div>
          <div className="side-link"><Code2 size={16} /> Developer API</div>
        </div>
        <div className="side-foot"><div className="status-dot" /> Local demo environment <small>Simulated agent actions only</small></div>
      </aside>
      <main className="main">
        <div className="topbar"><div className="breadcrumb">Workspace <ChevronRight size={15} /> AgentGuard Demo <ChevronRight size={15} /> <strong>Overview</strong></div><span className="env-pill">DEMO ENVIRONMENT</span></div>
        <div className="content">
          <div className="eyebrow"><CircleDot size={13} /> SECURITY & EVALUATION PLATFORM</div>
          <div className="hero"><div><h1>Agent reliability,<br/><em>explained.</em></h1><p>Stress-test your AI agents. Replay what went wrong. Verify that your next release actually fixes it.</p></div><div className="hero-symbol"><Shield size={83} strokeWidth={1.1}/><CheckCircle2 className="hero-symbol-check" size={28}/></div></div>
          {error && <div role="alert" className="error"><ShieldAlert size={16}/><span>{error}</span><button onClick={() => setError('')}>Dismiss</button></div>}
          <div className="metric-grid">
            <div className="metric"><span>Total campaigns</span><b>{runs.length}</b><small><Activity size={12}/> Recorded test runs</small></div>
            <div className="metric"><span>Current reliability</span><b>{activeRun?.score === null || !activeRun ? '—' : `${activeRun.score}%`}</b><small><ShieldCheck size={12}/> Latest selected run</small></div>
            <div className="metric"><span>Tests passing</span><b>{results.length ? `${success}/${results.length}` : '—'}</b><small><CheckCircle2 size={12}/> Deterministic evaluations</small></div>
            <div className="metric"><span>Critical findings</span><b className={critical ? 'red' : ''}>{activeRun?.status === 'completed' ? critical : '—'}</b><small><ShieldAlert size={12}/> Trace-backed violations</small></div>
          </div>

          <section className="panel launch-panel"><div><div className="section-eyebrow">01 / TEST CAMPAIGN</div><h2>Run an adversarial evaluation</h2><p>Both versions run the same five scenarios. No external model calls or real tool side effects.</p></div><div className="button-bar"><button className="btn btn-outline" disabled={busy || !demo} onClick={() => void launch('vulnerable')}><Play size={15}/> Run vulnerable agent</button><button className="btn btn-primary" disabled={busy || !demo} onClick={() => void launch('hardened')}><Play size={15}/> Run hardened agent</button></div></section>

          <div className="two-column">
            <section className="panel results-panel"><div className="panel-head"><div><div className="section-eyebrow">02 / TEST RESULTS</div><h2>Failure analysis</h2></div><button className="icon-button" aria-label="Refresh runs" onClick={() => void reload()}><RefreshCcw size={16}/></button></div>
              {!activeRun ? <div className="empty">Run an evaluation to see your agent's security and correctness results.</div> : <>
                <div className="run-label"><span className="version-tag">{activeProfile === 'vulnerable' ? 'v1.0 / vulnerable' : 'v1.1 / hardened'}</span><span className="run-status">{activeRun.status}</span></div>
                <div className="result-list">{results.length ? results.map((r) => <button key={r.id} className={`result-row ${selected?.id === r.id ? 'selected' : ''}`} onClick={() => void inspect(r)}>
                  {r.status === 'passed' ? <CheckCircle2 className="green" size={18} /> : <XCircle className="red" size={18} />}
                  <span><b>{r.name}</b><small>{r.category.replaceAll('_', ' ')}</small></span><span className={`result-state ${r.status}`}>{r.status.toUpperCase()}</span><ChevronRight size={15}/>
                </button>) : <div className="empty">{activeRun.status === 'failed' ? activeRun.error : 'Your test run is being processed…'}</div>}</div>
              </>}
            </section>
            <section className="panel trace-panel"><div className="panel-head"><div><div className="section-eyebrow">03 / EXECUTION TRACE</div><h2>Evidence timeline</h2></div><Terminal size={18} className="muted"/></div>
              {selected ? <><div className="trace-title">{selected.name}</div><div className="trace-events">{trace.map((event) => <div key={event.sequence} className="trace-event"><span className="trace-count">{String(event.sequence + 1).padStart(2, '0')}</span><div><strong>{event.event_type}</strong><pre>{JSON.stringify(event.detail, null, 2)}</pre></div></div>)}</div></> : <div className="empty">Select a test result to inspect input, retrieval, simulated tool attempts, and agent output.</div>}
            </section>
          </div>

          <section className="panel"><div className="panel-head"><div><div className="section-eyebrow">04 / REGRESSION INSIGHTS</div><h2>Version comparison</h2><p>Find precisely which failures were resolved or introduced.</p></div><button className="btn btn-outline" onClick={() => void compare()}><GitCompareArrows size={16}/> Compare versions</button></div>
            {comparison ? <div className="comparison"><div><small>BASELINE v1.0</small><strong>{comparison.baseline_score}%</strong></div><ArrowUpRight className="green" size={26}/><div><small>CANDIDATE v1.1</small><strong className="green">{comparison.candidate_score}%</strong></div><div><small>FIXED FAILURES</small><strong>{comparison.fixed_test_case_ids.length}</strong></div><div><small>NEW REGRESSIONS</small><strong>{comparison.regressed_test_case_ids.length}</strong></div></div> : <div className="comparison-placeholder"><GitCompareArrows size={18}/> Run both agent versions, then compare their results to expose fixed and regressed tests. <ArrowDownRight size={15}/></div>}
          </section>
          <section className="panel"><div className="panel-head"><div><div className="section-eyebrow">05 / RUN HISTORY</div><h2>Recent campaigns</h2></div></div><div className="history">{runs.map((run) => <button key={run.id} className={`history-row ${activeRun?.id === run.id ? 'active' : ''}`} onClick={() => setActiveRun(run)}><span className="history-profile">{profileFor(run, demo) === 'vulnerable' ? 'v1.0 Vulnerable' : 'v1.1 Hardened'}</span><span>{run.status}</span><strong>{run.score === null ? '—' : `${run.score}%`}</strong><ChevronRight size={15}/></button>)}{!runs.length && <div className="empty">No campaigns yet.</div>}</div></section>
          <footer>AgentGuard v0.1.0 <span>•</span> Deterministic demo <span>•</span> Built for evidence, not hype.</footer>
        </div>
      </main>
    </div>
  );
}

export default App;
