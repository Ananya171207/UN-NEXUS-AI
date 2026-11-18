import { Plus, X } from 'lucide-react';
import { MAX_COMPARE, QUICK_SETS } from '../../data/comparisonData';

// Lets the reader choose which countries India is compared with.
export default function CountryPicker({ countries, compareIds, onChange }) {
  const available = countries.filter((c) => c.id !== 'IN' && !compareIds.includes(c.id));
  const full = compareIds.length >= MAX_COMPARE;
  const nameOf = (id) => countries.find((c) => c.id === id)?.name ?? id;

  return (
    <div className="iw-picker">
      <div className="iw-picker-row">
        <span className="section-label">Comparing India with</span>
        <div className="iw-selected" aria-live="polite">
          <span className="iw-tag india">India</span>
          {compareIds.map((id) => (
            <span className="iw-tag" key={id}>
              {nameOf(id)}
              <button type="button" aria-label={`Remove ${nameOf(id)}`} onClick={() => onChange(compareIds.filter((x) => x !== id))}>
                <X size={12} />
              </button>
            </span>
          ))}
          {compareIds.length === 0 && <span className="iw-hint">Add at least one country below.</span>}
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
            onChange={(e) => e.target.value && onChange([...compareIds, e.target.value])}
          >
            <option value="">{full ? `Maximum of ${MAX_COMPARE} reached` : 'Add a country…'}</option>
            {available.map((c) => <option key={c.id} value={c.id}>{c.name} · {c.region}</option>)}
          </select>
        </label>
        <div className="chip-group" role="group" aria-label="Quick selections">
          {QUICK_SETS.map((set) => {
            const active = set.ids.length === compareIds.length && set.ids.every((id) => compareIds.includes(id));
            return (
              <button key={set.id} type="button" className={`chip ${active ? 'active' : ''}`} aria-pressed={active} onClick={() => onChange(set.ids)}>
                {set.label}
              </button>
            );
          })}
          {compareIds.length > 0 && <button type="button" className="chip" onClick={() => onChange([])}>Clear</button>}
        </div>
      </div>
    </div>
  );
}
