import { Globe, RotateCcw } from 'lucide-react';
import Panel from '../../components/common/Panel';
import EmptyState from '../../components/common/EmptyState';
import { EVENT_CATEGORIES } from '../../data/taxonomy';
import { formatRelative } from '../../utils/format';

const ICONS = Object.fromEntries(EVENT_CATEGORIES.map((c) => [c.id, c.icon]));

export default function EventFeed({
  events,
  countriesById,
  selectedCountry,
  onlySelected,
  onToggleOnlySelected,
  onOpen,
  onReset,
  now,
}) {
  const hasSampleEvents = events.some((event) => event.isSample);

  return (
    <Panel
      title="Global event feed"
      subtitle={`${events.length} event${events.length === 1 ? '' : 's'} · newest first`}
      className="feed-panel"
      index={4}
      flush
      actions={
        <>
          {hasSampleEvents && (
            <span className="badge badge-sample">Sample data</span>
          )}
          {selectedCountry && (
            <button
              type="button"
              className={`chip ${onlySelected ? 'active' : ''}`}
              aria-pressed={onlySelected}
              onClick={onToggleOnlySelected}
            >
              Only {selectedCountry.name}
            </button>
          )}
        </>
      }
    >
      {events.length === 0 ? (
        <EmptyState icon={Globe} title="No events match these filters">
          Try a different region, category or severity.
          <br />
          <button
            type="button"
            className="btn"
            onClick={onReset}
            style={{ marginTop: 12 }}
          >
            <RotateCcw size={14} /> Reset filters
          </button>
        </EmptyState>
      ) : (
        <ul className="feed-list">
          {events.map((event, i) => {
            const Icon = ICONS[event.category];
            const country = countriesById[event.countryId];

            return (
              <li
                key={event.id}
                className="reveal-left"
                style={{ '--i': Math.min(i, 8) + 5 }}
              >
                <button
                  type="button"
                  className="feed-item"
                  onClick={() => onOpen(event.id)}
                >
                  <span className={`feed-bar bar-${event.severity}`} />

                  <div className="feed-main">
                    <div className="feed-top">
                      <span className={`severity severity-${event.severity}`}>
                        {event.severity}
                      </span>

                      <span className="feed-category">
                        {Icon && <Icon size={12} />} {event.category}
                      </span>

                      {event.isSample && (
                        <span className="badge badge-sample">Sample</span>
                      )}
                    </div>

                    <strong>{event.title}</strong>

                    <small>
                      {country?.name || event.countryName || 'Global'}
                      {' · '}
                      {country?.region || event.region || 'Unknown region'}
                      {' · '}
                      {formatRelative(event.occurredAt, now)}
                    </small>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}
