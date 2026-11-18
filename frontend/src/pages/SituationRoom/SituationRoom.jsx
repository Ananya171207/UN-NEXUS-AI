
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, Flame, Globe, MapPin } from 'lucide-react';
import Panel from '../../components/common/Panel';
import MetricCard from '../../components/common/MetricCard';
import { Skeleton, ErrorState } from '../../components/common/StateViews';
import WorldMap from '../../components/maps/WorldMap';
import useAsync from '../../hooks/useAsync';
import useNow from '../../hooks/useNow';
import {
  getCountries,
  getEvents,
  getCountryProfile,
} from '../../services/situationService';
import { REGION_VIEWS } from '../../data/taxonomy';
import FilterBar from './FilterBar';
import CountryPanel from './CountryPanel';
import EventFeed from './EventFeed';
import RegionalMonitor from './RegionalMonitor';
import Timeline from './Timeline';
import EventModal from './EventModal';
import {
  buildMarkers,
  filterEvents,
  suggestCountries,
  summarizeRegions,
} from './utils';
import './SituationRoom.css';

const NONE = [];

function LoadingView() {
  return (
    <div className="page situation" aria-busy="true" aria-label="Loading Situation Room">
      <Skeleton height={34} width={320} className="mb" />
      <Skeleton height={108} className="mb" />
      <div className="sr-top">
        <Skeleton height={420} />
        <Skeleton height={420} />
      </div>
    </div>
  );
}

