import { useMemo, useState } from 'react';
import { Info, Search, Target, TrendingUp } from 'lucide-react';
import Panel from '../../components/common/Panel';
import MetricCard from '../../components/common/MetricCard';
import DataBadge from '../../components/common/DataBadge';
import EmptyState from '../../components/common/EmptyState';
import { sdgs } from '../../data/sdg';
import { SCOPES, SDG_DATA_NOTE, STATUS_BANDS } from '../../data/sdgProgress';
import SdgGoalCard from './SdgGoalCard';
import SdgDetail from './SdgDetail';
import SdgScoreChart from './SdgScoreChart';
import { average, scoreFor, sortGoals, statusFor } from './utils';
import './SdgTracker.css';

const SORTS = [
  { value: 'goal', label: 'Goal number' },
  { value: 'score-desc', label: 'Highest score first' },
  { value: 'score-asc', label: 'Lowest score first' },
];

export default function SdgTracker() {
  const [scopeId, setScopeId] = useState('world');
  const [status, setStatus] = useState('all');
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState('goal');
  const [selected, setSelected] = useState(13);

  const scope = SCOPES.find((s) => s.id === scopeId);
  const scores = sdgs.map((g) => scoreFor(scopeId, g.number));
  const counts = Object.fromEntries(STATUS_BANDS.map((b) => [b.id, scores.filter((s) => statusFor(s).id === b.id).length]));

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = sdgs.filter((goal) => {
      if (status !== 'all' && statusFor(scoreFor(scopeId, goal.number)).id !== status) return false;
      if (!q) return true;
      return goal.name.toLowerCase().includes(q) || String(goal.number) === q || goal.description.toLowerCase().includes(q);
    });
    return sortGoals(filtered, sort, scopeId);
  }, [query, status, sort, scopeId]);

  const selectedGoal = sdgs.find((g) => g.number === selected);
  const best = sdgs.reduce((a, b) => (scoreFor(scopeId, b.number) > scoreFor(scopeId, a.number) ? b : a));
  const weakest = sdgs.reduce((a, b) => (scoreFor(scopeId, b.number) < scoreFor(scopeId, a.number) ? b : a));

  function reset() {
    setStatus('all');
    setQuery('');
    setSort('goal');
  }

  return (
    <div className="page sdgt">
      <header className="page-header reveal">
        <div>
          <div className="eyebrow"><Target size={12} /> SDG Tracker</div>
          <h1>Sustainable Development Goals</h1>
          <p>Progress across all 17 goals, with indicator detail for each one.</p>
        </div>
        <DataBadge type="sample">Sample data</DataBadge>
      </header>

      <div className="sdgt-note reveal" role="note" style={{ '--i': 1 }}>
        <Info size={15} />
        <p><strong>Sample data.</strong> {SDG_DATA_NOTE} The goal names, wording and colours are the official ones.</p>
      </div>

      <div className="panel sdgt-scope reveal" style={{ '--i': 2 }}>
        <span className="section-label">Show progress for</span>
        <div className="chip-group" role="group" aria-label="Scope">
          {SCOPES.map((s) => (
            <button key={s.id} type="button" className={`chip ${scopeId === s.id ? 'active' : ''}`} aria-pressed={scopeId === s.id} onClick={() => setScopeId(s.id)}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <section className="sdgt-stats" aria-label="Summary">
        <MetricCard index={3} label="Average score" value={`${Math.round(average(scores))}/100`} note={`${scope.label} · sample`} icon={TrendingUp} badge="sample" />
        <MetricCard index={4} label="On track" value={counts['on-track']} note="goals scoring 70+" />
        <MetricCard index={5} label="Moderate progress" value={counts.moderate} note="goals scoring 50–69" />
        <MetricCard index={6} label="Off track" value={counts['off-track']} note="goals scoring below 50" />
      </section>

      <Panel index={7} title="Score by goal" subtitle={`${scope.label} · click a bar to open that goal`} actions={<DataBadge type="sample" />} className="mb">
        <SdgScoreChart scopeId={scopeId} scopeLabel={scope.label} selected={selected} onSelect={setSelected} />
        <p className="fine-print">Strongest in this sample: Goal {best.number}, {best.name} ({scoreFor(scopeId, best.number)}). Weakest: Goal {weakest.number}, {weakest.name} ({scoreFor(scopeId, weakest.number)}).</p>
      </Panel>

      <div className="panel sdgt-filters reveal" style={{ '--i': 8 }}>
        <label className="search-field sdgt-search">
          <Search size={14} />
          <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search goals (name, number or topic)" aria-label="Search goals" />
        </label>
        <div className="chip-group" role="group" aria-label="Status">
          <button type="button" className={`chip ${status === 'all' ? 'active' : ''}`} aria-pressed={status === 'all'} onClick={() => setStatus('all')}>All goals</button>
          {STATUS_BANDS.map((b) => (
            <button key={b.id} type="button" className={`chip ${status === b.id ? 'active' : ''}`} aria-pressed={status === b.id} onClick={() => setStatus(b.id)}>
              {b.label} ({counts[b.id]})
            </button>
          ))}
        </div>
        <select className="select" value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort goals">
          {SORTS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      <div className="sdgt-main">
        <div className="sdgt-grid-wrap">
          {visible.length === 0 ? (
            <Panel>
              <EmptyState icon={Search} title="No goals match">
                Try a different word, or <button type="button" className="btn btn-ghost" onClick={reset}>clear the filters</button>.
              </EmptyState>
            </Panel>
          ) : (
            <div className="sdgt-grid">
              {visible.map((goal, i) => (
                <SdgGoalCard key={goal.number} goal={goal} index={i} score={scoreFor(scopeId, goal.number)} selected={goal.number === selected} onSelect={setSelected} />
              ))}
            </div>
          )}
        </div>

        <Panel title={`Goal ${selectedGoal.number}`} subtitle={scope.label} className="sdgt-detail-panel" key={`${selected}-${scopeId}`}>
          <SdgDetail goal={selectedGoal} scope={scope} />
        </Panel>
      </div>
    </div>
  );
}
