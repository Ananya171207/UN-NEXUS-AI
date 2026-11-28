// Live data access for the India vs World module.
// This module deliberately does not fall back to illustrative/sample statistics.

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

async function requestJson(path, signal) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError') throw error;
    throw new Error(`Could not reach the UN NEXUS backend at ${API_BASE_URL}. Make sure FastAPI is running.`);
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    // Keep a useful HTTP error even if a proxy returns non-JSON content.
  }

  if (!response.ok) {
    const detail = payload?.detail ?? payload?.message;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg || JSON.stringify(item)).join('; ')
      : typeof detail === 'string'
        ? detail
        : `The backend returned HTTP ${response.status}.`;
    throw new Error(message);
  }

  return payload;
}

export async function getComparisonCountries({ signal } = {}) {
  const payload = await requestJson('/api/countries', signal);
  if (!Array.isArray(payload)) {
    throw new Error('The countries endpoint returned an unexpected response.');
  }

  return payload
    .map((country) => {
      const id = String(country.id || country.alpha2 || '').toUpperCase();
      const code = String(country.code || country.alpha3 || id).toUpperCase();
      return {
        ...country,
        id,
        code,
        name: country.name || country.countryName || code,
        region: country.region || 'Unknown region',
      };
    })
    .filter((country) => country.id && country.code && country.name);
}

export function getIndicatorCatalogue({ signal } = {}) {
  return requestJson('/api/compare/indicators', signal);
}

export function getCountryComparison(countryCodes, { signal, baseline } = {}) {
  if (!Array.isArray(countryCodes) || countryCodes.length < 2 || countryCodes.length > 5) {
    throw new Error('Select between 2 and 5 countries in total, including India.');
  }

  const params = new URLSearchParams({ countries: countryCodes.join(',') });
  if (baseline) params.set('baseline', baseline);
  return requestJson(`/api/compare?${params.toString()}`, signal);
}
