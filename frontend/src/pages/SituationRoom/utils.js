import { SEVERITY_RANK, REGIONS, SEVERITY_LEVELS } from '../../data/taxonomy';

// Pure helper functions for the Situation Room.

export function highestSeverity(events) {
  let best = 'none';

  for (const event of events) {
    if ((SEVERITY_RANK[event.severity] ?? 0) > SEVERITY_RANK[best]) {
      best = event.severity;
    }
  }

  return best;
}

// Applies region, category and minimum-severity filters.
// Unmapped events remain visible in the global view.
export function filterEvents(
  events,
  countriesById,
  { region = 'All', categories = [], minSeverity = 'low' }
) {
  const minRank = SEVERITY_RANK[minSeverity] ?? 1;

  return events
    .filter((event) => {
      const country = event.countryId
        ? countriesById[event.countryId]
        : null;

      if (region !== 'All' && (!country || country.region !== region)) {
        return false;
      }

      if (categories.length > 0 && !categories.includes(event.category)) {
        return false;
      }

      return (SEVERITY_RANK[event.severity] ?? 0) >= minRank;
    })
    .sort((a, b) => new Date(b.occurredAt) - new Date(a.occurredAt));
}

// One map marker per visible country.
export function buildMarkers(countries, filteredEvents) {
  return countries.map((country) => {
    const own = filteredEvents.filter(
      (event) => event.countryId === country.id
    );

    const severity = highestSeverity(own);

    const detail =
      own.length === 0
        ? 'no matching events'
        : `${own.length} event${own.length > 1 ? 's' : ''} · ${severity}`;

    return {
      id: country.id,
      position: country.position,
      severity,
      tooltip: `${country.name} · ${detail}`,
    };
  });
}

export function searchCountries(countries, query, limit = 8) {
  const q = query.trim().toLowerCase();

  if (!q) return [];

  return countries
    .filter(
      (country) =>
        country.name.toLowerCase().includes(q) ||
        country.id.toLowerCase() === q ||
        country.region.toLowerCase().includes(q)
    )
    .sort((a, b) => {
      const aStarts = a.name.toLowerCase().startsWith(q) ? 0 : 1;
      const bStarts = b.name.toLowerCase().startsWith(q) ? 0 : 1;

      return aStarts - bStarts || a.name.localeCompare(b.name);
    })
    .slice(0, limit);
}

// Countries with the most severe events.
export function suggestCountries(countries, events, limit = 4) {
  return countries
    .map((country) => ({
      country,
      rank: SEVERITY_RANK[
        highestSeverity(events.filter((event) => event.countryId === country.id))
      ],
    }))
    .sort(
      (a, b) =>
        b.rank - a.rank || a.country.name.localeCompare(b.country.name)
    )
    .slice(0, limit)
    .map((entry) => entry.country);
}

// Event counts per region and severity.
export function summarizeRegions(countries, eventsIgnoringRegion, countriesById) {
  return REGIONS.map((region) => {
    const regionEvents = eventsIgnoringRegion.filter(
      (event) => countriesById[event.countryId]?.region === region
    );

    const bySeverity = Object.fromEntries(
      SEVERITY_LEVELS.map((level) => [level, 0])
    );

    for (const event of regionEvents) {
      if (bySeverity[event.severity] !== undefined) {
        bySeverity[event.severity] += 1;
      }
    }

    return {
      region,
      countryCount: countries.filter((country) => country.region === region).length,
      total: regionEvents.length,
      bySeverity,
      highest: highestSeverity(regionEvents),
    };
  });
}

export function groupByDay(events, dayLabelFn) {
  const groups = [];

  for (const event of events) {
    const label = dayLabelFn(event.occurredAt);
    const last = groups[groups.length - 1];

    if (last && last.label === label) {
      last.events.push(event);
    } else {
      groups.push({ label, events: [event] });
    }
  }

  return groups;
}
