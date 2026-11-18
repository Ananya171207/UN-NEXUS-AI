// =====================================================================
// SAMPLE DATA — NOT OFFICIAL STATISTICS
// The extra indicators below were entered by hand as rounded, illustrative
// approximations (like data/countries.js). They are NOT from the World Bank,
// the UN or any other official source and must not be quoted. The backend
// will replace them with real datasets.
//
// Order of the numbers in each row, matching `countries.js`:
//   co2 = CO2 emissions per person (tonnes)   urban = urban population (%)
//   u5mr = deaths under age 5 per 1,000 births   electricity = access (%)
// =====================================================================

export const COMPARISON_DATA_NOTE =
  'Rounded, illustrative figures for 24 sample countries. Not official statistics.';

export const EXTRA_INDICATORS = {
  IN: { co2: 2.0, urban: 36, u5mr: 30, electricity: 99 },
  CN: { co2: 8.0, urban: 65, u5mr: 6, electricity: 100 },
  JP: { co2: 8.0, urban: 92, u5mr: 2, electricity: 100 },
  ID: { co2: 2.5, urban: 58, u5mr: 21, electricity: 99 },
  BD: { co2: 0.6, urban: 40, u5mr: 27, electricity: 99 },
  SA: { co2: 16, urban: 85, u5mr: 6, electricity: 100 },
  DE: { co2: 7.5, urban: 77, u5mr: 4, electricity: 100 },
  GB: { co2: 4.5, urban: 84, u5mr: 4, electricity: 100 },
  FR: { co2: 4.3, urban: 82, u5mr: 4, electricity: 100 },
  SE: { co2: 3.5, urban: 88, u5mr: 3, electricity: 100 },
  NG: { co2: 0.6, urban: 54, u5mr: 105, electricity: 61 },
  EG: { co2: 2.4, urban: 43, u5mr: 19, electricity: 100 },
  KE: { co2: 0.4, urban: 30, u5mr: 40, electricity: 76 },
  ZA: { co2: 6.8, urban: 68, u5mr: 32, electricity: 85 },
  ET: { co2: 0.15, urban: 23, u5mr: 47, electricity: 55 },
  US: { co2: 14, urban: 83, u5mr: 6, electricity: 100 },
  CA: { co2: 14, urban: 82, u5mr: 5, electricity: 100 },
  MX: { co2: 3.5, urban: 81, u5mr: 13, electricity: 100 },
  BR: { co2: 2.2, urban: 87, u5mr: 14, electricity: 100 },
  AR: { co2: 3.8, urban: 92, u5mr: 9, electricity: 100 },
  CO: { co2: 1.7, urban: 82, u5mr: 12, electricity: 99 },
  CL: { co2: 4.2, urban: 88, u5mr: 6, electricity: 100 },
  AU: { co2: 15, urban: 86, u5mr: 4, electricity: 100 },
  NZ: { co2: 6, urban: 87, u5mr: 5, electricity: 100 },
};

// better: which direction is "good". 'neutral' means size, not quality.
// value(country) reads the number; decimals controls rounding in the table.
export const INDICATORS = [
  { id: 'gdp', label: 'Economy size (GDP)', short: 'GDP', unit: 'US$ billion', group: 'Economy', better: 'neutral', get: (c) => c.gdpB, format: 'gdp' },
  { id: 'gdpPc', label: 'GDP per person', short: 'GDP/person', unit: 'US$', group: 'Economy', better: 'higher', get: (c) => Math.round((c.gdpB * 1e9) / (c.populationM * 1e6)), format: 'usd' },
  { id: 'population', label: 'Population', short: 'Population', unit: 'million', group: 'People & health', better: 'neutral', get: (c) => c.populationM, format: 'pop' },
  { id: 'lifeExpectancy', label: 'Life expectancy', short: 'Life exp.', unit: 'years', group: 'People & health', better: 'higher', get: (c) => c.indicators.lifeExpectancy, format: 'plain' },
  { id: 'u5mr', label: 'Child deaths (under 5, per 1,000 births)', short: 'Under-5 deaths', unit: 'per 1,000', group: 'People & health', better: 'lower', get: (c) => EXTRA_INDICATORS[c.id].u5mr, format: 'plain' },
  { id: 'urban', label: 'Urban population', short: 'Urban', unit: '%', group: 'People & health', better: 'neutral', get: (c) => EXTRA_INDICATORS[c.id].urban, format: 'pct' },
  { id: 'renewable', label: 'Renewable share of electricity', short: 'Renewables', unit: '%', group: 'Energy & environment', better: 'higher', get: (c) => c.indicators.renewableShare, format: 'pct' },
  { id: 'co2', label: 'CO2 emissions per person', short: 'CO2/person', unit: 'tonnes', group: 'Energy & environment', better: 'lower', get: (c) => EXTRA_INDICATORS[c.id].co2, format: 'plain' },
  { id: 'electricity', label: 'Access to electricity', short: 'Electricity', unit: '%', group: 'Access & connectivity', better: 'higher', get: (c) => EXTRA_INDICATORS[c.id].electricity, format: 'pct' },
  { id: 'internet', label: 'Internet use', short: 'Internet', unit: '%', group: 'Access & connectivity', better: 'higher', get: (c) => c.indicators.internetUse, format: 'pct' },
];

export const INDICATOR_GROUPS = ['Economy', 'People & health', 'Energy & environment', 'Access & connectivity'];

// Ready-made sets of comparison countries (ids from countries.js).
export const QUICK_SETS = [
  { id: 'large', label: 'Largest economies', ids: ['US', 'CN', 'DE', 'JP'] },
  { id: 'asia', label: 'Asian peers', ids: ['CN', 'ID', 'BD', 'JP'] },
  { id: 'emerging', label: 'Emerging economies', ids: ['CN', 'BR', 'ZA', 'ID'] },
  { id: 'africa', label: 'African countries', ids: ['NG', 'EG', 'KE', 'ET'] },
];

export const DEFAULT_COMPARE = ['CN', 'US', 'BR'];
export const MAX_COMPARE = 5;
