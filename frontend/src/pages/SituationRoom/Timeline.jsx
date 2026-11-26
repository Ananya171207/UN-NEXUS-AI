import { Clock } from 'lucide-react';
import Panel from '../../components/common/Panel';
import EmptyState from '../../components/common/EmptyState';
import { dayLabel, formatTime } from '../../utils/format';
import { groupByDay } from './utils';

export default function Timeline({ events, countriesById, onOpen, now }) {
  const groups = groupByDay(events, (iso) => dayLabel(iso, now));

  return (
    <Panel
      title="Recent developments"
      subtitle="Chronological view of the filtered events"
      className="timeline-panel"
      index={6}
    >
      {groups.length === 0 ? (
        <EmptyState icon={Clock} title="Nothing to show">
          No events match the current filters.
        </EmptyState>
      ) : (
        <div className="timeline">
          {groups.map((group) => (
            <section key={group.label} className="tl-day">
              <h4>{group.label}</h4>

              <ul>
                {group.events.map((event) => (
                  <li key={event.id}>
                    <button
                      type="button"
                      className="tl-item"
                      onClick={() => onOpen(event.id)}
                    >
                      <time dateTime={event.occurredAt}>
                        {formatTime(event.occurredAt)}
                      </time>

                      <span className={`tl-dot bar-${event.severity}`} />

                      <span className="tl-text">
                        <strong>{event.title}</strong>

                        <small>
                          {countriesById[event.countryId]?.name ||
                            event.countryName ||
                            'Global'}
                          {' · '}
                          {event.category}
                          {event.isSample && ' · Sample'}
                        </small>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </Panel>
  );
}