export default function SituationRoom() {
  const countriesQuery = useAsync(getCountries);
  const eventsQuery = useAsync(getEvents);
  const now = useNow(60000).getTime();

  const [region, setRegion] = useState('All');
  const [categories, setCategories] = useState(NONE);
  const [minSeverity, setMinSeverity] = useState('low');
  const [selectedId, setSelectedId] = useState(null);
  const [onlySelected, setOnlySelected] = useState(false);
  const [openEventId, setOpenEventId] = useState(null);

  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState(null);

  const countries = countriesQuery.data || NONE;
  const events = eventsQuery.data || NONE;

  const countriesById = useMemo(
    () => Object.fromEntries(countries.map((c) => [c.id, c])),
    [countries]
  );

  // Events under category + severity filters, across every region.
  const eventsAllRegions = useMemo(
    () => filterEvents(events, countriesById, {
      region: 'All',
      categories,
      minSeverity,
    }),
    [events, countriesById, categories, minSeverity]
  );

  const filteredEvents = useMemo(
    () =>
      region === 'All'
        ? eventsAllRegions
        : eventsAllRegions.filter(
            (e) => countriesById[e.countryId]?.region === region
          ),
    [eventsAllRegions, region, countriesById]
  );

  const visibleCountries = useMemo(
    () =>
      region === 'All'
        ? countries
        : countries.filter((c) => c.region === region),
    [countries, region]
  );

  const markers = useMemo(
    () => buildMarkers(visibleCountries, filteredEvents),
    [visibleCountries, filteredEvents]
  );

  const regionSummaries = useMemo(
    () => summarizeRegions(countries, eventsAllRegions, countriesById),
    [countries, eventsAllRegions, countriesById]
  );

  const suggestions = useMemo(
    () => suggestCountries(countries, events),
    [countries, events]
  );

  const selected = selectedId ? countriesById[selectedId] || null : null;
  const selectedCountryCode = selected?.code || selected?.id || null;

  // Fetch a detailed profile only for the currently selected country.
  useEffect(() => {
    let cancelled = false;

    if (!selectedCountryCode) {
      setProfile(null);
      setProfileLoading(false);
      setProfileError(null);
      return;
    }

    setProfile(null);
    setProfileLoading(true);
    setProfileError(null);

    getCountryProfile(selectedCountryCode)
      .then((data) => {
        if (!cancelled) setProfile(data);
      })
      .catch((error) => {
        if (!cancelled) setProfileError(error);
      })
      .finally(() => {
        if (!cancelled) setProfileLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedCountryCode]);

  const selectedEvents = useMemo(
    () =>
      selected
        ? events
            .filter((e) => e.countryId === selected.id)
            .sort(
              (a, b) =>
                new Date(b.occurredAt) - new Date(a.occurredAt)
            )
        : NONE,
    [events, selected]
  );

  const feedEvents =
    onlySelected && selected
      ? filteredEvents.filter((e) => e.countryId === selected.id)
      : filteredEvents;

  const openEvent = openEventId
    ? events.find((e) => e.id === openEventId)
    : null;

  const view = selected
    ? { center: selected.position, zoom: 4 }
    : REGION_VIEWS[region];

  const activeFilters =
    (region !== 'All' ? 1 : 0) +
    categories.length +
    (minSeverity !== 'low' ? 1 : 0);

  const urgentCount = filteredEvents.filter(
    (e) => e.severity === 'high' || e.severity === 'critical'
  ).length;

  const regionsWithEvents = new Set(
    filteredEvents
      .map((e) => countriesById[e.countryId]?.region)
      .filter(Boolean)
  ).size;

  const pickCountry = useCallback(
    (id) => {
      const country = countriesById[id];
      setSelectedId(id);

      // Make sure the chosen country is not hidden by the region filter.
      setRegion((r) =>
        r !== 'All' && country && country.region !== r ? 'All' : r
      );
    },
    [countriesById]
  );

  const handleMapSelect = useCallback(
    (id) => (id ? pickCountry(id) : setSelectedId(null)),
    [pickCountry]
  );

  function changeRegion(next) {
    setRegion(next);

    if (next !== 'All' && selected && selected.region !== next) {
      setSelectedId(null);
      setOnlySelected(false);
    }
  }

  function toggleCategory(id) {
    setCategories((list) =>
      list.includes(id)
        ? list.filter((c) => c !== id)
        : [...list, id]
    );
  }

  function resetFilters() {
    setRegion('All');
    setCategories(NONE);
    setMinSeverity('low');
  }

  function clearSelection() {
    setSelectedId(null);
    setOnlySelected(false);
  }

  const closeModal = useCallback(
    () => setOpenEventId(null),
    []
  );

  if (countriesQuery.loading || eventsQuery.loading) {
    return <LoadingView />;
  }

  if (countriesQuery.error || eventsQuery.error) {
    return (
      <div className="page situation">
        <Panel title="Global Situation Room">
          <ErrorState
            title="Could not load monitoring data"
            message={(countriesQuery.error || eventsQuery.error).message}
            onRetry={() => {
              countriesQuery.reload();
              eventsQuery.reload();
            }}
          />
        </Panel>
      </div>
    );
  }

  return (
    <div className="page situation">
      <header className="page-header reveal">
        <div>
          <div className="eyebrow">Module 1 · Monitoring</div>
          <h1>Global Situation Room</h1>
          <p>
            Monitor countries, regions and events. Select a pin to open a country brief.
          </p>
        </div>
      </header>

      <FilterBar
        countries={countries}
        onPickCountry={pickCountry}
        region={region}
        onRegion={changeRegion}
        categories={categories}
        onToggleCategory={toggleCategory}
        minSeverity={minSeverity}
        onMinSeverity={setMinSeverity}
        activeFilters={activeFilters}
        onReset={resetFilters}
      />

      <section className="sr-stats" aria-label="Summary">
        <MetricCard
          index={2}
          label="Countries in view"
          value={visibleCountries.length}
          note={`of ${countries.length} available`}
          icon={Globe}
        />
        <MetricCard
          index={3}
          label="Events shown"
          value={filteredEvents.length}
          note="after filters"
          icon={Activity}
        />
        <MetricCard
          index={4}
          label="High and critical"
          value={urgentCount}
          note="needing attention"
          icon={Flame}
        />
        <MetricCard
          index={5}
          label="Regions with events"
          value={regionsWithEvents}
          note="of 6 regions"
          icon={MapPin}
        />
      </section>

      <section className="sr-top">
        <Panel
          title="World map"
          subtitle={
            selected
              ? `Focused on ${selected.name}`
              : region === 'All'
                ? 'Global view'
                : region
          }
          className="sr-map-panel"
          index={6}
          flush
        >
          <div className="sr-map-frame">
            <WorldMap
              markers={markers}
              selectedId={selectedId}
              onSelect={handleMapSelect}
              view={view}
            />
          </div>
        </Panel>

        <CountryPanel
          key={selected ? selected.id : 'none'}
          country={selected}
          profile={profile}
          profileLoading={profileLoading}
          profileError={profileError}
          events={selectedEvents}
          suggestions={suggestions}
          onPickCountry={pickCountry}
          onClear={clearSelection}
          onOpenEvent={setOpenEventId}
          now={now}
        />
      </section>

      <section className="sr-middle">
        <EventFeed
          events={feedEvents}
          countriesById={countriesById}
          selectedCountry={selected}
          onlySelected={onlySelected}
          onToggleOnlySelected={() => setOnlySelected((v) => !v)}
          onOpen={setOpenEventId}
          onReset={resetFilters}
          now={now}
        />
        <RegionalMonitor
          summaries={regionSummaries}
          activeRegion={region}
          onSelectRegion={changeRegion}
        />
      </section>

      <Timeline
        events={feedEvents}
        countriesById={countriesById}
        onOpen={setOpenEventId}
        now={now}
      />

      {openEvent && (
        <EventModal
          event={openEvent}
          country={countriesById[openEvent.countryId]}
          now={now}
          onClose={closeModal}
          onViewCountry={(id) => {
            pickCountry(id);
            closeModal();
          }}
        />
      )}
    </div>
  );
}
