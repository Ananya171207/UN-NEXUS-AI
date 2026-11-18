import { useMemo, useState } from 'react';
import { BookOpen, Info } from 'lucide-react';
import Panel from '../../components/common/Panel';
import MetricCard from '../../components/common/MetricCard';
import DataBadge from '../../components/common/DataBadge';
import CopyButton from '../../components/common/CopyButton';
import EmptyState from '../../components/common/EmptyState';
import ProgressBar from '../../components/common/ProgressBar';
import Tabs from '../../components/common/Tabs';
import { countries } from '../../data/countries';
import {
  COMPARISON_DATA_NOTE, DEFAULT_COMPARE, INDICATORS, INDICATOR_GROUPS,
} from '../../data/comparisonData';
import CountryPicker from './CountryPicker';
import BarComparison from './BarComparison';
import ProfileRadar from './ProfileRadar';
import ComparisonTable from './ComparisonTable';
import {
  PROFILE_INDICATORS, buildInsights, formatValue, median, medianOf, profileScore, rankOf,
} from './utils';
import './IndiaVsWorld.css';

const india = countries.find((c) => c.id === 'IN');
const TOTAL = countries.length;
function ordinal(n) {
  const teen = n % 100 >= 11 && n % 100 <= 13;
  const suffix = teen ? 'th' : { 1: 'st', 2: 'nd', 3: 'rd' }[n % 10] || 'th';
  return `${n}${suffix}`;
}

function tableText(others) {
  const header = ['Indicator', 'India', ...others.map((c) => c.name), 'Sample median'].join(' | ');
  const rows = INDICATORS.map((i) => [`${i.label} (${i.unit})`, formatValue(i, i.get(india)), ...others.map((c) => formatValue(i, i.get(c))), formatValue(i, Number(medianOf(i, countries).toFixed(1)))].join(' | '));
  return ['India compared with other countries — SAMPLE DATA, not official statistics', '', header, ...rows].join('\n');
}

