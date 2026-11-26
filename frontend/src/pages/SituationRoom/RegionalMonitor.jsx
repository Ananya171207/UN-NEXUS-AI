import Panel from '../../components/common/Panel';
import { SEVERITY_LEVELS } from '../../data/taxonomy';

// One row per region. Clicking a row filters the whole page to that region.
export default function RegionalMonitor({
  summaries,
  activeRegion,
  onSelectRegion,
}) {
  const max = Math.max(1, ...summaries.map((s) => s.total));

  return (
    <Panel
      title="Regional monitoring"
      subtitle="Events by region and severity (respects category and severity filters)"
      className="regional-panel"
      index={5}
    >
      <ul className="region-list">
        {summaries.map((summary) => (
          <li key={summary.region}>
            <button
              type="button"
              className={`region-row ${
                activeRegion === summary.region ? 'active' : ''
              }`}
              aria-pressed={activeRegion === summary.region}
              onClick={() =>
                onSelectRegion(
                  activeRegion === summary.region ? 'All' : summary.region
                )
              }
            >
              <div className="region-top">
                <strong>{summary.region}</strong>

                <span className="region-count">
                  {summary.total} event{summary.total === 1 ? '' : 's'} ·{' '}
                  {summary.countryCount} countries
                </span>
              </div>

              <div className="region-bar" aria-hidden="true">
                {SEVERITY_LEVELS.map((level) => (
                  <span
                    key={level}
                    className={`bar-${level}`}
                    style={{
                      width: `${(summary.bySeverity[level] / max) * 100}%`,
                    }}
                    title={`${summary.bySeverity[level]} ${level}`}
                  />
                ))}
              </div>

              <div className="region-foot">
                {summary.total === 0 ? (
                  <span className="muted">No matching events</span>
                ) : (
                  <span className={`severity severity-${summary.highest}`}>
                    Highest: {summary.highest}
                  </span>
                )}
              </div>
            </button>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
