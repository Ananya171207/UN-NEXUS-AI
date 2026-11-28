import { useEffect, useMemo, useState } from 'react';
import { BookOpen, Info } from 'lucide-react';
import Panel from '../../components/common/Panel';
import MetricCard from '../../components/common/MetricCard';
import DataBadge from '../../components/common/DataBadge';
import CopyButton from '../../components/common/CopyButton';
import EmptyState from '../../components/common/EmptyState';
import ProgressBar from '../../components/common/ProgressBar';
import Tabs from '../../components/common/Tabs';
import { DEFAULT_COMPARE } from '../../data/comparisonData';
import {
  getComparisonCountries,
  getCountryComparison,
  getIndicatorCatalogue,
} from '../../services/comparisonService';
import CountryPicker from './CountryPicker';
import BarComparison from './BarComparison';
import ComparisonTable from './ComparisonTable';
import { formatValue } from './utils';
import './IndiaVsWorld.css';

const HEADLINE_KEYS = ['population', 'gdp_per_capita', 'life_expectancy', 'renewable_electricity'];

function countryName(comparison, code) {
  return comparison?.countryMetadata?.[code]?.name || code;
}

function createCopyText(comparison, indicators) {
  if (!comparison) return '';
  const codes = comparison.countries || [];
  const baseline = comparison.baseline?.country;
  const headers = ['Indicator', ...codes.map((code) => countryName(comparison, code))];
  const rows = indicators.map((indicator) => [
    `${indicator.label} (${indicator.unit})`,
    ...codes.map((code) => {
      const entry = comparison.comparison?.[code]?.[indicator.key];
      const value = formatValue(indicator, entry);
      return entry?.year ? `${value} (${entry.year})` : value;
    }),
  ]);
  return [
    `UN NEXUS AI — India vs World`,
    `Source: ${comparison.source || 'World Bank Open Data'}`,
    `Baseline: ${countryName(comparison, baseline)}`,
    `Latest updated: ${comparison.lastUpdated || 'Not available'}`,
    '',
    headers.join(' | '),
    ...rows.map((row) => row.join(' | ')),
  ].join('\n');
}

