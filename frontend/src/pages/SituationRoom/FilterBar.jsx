import { RotateCcw } from 'lucide-react';
import CountrySearch from './CountrySearch';
import { EVENT_CATEGORIES, REGIONS, SEVERITY_LEVELS } from '../../data/taxonomy';

const SEVERITY_OPTIONS = [
  { value: 'low', label: 'All severities' },
  { value: 'moderate', label: 'Moderate and above' },
  { value: 'high', label: 'High and above' },
  { value: 'critical', label: 'Critical only' },
];

export default function FilterBar({
  countries,
  onPickCountry,
  region,
  onRegion,
  categories,
  onToggleCategory,
  minSeverity,
  onMinSeverity,
  activeFilters,
  onReset,
}) {
  return (
    <div className="panel filterbar reveal" style={{ '--i': 1 }}>
      <div className="filter-row">
        <CountrySearch countries={countries} onPick={onPickCountry} />

        <div className="chip-group" role="group" aria-label="Region">
          {['All', ...REGIONS].map((name) => (
            <button
              key={name}
              type="button"
              className={`chip ${region === name ? 'active' : ''}`}
              aria-pressed={region === name}
              onClick={() => onRegion(name)}
            >
              {name === 'All' ? 'All regions' : name}
            </button>
          ))}
        </div>
      </div>

      <div className="filter-row">
        <div className="chip-group" role="group" aria-label="Event category">
          {EVENT_CATEGORIES.map(({ id, icon: Icon }) => (
            <button
              key={id}
              type="button"
              className={`chip ${categories.includes(id) ? 'active' : ''}`}
              aria-pressed={categories.includes(id)}
              onClick={() => onToggleCategory(id)}
            >
              <Icon size={13} /> {id}
            </button>
          ))}
        </div>

        <div className="filter-actions">
          <select
            className="select"
            value={minSeverity}
            onChange={(e) => onMinSeverity(e.target.value)}
            aria-label="Minimum severity"
          >
            {SEVERITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <button type="button" className="btn btn-ghost" onClick={onReset} disabled={activeFilters === 0}>
            <RotateCcw size={13} /> Reset{activeFilters > 0 ? ` (${activeFilters})` : ''}
          </button>
        </div>
      </div>

      <div className="severity-key" aria-label="Severity key">
        {SEVERITY_LEVELS.map((level) => (
          <span key={level} className={`severity severity-${level}`}>{level}</span>
        ))}
        <span className="severity-note">Pin colour = most severe matching event</span>
      </div>
    </div>
  );
}
