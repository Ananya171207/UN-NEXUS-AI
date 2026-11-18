import { useState } from 'react';
import { ArrowUpRight, Database, Globe, ListChecks, MapPinned, X } from 'lucide-react';
import Panel from '../../components/common/Panel';
import MetricCard from '../../components/common/MetricCard';
import DataBadge from '../../components/common/DataBadge';
import EmptyState from '../../components/common/EmptyState';
import WorldMap from '../../components/maps/WorldMap';
import TrendChart from '../../components/charts/TrendChart';
import useNow from '../../hooks/useNow';
import { NAV_ITEMS } from '../../data/navigation';
import { sampleEvents, trendSeries, SEVERITY_LEVELS } from '../../data/overviewData';
import { WORLD_VIEW } from '../../data/taxonomy';
import './Overview.css';

function greeting(date) {
  const h = date.getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

export default function Overview({ onNavigate }) {
  const [selectedId, setSelectedId] = useState(null);
  const [seriesId, setSeriesId] = useState(trendSeries[0].id);
  const now = useNow(1000);

  const series = trendSeries.find((s) => s.id === seriesId);
  const selected = sampleEvents.find((e) => e.id === selectedId);
  const modules = NAV_ITEMS.filter((item) => item.id !== 'overview');

  const markers = sampleEvents.map((e) => ({
    id: e.id,
    position: e.position,
    severity: e.severity,
    tooltip: `${e.location} · ${e.severity}`,
  }));
  const view = selected ? { center: selected.position, zoom: 4 } : WORLD_VIEW;

  return (
    <div className="page overview">
      <header className="page-header reveal">
        <div>
          <div className="eyebrow">
            <span className="live-dot" /> {greeting(now)} · Global monitoring platform
          </div>
          <h1>Global Intelligence Overview</h1>
          <p>Development, sustainability and international affairs in one workspace.</p>
        </div>
        <div className="header-meta">
          <div className="clock">
            <strong>{now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</strong>
            <small>{now.toLocaleDateString([], { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</small>
          </div>
          <DataBadge type="sample">Sample data mode</DataBadge>
        </div>
      </header>

      {/* Facts about the framework are stable and well known, so they are tagged as reference. */}
      <section className="metrics-grid" aria-label="Key figures">
        <MetricCard index={1} label="UN member states" value={193} note="Scope of the platform" icon={Globe} badge="reference" />
        <MetricCard index={2} label="Sustainable Development Goals" value={17} note="2030 Agenda" icon={ListChecks} badge="reference" />
        <MetricCard index={3} label="SDG targets" value={169} note="Official framework" icon={MapPinned} badge="reference" />
        <MetricCard index={4} label="Data connection" value="Offline" note="Backend not connected yet" icon={Database} />
      </section>

      <section className="overview-grid">
        <Panel
          index={5}
          title="Global Situation Room"
          subtitle="Placeholder monitoring locations — select a marker or an event"
          actions={<DataBadge type="sample" />}
          flush
          className="map-panel"
        >
          <div className="map-frame">
            <WorldMap markers={markers} view={view} selectedId={selectedId} onSelect={setSelectedId} />
          </div>
          <div className="map-legend" aria-label="Severity legend">
            {SEVERITY_LEVELS.map((level) => (
              <span key={level} className={`severity severity-${level}`}>{level}</span>
            ))}
          </div>
        </Panel>

        <Panel
          index={6}
          title="Event feed"
          subtitle="Illustrative entries, not real events"
          actions={
            selected && (
              <button type="button" className="btn btn-ghost" onClick={() => setSelectedId(null)}>
                <X size={14} /> Clear
              </button>
            )
          }
          flush
          className="feed-panel"
        >
          {sampleEvents.length === 0 ? (
            <EmptyState icon={Globe} title="No events">Events will appear here once a data source is connected.</EmptyState>
          ) : (
            <ul className="event-list">
              {sampleEvents.map((event, i) => (
                <li key={event.id} className="reveal-left" style={{ '--i': i + 7 }}>
                  <button
                    type="button"
                    className={`event-item ${event.id === selectedId ? 'selected' : ''}`}
                    onClick={() => setSelectedId(event.id === selectedId ? null : event.id)}
                    aria-pressed={event.id === selectedId}
                  >
                    <div className="event-top">
                      <span className={`severity severity-${event.severity}`}>{event.severity}</span>
                      <span className="event-category">{event.category}</span>
                    </div>
                    <strong>{event.title}</strong>
                    <small>{event.location} · {event.region}</small>
                    {event.id === selectedId && <p>{event.summary}</p>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </section>

      <section className="overview-grid lower">
        <Panel
          index={8}
          title="Development trend"
          subtitle={`${series.label} (${series.unit})`}
          actions={
            <>
              <DataBadge type="sample" />
              <select
                className="select"
                value={seriesId}
                onChange={(e) => setSeriesId(e.target.value)}
                aria-label="Choose indicator"
              >
                {trendSeries.map((s) => (
                  <option key={s.id} value={s.id}>{s.label}</option>
                ))}
              </select>
            </>
          }
        >
          <TrendChart key={seriesId} data={series.data} unit={series.unit} />
          <p className="chart-note">Illustrative values for interface design. Not official UN statistics.</p>
        </Panel>

        <Panel index={9} title="Platform modules" subtitle="Build status of each workspace" flush>
          <ul className="module-list">
            {modules.map((item, i) => {
              const Icon = item.icon;
              return (
                <li key={item.id} className="reveal-left" style={{ '--i': i + 10 }}>
                  <button type="button" className="module-item" onClick={() => onNavigate(item.id)}>
                    <Icon size={16} />
                    <span>
                      <strong>{item.label}</strong>
                      <small>{item.description}</small>
                    </span>
                    <span className="badge badge-neutral">
                      {item.status === 'available' ? 'Available' : 'In development'}
                    </span>
                    <ArrowUpRight size={14} />
                  </button>
                </li>
              );
            })}
          </ul>
        </Panel>
      </section>

      <footer className="page-footer">
        UN NEXUS AI · Development preview · All figures marked “Sample data” are illustrative
      </footer>
    </div>
  );
}
