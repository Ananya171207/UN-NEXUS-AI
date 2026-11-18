
import { SEVERITY_RANK, REGIONS, SEVERITY_LEVELS } from '../../data/taxonomy';
import { formatGdp, formatPopulation, formatUsd, gdpPerCapita } from '../../utils/format';

// Pure helper functions for the Situation Room (no React inside, easy to test).

export function highestSeverity(events) {
  let best = 'none';
  for (const event of events) {
    if ((SEVERITY_RANK[event.severity] ?? 0) > SEVERITY_RANK[best]) {
      best = event.severity;
    }
  }
  return best;
}

// Applies region, category and minimum-severity filters. Newest first.
// Unmapped events remain visible in the global view but are not assigned
// to an invented region or country.
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

      // A regional view requires a genuine country-to-region mapping.
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

// One map marker per visible country, coloured by its most severe matching event.
export function buildMarkers(countries, filteredEvents) {
  return countries.map((country) => {
    const own = filteredEvents.filter((event) => event.countryId === country.id);
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
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.id.toLowerCase() === q ||
        c.region.toLowerCase().includes(q)
    )
    .sort((a, b) => {
      const aStarts = a.name.toLowerCase().startsWith(q) ? 0 : 1;
      const bStarts = b.name.toLowerCase().startsWith(q) ? 0 : 1;
      return aStarts - bStarts || a.name.localeCompare(b.name);
    })
    .slice(0, limit);
}

// Countries with the most severe events, used as quick picks in the empty panel.
export function suggestCountries(countries, events, limit = 4) {
  return countries
    .map((country) => ({
      country,
      rank: SEVERITY_RANK[
        highestSeverity(events.filter((e) => e.countryId === country.id))
      ],
    }))
    .sort(
      (a, b) =>
        b.rank - a.rank || a.country.name.localeCompare(b.country.name)
    )
    .slice(0, limit)
    .map((entry) => entry.country);
}

// Event counts per region and severity (ignores the region filter on purpose).
export function summarizeRegions(countries, eventsIgnoringRegion, countriesById) {
  return REGIONS.map((region) => {
    const regionEvents = eventsIgnoringRegion.filter(
      (e) => countriesById[e.countryId]?.region === region
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
      countryCount: countries.filter((c) => c.region === region).length,
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

// Demonstration thresholds only. These are NOT UN assessments of progress.
const BANDS = {
  strong: { tone: 'good', label: 'On track (demo)' },
  moderate: { tone: 'mid', label: 'Moderate progress (demo)' },
  weak: { tone: 'low', label: 'Needs attention (demo)' },
};

function band(value, strongFrom, moderateFrom) {
  if (value >= strongFrom) return BANDS.strong;
  if (value >= moderateFrom) return BANDS.moderate;
  return BANDS.weak;
}

export function deriveSdgIndicators(country) {
  const { lifeExpectancy, renewableShare, internetUse } = country.indicators;

  return [
    {
      goal: 3,
      name: 'Good Health and Well-being',
      metric: 'Life expectancy',
      value: `${lifeExpectancy} years`,
      ...band(lifeExpectancy, 78, 68),
    },
    {
      goal: 7,
      name: 'Affordable and Clean Energy',
      metric: 'Renewable share of electricity',
      value: `${renewableShare}%`,
      ...band(renewableShare, 50, 20),
    },
    {
      goal: 9,
      name: 'Industry, Innovation and Infrastructure',
      metric: 'Internet use',
      value: `${internetUse}%`,
      ...band(internetUse, 80, 50),
    },
  ];
}

export function buildCountryBrief(country, events) {
  const lines = [
    `${country.name} (${country.region}) — UN NEXUS AI country brief`,
    'DATA TYPE: SAMPLE DATA — rounded approximations, not official statistics.',
    `Population: ${formatPopulation(country.populationM)}`,
    `GDP: ${formatGdp(country.gdpB)}`,
    `GDP per capita: ${formatUsd(gdpPerCapita(country))}`,
    `Life expectancy: ${country.indicators.lifeExpectancy} years`,
    `Renewable share of electricity: ${country.indicators.renewableShare}%`,
    `Internet use: ${country.indicators.internetUse}%`,
  ];

  if (events.length > 0) {
    lines.push('Recent events (demonstration entries):');
    for (const event of events) {
      lines.push(`- [${event.severity}] ${event.category}: ${event.title}`);
    }
  }

  return lines.join('\n');
}
