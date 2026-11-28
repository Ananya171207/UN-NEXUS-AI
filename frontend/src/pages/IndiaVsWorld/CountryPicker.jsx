import { Plus, X } from 'lucide-react';
import { MAX_COMPARE, QUICK_SETS } from '../../data/comparisonData';

// India is the fixed baseline; compareIds contains the other selected countries.
export default function CountryPicker({ countries, compareIds, onChange }) {
  const available = countries.filter(
    (country) => country.id !== 'IN' && !compareIds.includes(country.id)
  );
  const full = compareIds.length >= MAX_COMPARE;
  const nameOf = (id) => countries.find((country) => country.id === id)?.name ?? id;

  return (
    <div className="iw-picker">
      <div className="iw-picker-row">
        <span className="section-label">Comparing India with</span>
        <div className="iw-selected" aria-live="polite">
          <span className="iw-tag india">India</span>
          {compareIds.map((id) => (
            <span className="iw-tag" key={id}>
              {nameOf(id)}
              <button
                type="button"
                aria-label={`Remove ${nameOf(id)}`}
                onClick={() => onChange(compareIds.filter((item) => item !== id))}
              >
                <X size={12} />
              </button>
            </span>
          ))}
          {compareIds.length === 0 && (
            <span className="iw-hint">Add at least one country below.</span>
          )}
        </div>
      </div>

      <div className="iw-picker-row">
        <label className="iw-add">
          <Plus size={14} />
          <select
            className="select"
            value=""
            disabled={full || available.length === 0}
            aria-label="Add a country to compare"
            onChange={(event) => {
              if (event.target.value) onChange([...compareIds, event.target.value]);
            }}
          >
            <option value="">
              {full ? `Maximum of ${MAX_COMPARE} additional countries reached` : 'Add a country…'}
            </option>
            {available.map((country) => (
              <option key={country.id} value={country.id}>
                {country.name} · {country.region}
              </option>
            ))}
          </select>
        </label>

        <div className="chip-group" role="group" aria-label="Quick selections">
          {QUICK_SETS.map((set) => {
            const ids = set.ids.slice(0, MAX_COMPARE);
            const active = ids.length === compareIds.length && ids.every((id) => compareIds.includes(id));
            return (
              <button
                key={set.id}
                type="button"
                className={`chip ${active ? 'active' : ''}`}
                aria-pressed={active}
                onClick={() => onChange(ids.filter((id) => countries.some((country) => country.id === id)))}
              >
                {set.label}
              </button>
            );
          })}
          {compareIds.length > 0 && (
            <button type="button" className="chip" onClick={() => onChange([])}>
              Clear
            </button>
          )}
        </div>
      </div>
      <p className="fine-print">Select up to four countries in addition to India (five countries total).</p>
    </div>
  );
}
