
import { apiGet, delay, USE_SAMPLE_DATA } from './api';
import { countries } from '../data/countries';
import { sampleEvents } from '../data/situationEvents';

// Central data access for the Global Situation Room.
// Live API responses are normalized here so the UI receives
// consistent fields without changing the backend.

export async function getCountries() {
  if (!USE_SAMPLE_DATA) {
    const response = await apiGet('/api/countries');

    return response.map((country) => ({
      ...country,
      id: country.id ?? country.code,
      code: country.code ?? country.id,
      name: country.name,
      region: country.region ?? 'Unknown',
      position: country.position ?? null,

      // These are supplied by the country profile endpoint,
      // not necessarily by the country-list endpoint.
      populationM: country.populationM ?? null,
      gdpB: country.gdpB ?? null,
      indicators: country.indicators ?? {},
      isSample: false,
    }));
  }

  await delay(350);
  return countries;
}

export async function getEvents() {
  if (!USE_SAMPLE_DATA) {
    const response = await apiGet('/api/events');

    return response.map((event) => ({
      ...event,
      id: event.id,
      countryId: event.countryId || null,
      category: event.category || 'Other',
      severity: event.severity || 'low',
      title: event.title || 'Untitled event',
      summary: event.summary || '',
      occurredAt: event.occurredAt || null,
      source: event.source || 'Unknown source',
      url: event.url || null,
      isSample: false,
    }));
  }

  await delay(450);
  const now = Date.now();

  return sampleEvents.map((event) => ({
    ...event,
    occurredAt: new Date(now - event.hoursAgo * 3600 * 1000).toISOString(),
    isSample: true,
  }));
}

// Fetch detailed information only when a country is selected.
// Avoids making 197 profile requests when the page loads.
export async function getCountryProfile(countryCode) {
  if (USE_SAMPLE_DATA) return null;
  return apiGet(`/api/countries/${countryCode}/profile`);
}

export const dataMode = USE_SAMPLE_DATA ? 'sample' : 'live';
