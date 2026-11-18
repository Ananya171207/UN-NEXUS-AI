import { formatGdp, formatPopulation, formatUsd } from '../../utils/format';
import { INDICATORS } from '../../data/comparisonData';

export function formatValue(indicator, value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  switch (indicator.format) {
    case 'gdp': return formatGdp(value);
    case 'pop': return formatPopulation(value);
    case 'usd': return formatUsd(value);
    case 'pct': return `${value}%`;
    default: return String(value);
  }
}

export function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function medianOf(indicator, countries) {
  return median(countries.map(indicator.get));
}

// Rank 1 = best (or largest, for "neutral" indicators).
export function rankOf(indicator, countries, countryId) {
  const ordered = [...countries].sort((a, b) => (indicator.better === 'lower' ? indicator.get(a) - indicator.get(b) : indicator.get(b) - indicator.get(a)));
  return ordered.findIndex((c) => c.id === countryId) + 1;
}

// 0 to 100: where the country sits between the weakest and strongest sample country.
// Indicators where lower is better are flipped; GDP per person uses a log scale.
export function profileScore(indicator, countries, country) {
  const scale = indicator.id === 'gdpPc' ? (v) => Math.log(v) : (v) => v;
  const values = countries.map((c) => scale(indicator.get(c)));
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (max === min) return 50;
  const raw = ((scale(indicator.get(country)) - min) / (max - min)) * 100;
  return Math.round(indicator.better === 'lower' ? 100 - raw : raw);
}

export const PROFILE_INDICATORS = INDICATORS.filter((i) => i.better !== 'neutral');

// Compare a value with India's: 'better' | 'worse' | 'same' | 'neutral'
export function versusIndia(indicator, value, indiaValue) {
  if (indicator.better === 'neutral') return 'neutral';
  if (value === indiaValue) return 'same';
  const higher = value > indiaValue;
  return (indicator.better === 'higher') === higher ? 'better' : 'worse';
}

// Plain-language statements computed from the data, never invented.
export function buildInsights(countries, india) {
  const rows = PROFILE_INDICATORS.map((indicator) => {
    const rank = rankOf(indicator, countries, india.id);
    return { indicator, rank, med: medianOf(indicator, countries), value: indicator.get(india) };
  });
  const total = countries.length;
  const strengths = rows.filter((r) => r.rank <= Math.ceil(total / 3)).sort((a, b) => a.rank - b.rank);
  const gaps = rows.filter((r) => r.rank > Math.floor((total * 2) / 3)).sort((a, b) => b.rank - a.rank);
  return { strengths, gaps, total };
}
