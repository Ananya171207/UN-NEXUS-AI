// =====================================================================
// SAMPLE DATA — NOT OFFICIAL STATISTICS
// Figures below are rounded approximations entered by hand so the
// interface can be designed and tested. They are NOT taken from the
// World Bank, the UN or any other official source, and must not be
// quoted. The backend will replace this file with real datasets.
//
// populationM = population in millions
// gdpB        = GDP in billions of US dollars
// indicators  = illustrative values (life expectancy in years;
//               renewable share of electricity and internet use in %)
// =====================================================================

export const COUNTRY_DATA_NOTE =
  'Rounded approximations for interface design. Not official statistics.';

const c = (id, name, region, position, populationM, gdpB, lifeExpectancy, renewableShare, internetUse) => ({
  id,
  name,
  region,
  position,
  populationM,
  gdpB,
  indicators: { lifeExpectancy, renewableShare, internetUse },
});

export const countries = [
  // Asia
  c('IN', 'India', 'Asia', [20.59, 78.96], 1428, 3550, 68, 21, 46),
  c('CN', 'China', 'Asia', [35.86, 104.2], 1410, 17800, 78, 31, 76),
  c('JP', 'Japan', 'Asia', [36.2, 138.25], 124, 4210, 84, 22, 85),
  c('ID', 'Indonesia', 'Asia', [-0.79, 113.92], 277, 1370, 68, 19, 66),
  c('BD', 'Bangladesh', 'Asia', [23.68, 90.36], 173, 437, 73, 3, 39),
  c('SA', 'Saudi Arabia', 'Asia', [23.89, 45.08], 36, 1070, 78, 1, 99),
  // Europe
  c('DE', 'Germany', 'Europe', [51.17, 10.45], 84, 4460, 81, 52, 91),
  c('GB', 'United Kingdom', 'Europe', [55.38, -3.44], 68, 3340, 81, 45, 97),
  c('FR', 'France', 'Europe', [46.23, 2.21], 68, 3030, 83, 26, 92),
  c('SE', 'Sweden', 'Europe', [60.13, 18.64], 10.5, 585, 83, 68, 95),
  // Africa
  c('NG', 'Nigeria', 'Africa', [9.08, 8.68], 224, 363, 53, 20, 45),
  c('EG', 'Egypt', 'Africa', [26.82, 30.8], 112, 396, 70, 12, 72),
  c('KE', 'Kenya', 'Africa', [-0.02, 37.91], 55, 108, 62, 88, 40),
  c('ZA', 'South Africa', 'Africa', [-30.56, 22.94], 60, 380, 64, 11, 72),
  c('ET', 'Ethiopia', 'Africa', [9.15, 40.49], 126, 156, 66, 95, 17),
  // North America
  c('US', 'United States', 'North America', [37.09, -95.71], 335, 27360, 78, 22, 92),
  c('CA', 'Canada', 'North America', [56.13, -106.35], 40, 2140, 82, 68, 93),
  c('MX', 'Mexico', 'North America', [23.63, -102.55], 128, 1790, 75, 25, 81),
  // South America
  c('BR', 'Brazil', 'South America', [-14.24, -51.93], 216, 2170, 75, 89, 84),
  c('AR', 'Argentina', 'South America', [-38.42, -63.62], 46, 640, 76, 38, 88),
  c('CO', 'Colombia', 'South America', [4.57, -74.3], 52, 363, 77, 70, 73),
  c('CL', 'Chile', 'South America', [-35.68, -71.54], 19.6, 335, 80, 55, 90),
  // Oceania
  c('AU', 'Australia', 'Oceania', [-25.27, 133.78], 26, 1720, 83, 36, 96),
  c('NZ', 'New Zealand', 'Oceania', [-40.9, 174.89], 5.2, 252, 82, 85, 96),
];
