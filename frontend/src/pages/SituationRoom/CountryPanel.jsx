
import { useState } from 'react';
import { MapPin, X } from 'lucide-react';
import Panel from '../../components/common/Panel';
import Tabs from '../../components/common/Tabs';
import Accordion from '../../components/common/Accordion';
import CopyButton from '../../components/common/CopyButton';
import EmptyState from '../../components/common/EmptyState';
import { formatRelative } from '../../utils/format';

const GROUPS = [
  { id: 'economic', label: 'Economic indicators' },
  { id: 'social', label: 'Social indicators' },
  { id: 'environmental', label: 'Environmental indicators' },
];

const SDG_PROXIES = [
  { goal: 1, name: 'No Poverty', metric: 'Poverty headcount', key: 'poverty_rate' },
  { goal: 2, name: 'Zero Hunger', metric: 'Undernourishment', key: 'undernourishment' },
  { goal: 3, name: 'Good Health and Well-being', metric: 'Life expectancy', key: 'life_expectancy' },
  { goal: 4, name: 'Quality Education', metric: 'Secondary school enrollment', key: 'school_enrollment' },
  { goal: 6, name: 'Clean Water and Sanitation', metric: 'Safely managed drinking water', key: 'drinking_water' },
  { goal: 7, name: 'Affordable and Clean Energy', metric: 'Renewable electricity', key: 'renewable_electricity' },
  { goal: 9, name: 'Industry, Innovation and Infrastructure', metric: 'Internet use', key: 'internet_use' },
  { goal: 11, name: 'Sustainable Cities and Communities', metric: 'PM2.5 air pollution', key: 'pm25' },
  { goal: 13, name: 'Climate Action', metric: 'CO₂ emissions per capita', key: 'co2_emissions' },
  { goal: 15, name: 'Life on Land', metric: 'Forest area', key: 'forest_area' },
];

function formatValue(indicator, key) {
  if (!indicator || indicator.value === null || indicator.value === undefined) {
    return 'Unavailable';
  }

  const value = Number(indicator.value);
  if (!Number.isFinite(value)) return 'Unavailable';

  if (key === 'population') {
    return new Intl.NumberFormat('en-US', {
      notation: 'compact',
      maximumFractionDigits: 2,
    }).format(value);
  }

  if (key === 'gdp') {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      notation: 'compact',
      maximumFractionDigits: 2,
    }).format(value);
  }

  if (key === 'gdp_per_capita') {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value);
  }

  const formatted = new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 2,
  }).format(value);

  if (indicator.unit?.includes('%')) return `${formatted}%`;
  if (indicator.unit?.includes('years')) return `${formatted} years`;

  return `${formatted} ${indicator.unit || ''}`.trim();
}

function IndicatorRow({ indicator, indicatorKey }) {
  if (!indicator) return null;

  return (
    <li>
      <div className="indicator-top">
        <span>{indicator.label || indicatorKey.replaceAll('_', ' ')}</span>
        <strong>{formatValue(indicator, indicatorKey)}</strong>
      </div>
      <small>
        {indicator.year ? `Year: ${indicator.year}` : 'Year unavailable'}
        {indicator.stale ? ' · Cached data' : ''}
      </small>
    </li>
  );
}

function Profile({ profile, profileLoading, profileError }) {
  if (profileLoading) {
    return <p className="fine-print">Loading live country indicators...</p>;
  }

  if (profileError) {
    return (
      <p className="fine-print">
        Could not load this country's profile. Please try selecting the country again.
      </p>
    );
  }

  if (!profile?.indicators) {
    return <p className="fine-print">Country profile data is not currently available.</p>;
  }

  const identity = profile.identity || {};
  const indicators = profile.indicators;

  return (
    <>
      <dl className="facts">
        <div>
          <dt>Region</dt>
          <dd>{identity.region || 'Unavailable'}</dd>
        </div>
        <div>
          <dt>Capital</dt>
          <dd>{identity.capital || 'Unavailable'}</dd>
        </div>
        <div>
          <dt>Population</dt>
          <dd>{formatValue(indicators.population, 'population')}</dd>
        </div>
        <div>
          <dt>GDP per capita</dt>
          <dd>{formatValue(indicators.gdp_per_capita, 'gdp_per_capita')}</dd>
        </div>
      </dl>

      {GROUPS.map((group) => {
        const keys = profile.groups?.[group.id] || Object.keys(indicators).filter(
          (key) => indicators[key]?.group === group.id
        );

        return (
          <section key={group.id}>
            <h4 className="section-label">{group.label}</h4>
            <ul className="indicator-list">
              {keys.map((key) => (
                <IndicatorRow
                  key={key}
                  indicator={indicators[key]}
                  indicatorKey={key}
                />
              ))}
            </ul>
          </section>
        );
      })}

      <p className="fine-print">
        Indicator values are shown with their respective reporting years.
        Some indicators may refer to different years because of source availability.
      </p>
    </>
  );
}

function SdgList({ profile }) {
  const indicators = profile?.indicators || {};

  const available = SDG_PROXIES.filter(
    (item) => indicators[item.key]?.value !== null &&
      indicators[item.key]?.value !== undefined
  );

  if (available.length === 0) {
    return <p className="fine-print">No SDG-related proxy indicators are currently available.</p>;
  }

  return (
    <>
      <ul className="sdg-rows">
        {available.map((item) => {
          const indicator = indicators[item.key];

          return (
            <li key={item.goal}>
              <span className="sdg-chip">SDG {item.goal}</span>
              <div>
                <strong>{item.name}</strong>
                <small>
                  {item.metric}: {formatValue(indicator, item.key)}
                  {indicator.year ? ` · ${indicator.year}` : ''}
                </small>
              </div>
            </li>
          );
        })}
      </ul>

      <p className="fine-print">
        These are real World Bank indicators mapped to related Sustainable
        Development Goals. They are proxy indicators, not official UN SDG
        scores, rankings or progress assessments. Not all 17 goals are
        represented here.
      </p>
    </>
  );
}

