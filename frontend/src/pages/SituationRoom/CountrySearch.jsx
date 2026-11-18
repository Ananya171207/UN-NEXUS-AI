import { useCallback, useMemo, useRef, useState } from 'react';
import { Search, X } from 'lucide-react';
import useClickOutside from '../../hooks/useClickOutside';
import { searchCountries } from './utils';

// Type-ahead country search. Arrow keys + Enter work as well as the mouse.
export default function CountrySearch({ countries, onPick }) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const wrapRef = useRef(null);
  const close = useCallback(() => setOpen(false), []);
  useClickOutside(wrapRef, close);

  const results = useMemo(() => searchCountries(countries, query), [countries, query]);
  const showList = open && query.trim() !== '';

  function pick(country) {
    onPick(country.id);
    setQuery('');
    setOpen(false);
  }

  function onKeyDown(event) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (event.key === 'Enter' && results[active]) {
      pick(results[active]);
    } else if (event.key === 'Escape') {
      setOpen(false);
    }
  }

  return (
    <div className="country-search" ref={wrapRef}>
      <div className="search-field">
        <Search size={15} />
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder="Search a country…"
          role="combobox"
          aria-expanded={showList}
          aria-controls="country-results"
          aria-label="Search by country"
        />
        {query && (
          <button type="button" className="icon-btn small" onClick={() => setQuery('')} aria-label="Clear search">
            <X size={14} />
          </button>
        )}
      </div>

      {showList && (
        <div className="popover country-results" id="country-results" role="listbox">
          {results.length === 0 ? (
            <div className="popover-empty">No countries match “{query}”.</div>
          ) : (
            results.map((country, i) => (
              <button
                key={country.id}
                type="button"
                role="option"
                aria-selected={i === active}
                className={`search-result ${i === active ? 'highlight' : ''}`}
                onMouseEnter={() => setActive(i)}
                onClick={() => pick(country)}
              >
                <span>
                  <strong>{country.name}</strong>
                  <small>{country.region}</small>
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
