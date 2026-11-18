// Simple tab strip. The parent keeps `active` in its own state and shows
// the matching content below.
export default function Tabs({ tabs, active, onChange, label = 'Sections' }) {
  function onKeyDown(event) {
    const index = tabs.findIndex((t) => t.id === active);
    if (event.key === 'ArrowRight') onChange(tabs[(index + 1) % tabs.length].id);
    if (event.key === 'ArrowLeft') onChange(tabs[(index - 1 + tabs.length) % tabs.length].id);
  }

  return (
    <div className="tabs" role="tablist" aria-label={label} onKeyDown={onKeyDown}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={tab.id === active}
          tabIndex={tab.id === active ? 0 : -1}
          className={`tab ${tab.id === active ? 'active' : ''}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
          {tab.count !== undefined && <span className="tab-count">{tab.count}</span>}
        </button>
      ))}
    </div>
  );
}