function CountryEvents({ events, now, onOpenEvent }) {
  if (!events.length) {
    return (
      <EmptyState title="No recent events">
        No events are currently available for this country.
      </EmptyState>
    );
  }

  return (
    <ul className="mini-events">
      {events.map((event) => (
        <li key={event.id}>
          <button type="button" onClick={() => onOpenEvent(event.id)}>
            <span className={`severity severity-${event.severity}`}>
              {event.severity}
            </span>
            <strong>{event.title}</strong>
            <small>
              {event.category} · {formatRelative(event.occurredAt, now)}
            </small>
          </button>
        </li>
      ))}
    </ul>
  );
}

function buildLiveCountryBrief(country, profile, events) {
  const identity = profile?.identity || {};
  const indicators = profile?.indicators || {};

  const lines = [
    `COUNTRY BRIEF: ${identity.name || country.name}`,
    `Region: ${identity.region || country.region || 'Unavailable'}`,
    `Capital: ${identity.capital || 'Unavailable'}`,
    '',
    'ECONOMIC INDICATORS',
  ];

  for (const key of profile?.groups?.economic || []) {
    const item = indicators[key];
    if (item) {
      lines.push(
        `${item.label}: ${formatValue(item, key)} (${item.year || 'Year unavailable'})`
      );
    }
  }

  lines.push('', 'SOCIAL INDICATORS');

  for (const key of profile?.groups?.social || []) {
    const item = indicators[key];
    if (item) {
      lines.push(
        `${item.label}: ${formatValue(item, key)} (${item.year || 'Year unavailable'})`
      );
    }
  }

  lines.push('', 'ENVIRONMENTAL INDICATORS');

  for (const key of profile?.groups?.environmental || []) {
    const item = indicators[key];
    if (item) {
      lines.push(
        `${item.label}: ${formatValue(item, key)} (${item.year || 'Year unavailable'})`
      );
    }
  }

  lines.push('', `RECENT EVENTS: ${events.length}`);

  events.slice(0, 5).forEach((event) => {
    lines.push(`- ${event.title}`);
  });

  lines.push('', `Indicator source: ${profile?.source || 'Unavailable'}`);

  return lines.join('\n');
}

export default function CountryPanel({
  country,
  events = [],
  suggestions = [],
  onPickCountry,
  onClear,
  onOpenEvent,
  now,
  profile,
  profileLoading = false,
  profileError = null,
}) {
  const [tab, setTab] = useState('profile');

  if (!country) {
    return (
      <Panel
        title="Country information"
        subtitle="Select a pin on the map or search above"
        className="country-panel"
        index={3}
      >
        <EmptyState icon={MapPin} title="No country selected">
          Choose a country to see its live profile, development indicators,
          SDG-related signals and recent events.
        </EmptyState>

        {suggestions.length > 0 && (
          <div className="quick-picks">
            <h4 className="section-label">Most active right now</h4>
            {suggestions.map((c) => (
              <button
                key={c.id}
                type="button"
                className="btn"
                onClick={() => onPickCountry(c.id)}
              >
                {c.name}
              </button>
            ))}
          </div>
        )}
      </Panel>
    );
  }

  const countryName = profile?.identity?.name || country.name;
  const countryRegion = profile?.identity?.region || country.region;

  const tabs = [
    { id: 'profile', label: 'Profile' },
    { id: 'sdg', label: 'SDG signals' },
    { id: 'events', label: 'Events', count: events.length },
  ];

  return (
    <Panel
      title={countryName}
      subtitle={countryRegion}
      className="country-panel"
      index={3}
      actions={
        <button
          type="button"
          className="icon-btn"
          onClick={onClear}
          aria-label="Clear selected country"
        >
          <X size={16} />
        </button>
      }
    >
      <Tabs tabs={tabs} active={tab} onChange={setTab} label="Country sections" />

      <div className="tab-panel" key={tab}>
        {tab === 'profile' && (
          <Profile
            profile={profile}
            profileLoading={profileLoading}
            profileError={profileError}
          />
        )}

        {tab === 'sdg' && <SdgList profile={profile} />}

        {tab === 'events' && (
          <CountryEvents
            events={events}
            now={now}
            onOpenEvent={onOpenEvent}
          />
        )}
      </div>

      <div className="country-footer">
        <CopyButton
          text={buildLiveCountryBrief(country, profile, events)}
          label="Copy brief"
        />
      </div>

      <Accordion title="Source information">
        <ul className="source-list">
          <li>
            <strong>Country metadata:</strong> REST Countries
          </li>
          <li>
            <strong>Development indicators:</strong>{' '}
            {profile?.source || 'World Bank Open Data'}
          </li>
          <li>
            <strong>Indicator reporting:</strong> Each indicator displays
            its own reporting year and source metadata.
          </li>
          <li>
            <strong>Events:</strong> Retrieved through the Situation Room
            events API.
          </li>
        </ul>
      </Accordion>
    </Panel>
  );
}