export default function IndiaVsWorld() {
  const [compareIds, setCompareIds] = useState(DEFAULT_COMPARE);
  const [group, setGroup] = useState(INDICATOR_GROUPS[0]);
  const [indicatorId, setIndicatorId] = useState('gdp');
  const [showAll, setShowAll] = useState(false);
  const [radarId, setRadarId] = useState('');

  const others = compareIds.map((id) => countries.find((c) => c.id === id)).filter(Boolean);
  const groupIndicators = INDICATORS.filter((i) => i.group === group);
  const indicator = INDICATORS.find((i) => i.id === indicatorId);
  const med = medianOf(indicator, countries);

  function changeGroup(next) {
    setGroup(next);
    setIndicatorId(INDICATORS.find((i) => i.group === next).id);
  }

  const chartRows = useMemo(() => {
    const set = showAll ? countries : [india, ...others];
    return [...set]
      .map((c) => ({ id: c.id, name: c.name, value: indicator.get(c), label: formatValue(indicator, indicator.get(c)) }))
      .sort((a, b) => (indicator.better === 'lower' ? a.value - b.value : b.value - a.value));
  }, [showAll, others, indicator]);

  const radarOther = others.find((c) => c.id === radarId) || others[0] || null;
  const radarData = PROFILE_INDICATORS.map((i) => ({
    axis: i.short,
    india: profileScore(i, countries, india),
    other: radarOther ? profileScore(i, countries, radarOther) : undefined,
    median: Math.round(median(countries.map((c) => profileScore(i, countries, c)))),
  }));

  const insights = useMemo(() => buildInsights(countries, india), []);
  const headline = ['population', 'gdpPc', 'lifeExpectancy', 'renewable'].map((id) => INDICATORS.find((i) => i.id === id));

  return (
    <div className="page iw">
      <header className="page-header reveal">
        <div>
          <div className="eyebrow"><BookOpen size={12} /> India vs the World</div>
          <h1>India compared with other countries</h1>
          <p>Choose countries, switch indicators and see where India stands.</p>
        </div>
        <DataBadge type="sample">Sample data</DataBadge>
      </header>

      <div className="iw-note reveal" role="note" style={{ '--i': 1 }}>
        <Info size={15} />
        <p>
          <strong>Sample data.</strong> {COMPARISON_DATA_NOTE} The “sample median” is the middle value of these {TOTAL} countries,
          not a world average, and ranks are out of {TOTAL}, not out of all countries.
        </p>
      </div>

      <div className="panel reveal" style={{ '--i': 2 }}>
        <div className="panel-body"><CountryPicker countries={countries} compareIds={compareIds} onChange={setCompareIds} /></div>
      </div>

      <section className="iw-stats" aria-label="India at a glance">
        {headline.map((i, idx) => {
          const rank = rankOf(i, countries, 'IN');
          return (
            <MetricCard
              key={i.id}
              index={idx + 3}
              label={i.label}
              value={formatValue(i, i.get(india))}
              note={`${i.better === 'neutral' ? 'Size rank' : 'Rank'} ${ordinal(rank)} of ${TOTAL} · median ${formatValue(i, Number(medianOf(i, countries).toFixed(1)))}`}
              badge="sample"
            />
          );
        })}
      </section>

      {others.length === 0 && !showAll ? (
        <Panel index={7} title="Comparison" className="mb">
          <EmptyState icon={BookOpen} title="Choose a country to compare">
            Add a country above, pick one of the quick selections, or show all sample countries.
            <br />
            <button type="button" className="btn" onClick={() => setShowAll(true)}>Show all {TOTAL} sample countries</button>
          </EmptyState>
        </Panel>
      ) : (
        <div className="iw-main">
          <Panel index={7} title="Indicator comparison" subtitle="India is highlighted · dashed line is the sample median" actions={<DataBadge type="sample" />}>
            <Tabs tabs={INDICATOR_GROUPS.map((g) => ({ id: g, label: g }))} active={group} onChange={changeGroup} label="Indicator groups" />
            <div className="chip-group iw-indicators" role="group" aria-label="Indicator">
              {groupIndicators.map((i) => (
                <button key={i.id} type="button" className={`chip ${indicatorId === i.id ? 'active' : ''}`} aria-pressed={indicatorId === i.id} onClick={() => setIndicatorId(i.id)}>
                  {i.label}
                </button>
              ))}
            </div>
            <p className="iw-unit">
              {indicator.label} · {indicator.unit}
              {indicator.better === 'higher' && ' · higher is better'}
              {indicator.better === 'lower' && ' · lower is better'}
              {indicator.better === 'neutral' && ' · size, not a quality measure'}
            </p>
            <BarComparison indicator={indicator} rows={chartRows} median={med} />
            <label className="iw-toggle">
              <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} />
              Show all {TOTAL} sample countries
            </label>
          </Panel>

          <Panel index={8} title="Overall profile" subtitle="Each indicator rescaled 0–100 across the sample" actions={<DataBadge type="sample" />}>
            {others.length > 1 && (
              <select className="select iw-radar-select" value={radarOther?.id || ''} onChange={(e) => setRadarId(e.target.value)} aria-label="Country shown against India">
                {others.map((c) => <option key={c.id} value={c.id}>India vs {c.name}</option>)}
              </select>
            )}
            <ProfileRadar data={radarData} otherName={radarOther?.name} />
            <p className="fine-print">Further out is better: indicators where lower is better (child deaths, CO2) are flipped, and GDP per person uses a log scale. The scale is relative to these {TOTAL} countries only.</p>
          </Panel>
        </div>
      )}

      <div className="iw-insights">
        <Panel index={9} title="Where India does well" subtitle={`Top third of the ${TOTAL} sample countries`} actions={<DataBadge type="sample" />}>
          <ul className="iw-rank-list">
            {insights.strengths.length === 0 && <li className="muted">No indicator in the top third.</li>}
            {insights.strengths.map((r) => (
              <li key={r.indicator.id}>
                <div><strong>{r.indicator.label}</strong><small>{formatValue(r.indicator, r.value)} · median {formatValue(r.indicator, Number(r.med.toFixed(1)))}</small></div>
                <span className="iw-rank good">{ordinal(r.rank)}</span>
                <ProgressBar value={TOTAL - r.rank + 1} min={0} max={TOTAL} label={`Rank ${r.rank}`} />
              </li>
            ))}
          </ul>
        </Panel>
        <Panel index={10} title="Where India lags" subtitle={`Bottom third of the ${TOTAL} sample countries`} actions={<DataBadge type="sample" />}>
          <ul className="iw-rank-list">
            {insights.gaps.length === 0 && <li className="muted">No indicator in the bottom third.</li>}
            {insights.gaps.map((r) => (
              <li key={r.indicator.id}>
                <div><strong>{r.indicator.label}</strong><small>{formatValue(r.indicator, r.value)} · median {formatValue(r.indicator, Number(r.med.toFixed(1)))}</small></div>
                <span className="iw-rank low">{ordinal(r.rank)}</span>
                <ProgressBar value={TOTAL - r.rank + 1} min={0} max={TOTAL} tone="amber" label={`Rank ${r.rank}`} />
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <Panel
        index={11}
        title="Full comparison table"
        subtitle="Every indicator side by side"
        actions={<><DataBadge type="sample" /><CopyButton text={tableText(others)} label="Copy table" /></>}
      >
        <ComparisonTable india={india} others={others} sampleSet={countries} />
      </Panel>
    </div>
  );
}
