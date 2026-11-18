import { useCallback, useEffect, useRef, useState } from 'react';
import { Bell, Menu, Search } from 'lucide-react';
import { ALL_PAGES } from '../../data/navigation';
import useClickOutside from '../../hooks/useClickOutside';

// Search over the platform's modules. When the backend exists this can be
// extended to search countries, indicators and documents.
function searchModules(query) {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  return ALL_PAGES.filter(
    (page) =>
      page.label.toLowerCase().includes(q) ||
      page.description.toLowerCase().includes(q) ||
      page.keywords.some((k) => k.includes(q))
  );
}

function GlobalSearch({ onNavigate }) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);
  const inputRef = useRef(null);
  const results = searchModules(query);

  const close = useCallback(() => setOpen(false), []);
  useClickOutside(wrapRef, close);

  // Ctrl+K / Cmd+K focuses the search box
  useEffect(() => {
    function onKey(event) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  function choose(page) {
    onNavigate(page.id);
    setQuery('');
    setOpen(false);
    inputRef.current?.blur();
  }

  function onKeyDown(event) {
    if (event.key === 'Enter' && results.length > 0) choose(results[0]);
    if (event.key === 'Escape') {
      setQuery('');
      setOpen(false);
      inputRef.current?.blur();
    }
  }

  return (
    <div className="search-wrap" ref={wrapRef}>
      <div className="search-box" onClick={() => inputRef.current?.focus()}>
        <Search size={15} />
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder="Search modules…"
          aria-label="Search modules"
        />
        <kbd>Ctrl K</kbd>
      </div>

      {open && query.trim() !== '' && (
        <div className="popover search-results" role="listbox">
          {results.length === 0 ? (
            <div className="popover-empty">No modules match “{query}”.</div>
          ) : (
            results.map((page) => {
              const Icon = page.icon;
              return (
                <button key={page.id} type="button" className="search-result" onClick={() => choose(page)}>
                  <Icon size={15} />
                  <span>
                    <strong>{page.label}</strong>
                    <small>{page.description}</small>
                  </span>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

function NotificationsButton() {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);
  const close = useCallback(() => setOpen(false), []);
  useClickOutside(wrapRef, close);

  return (
    <div className="popover-wrap" ref={wrapRef}>
      <button
        type="button"
        className="icon-btn"
        onClick={() => setOpen((v) => !v)}
        aria-label="Notifications"
        aria-expanded={open}
      >
        <Bell size={17} />
      </button>
      {open && (
        <div className="popover notifications">
          <div className="popover-title">Notifications</div>
          <div className="popover-empty">
            <strong>No notifications</strong>
            <p>Live alerts need the backend service, which is not connected yet.</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Topbar({ activeLabel, onMenu, onNavigate }) {
  return (
    <header className="topbar">
      <button type="button" className="icon-btn mobile-only" onClick={onMenu} aria-label="Open navigation">
        <Menu size={20} />
      </button>

      <div className="breadcrumb">
        <span>Workspace</span>
        <span aria-hidden="true">/</span>
        <strong>{activeLabel}</strong>
      </div>

      <div className="topbar-actions">
        <GlobalSearch onNavigate={onNavigate} />
        <NotificationsButton />
        <button
          type="button"
          className="avatar"
          onClick={() => onNavigate('settings')}
          aria-label="Open settings"
          title="Settings"
        >
          UN
        </button>
      </div>
    </header>
  );
}