export default function IndiaVsWorld() {
  const [countries, setCountries] = useState([]);
  const [catalogue, setCatalogue] = useState(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialError, setInitialError] = useState('');

  const [compareIds, setCompareIds] = useState(DEFAULT_COMPARE);
  const [comparison, setComparison] = useState(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState('');

  const [group, setGroup] = useState('economic');
  const [indicatorKey, setIndicatorKey] = useState('gdp');

  // Load country names/metadata and the indicator catalogue from the live backend.
  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    Promise.all([
      getComparisonCountries({ signal: controller.signal }),
      getIndicatorCatalogue({ signal: controller.signal }),
    ])
      .then(([countryData, indicatorData]) => {
        if (!active) return;
        setCountries(countryData);
        setCatalogue(indicatorData);
      })
      .catch((error) => {
        if (!active || error?.name === 'AbortError') return;
        setInitialError(error.message || 'Could not load comparison metadata.');
      })
      .finally(() => {
        if (active) setInitialLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  const india = useMemo(
    () => countries.find((country) => country.id === 'IN' || country.code === 'IND') || null,
    [countries]
  );

  const selectedCodes = useMemo(() => {
    if (!india) return [];
    const selected = compareIds
      .map((id) => countries.find((country) => country.id === id))
      .filter(Boolean);
    return [india, ...selected].map((country) => country.code || country.id);
  }, [countries, compareIds, india]);

  // Re-fetch only when the selected country set changes. Backend caching avoids duplicate upstream calls.
  useEffect(() => {
    if (initialLoading || initialError) return undefined;

    if (!india) {
      setComparison(null);
      setComparisonError('India was not returned by the country metadata endpoint.');
      setComparisonLoading(false);
      return undefined;
    }

    if (compareIds.length === 0) {
      setComparison(null);
      setComparisonError('Select at least one country to compare with India.');
      setComparisonLoading(false);
      return undefined;
    }

    if (selectedCodes.length < 2 || selectedCodes.length > 5) {
      setComparison(null);
      setComparisonError('Select between one and four countries in addition to India.');
      setComparisonLoading(false);
      return undefined;
    }

    const controller = new AbortController();
    let active = true;
    setComparison(null);
    setComparisonError('');
    setComparisonLoading(true);

    getCountryComparison(selectedCodes, { signal: controller.signal })
      .then((result) => {
        if (active) setComparison(result);
      })
      .catch((error) => {
        if (!active || error?.name === 'AbortError') return;
        setComparisonError(error.message || 'The country comparison could not be loaded.');
      })
      .finally(() => {
        if (active) setComparisonLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [initialLoading, initialError, india, compareIds, selectedCodes]);

  const indicators = catalogue?.indicators || [];
  const categories = catalogue?.categories || [];
  const activeGroup = categories.some((category) => category.id === group)
    ? group
    : categories[0]?.id || 'economic';
  const groupIndicators = indicators.filter((indicator) => indicator.category === activeGroup);
  const indicator = indicators.find((item) => item.key === indicatorKey) || groupIndicators[0] || indicators[0];

  function changeGroup(nextGroup) {
    setGroup(nextGroup);
    const first = indicators.find((item) => item.category === nextGroup);
    if (first) setIndicatorKey(first.key);
  }

  const analytics = indicator ? comparison?.analytics?.[indicator.key] : null;
  const chartRows = useMemo(() => {
    if (!comparison || !indicator || !analytics) return [];

    const valuesByCode = new Map((analytics.values || []).map((row) => [row.country, row]));
    const orderedCodes = analytics.orderedBestToWorst || analytics.orderedByValue || comparison.countries || [];

    return orderedCodes
      .map((code) => {
        const valueRow = valuesByCode.get(code);
        const metadata = comparison.countryMetadata?.[code];
        if (!valueRow?.usable || !Number.isFinite(valueRow.value)) return null;
        return {
          code,
          id: metadata?.alpha2 || code,
          name: metadata?.name || code,
          value: valueRow.value,
          label: formatValue(indicator, valueRow.value),
          year: valueRow.year,
          isBaseline: code === comparison.baseline?.country,
        };
      })
      .filter(Boolean);
  }, [comparison, indicator, analytics]);

  const headlineMetrics = HEADLINE_KEYS
    .map((key) => {
      const metadata = indicators.find((item) => item.key === key);
      const entry = comparison?.comparison?.IND?.[key];
      return metadata ? { metadata, entry } : null;
    })
    .filter(Boolean);

  const copyText = useMemo(
    () => createCopyText(comparison, indicators),
    [comparison, indicators]
  );

  const baselineCode = comparison?.baseline?.country || 'IND';
  const baselineName = comparison ? countryName(comparison, baselineCode) : 'India';
  const baselineValue = analytics?.baseline?.value;

  return (
    <div className="page iw">
      <header className="page-header reveal">
        <div>
          <div className="eyebrow"><BookOpen size={12} /> India vs the World</div>
          <h1>India compared with other countries</h1>
          <p>Compare the latest available economic, social and environmental indicators from the World Bank.</p>
        </div>
        <DataBadge type="reference">World Bank Open Data</DataBadge>
      </header>

      <div className="iw-note reveal" role="note" style={{ '--i': 1 }}>
        <Info size={15} />
        <p>
          <strong>Source-backed comparison.</strong> Values come from World Bank Open Data. Reporting years can differ
          by country and indicator; unavailable observations are shown rather than estimated. No composite development
          score is calculated.
        </p>
      </div>

      <div className="panel reveal" style={{ '--i': 2 }}>
        <div className="panel-body">
          {initialLoading ? (
            <p className="muted">Loading country list and indicator catalogue…</p>
          ) : initialError ? (
            <EmptyState icon={Info} title="Could not connect to comparison data">
              {initialError}
            </EmptyState>
          ) : (
            <CountryPicker countries={countries} compareIds={compareIds} onChange={setCompareIds} />
          )}
        </div>
      </div>

      {initialLoading ? (
        <Panel index={3} title="India vs World" className="mb">
          <p className="muted">Loading live comparison data…</p>
        </Panel>
      ) : initialError ? (
        <Panel index={3} title="Live data unavailable" className="mb">
          <EmptyState icon={Info} title="The backend could not be reached">
            {initialError} Check that FastAPI is running and that VITE_API_URL points to it.
          </EmptyState>
        </Panel>
      ) : comparisonLoading ? (
        <Panel index={3} title="Loading comparison" className="mb">
          <p className="muted">Fetching the latest available World Bank observations for the selected countries…</p>
        </Panel>
      ) : comparisonError ? (
        <Panel index={3} title="Comparison unavailable" className="mb">
          <EmptyState icon={Info} title="Select countries or check the API response">
            {comparisonError}
          </EmptyState>
        </Panel>
      ) : comparison ? (
        <>
          <section className="iw-stats" aria-label="India at a glance">
            {headlineMetrics.map(({ metadata, entry }, index) => (
              <MetricCard
                key={metadata.key}
                index={index + 3}
                label={metadata.label}
                value={formatValue(metadata, entry)}
                note={entry?.year ? `World Bank · reporting year ${entry.year}` : statusNote(entry)}
              />
            ))}
          </section>

          <div className="iw-main">
            <Panel
              index={7}
              title="Indicator comparison"
              subtitle={`India is the baseline · dashed line marks ${baselineName}`}
              actions={<span className="badge badge-neutral">{comparison.dataStatus === 'complete' ? 'Complete data' : 'Partial data'}</span>}
            >
              <Tabs
                tabs={categories.map((category) => ({ id: category.id, label: category.label }))}
                active={activeGroup}
                onChange={changeGroup}
                label="Indicator categories"
              />
              <div className="chip-group iw-indicators" role="group" aria-label="Indicator">
                {groupIndicators.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    className={`chip ${indicator?.key === item.key ? 'active' : ''}`}
                    aria-pressed={indicator?.key === item.key}
                    onClick={() => setIndicatorKey(item.key)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              {indicator && (
                <>
                  <p className="iw-unit">
                    {indicator.label} · {indicator.unit}
                    {indicator.direction === 'higher_is_better' && ' · higher is generally better'}
                    {indicator.direction === 'lower_is_better' && ' · lower is generally better'}
                    {indicator.direction === 'contextual' && ' · contextual indicator'}
                  </p>
                  {indicator.interpretation && <p className="fine-print">{indicator.interpretation}</p>}
                  {chartRows.length > 0 ? (
                    <BarComparison
                      indicator={indicator}
                      rows={chartRows}
                      baselineValue={baselineValue}
                      baselineName={baselineName}
                    />
                  ) : (
                    <EmptyState icon={Info} title="No comparable values are available">
                      The selected indicator has no usable observations for these countries yet.
                    </EmptyState>
                  )}
                </>
              )}
            </Panel>

            <Panel
              index={8}
              title="Data coverage"
              subtitle="Available observations across the selected countries"
            >
              <ul className="iw-rank-list">
                {(comparison.countries || []).map((code) => {
                  const quality = comparison.dataQuality?.[code] || {};
                  const name = countryName(comparison, code);
                  const total = quality.total || indicators.length;
                  const available = quality.available || 0;
                  return (
                    <li key={code}>
                      <div>
                        <strong>{name}</strong>
                        <small>
                          {available} of {total} indicators available
                          {quality.stale ? ` · ${quality.stale} cached/stale` : ''}
                        </small>
                      </div>
                      <span className="iw-rank">{total ? Math.round((available / total) * 100) : 0}%</span>
                      <ProgressBar value={available} min={0} max={Math.max(total, 1)} label={`${name} data coverage`} />
                      <small className="muted">
                        {quality.noData || 0} not reported · {quality.pending || 0} pending · {quality.error || 0} errors
                      </small>
                    </li>
                  );
                })}
              </ul>
            </Panel>
          </div>

          <div className="iw-insights">
            <Panel
              index={9}
              title="Data quality and interpretation"
              subtitle={`Baseline: ${baselineName} · ${comparison.source || 'World Bank Open Data'}`}
              actions={<span className="badge badge-neutral">{comparison.dataStatus === 'complete' ? 'Complete' : 'Partial'}</span>}
            >
              {comparison.warnings?.length ? (
                <ul className="iw-rank-list">
                  {comparison.warnings.map((warning, index) => (
                    <li key={`${index}-${warning}`}><div><small>{warning}</small></div></li>
                  ))}
                </ul>
              ) : (
                <p className="muted">No data-quality or reporting-year warnings were returned for this selection.</p>
              )}
              <p className="fine-print">
                Differences are calculated per indicator against the baseline. Reporting years may differ; check each
                indicator’s year before interpreting a difference. GDP, population, inflation and other contextual
                measures are not labelled as better or worse.
              </p>
              {comparison.lastUpdated && (
                <p className="fine-print">Oldest observation refresh in this response: {new Date(comparison.lastUpdated).toLocaleString()}</p>
              )}
            </Panel>
          </div>

          <Panel
            index={10}
            title="Full comparison table"
            subtitle="All registered indicators, values, reporting years and differences"
            actions={<CopyButton text={copyText} label="Copy table" />}
          >
            <ComparisonTable comparison={comparison} indicators={indicators} />
          </Panel>
        </>
      ) : (
        <Panel index={3} title="Comparison" className="mb">
          <EmptyState icon={BookOpen} title="Choose a country to compare">
            Add at least one country above. India is included automatically as the baseline.
          </EmptyState>
        </Panel>
      )}
    </div>
  );
}

function statusNote(entry) {
  if (!entry) return 'No observation returned';
  if (entry.status && entry.status !== 'available') {
    return entry.status === 'no_data'
      ? 'Not reported by the World Bank'
      : entry.status === 'pending'
        ? 'Still loading; retry shortly'
        : 'Currently unavailable';
  }
  return 'World Bank Open Data';
}
