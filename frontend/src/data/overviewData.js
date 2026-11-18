// =====================================================================
// SAMPLE DATA ONLY
// Nothing in this file is an official statistic or a real news event.
// It exists so the interface can be designed and tested before a real
// data source (the future FastAPI backend) is connected.
// =====================================================================

export { SEVERITY_LEVELS } from './taxonomy';

// Locations carry a region so the Situation Room can reuse them in Phase 3.
export const sampleEvents = [
  {
    id: 'evt-delhi',
    location: 'New Delhi',
    region: 'Asia',
    position: [28.61, 77.2],
    category: 'Environmental',
    severity: 'moderate',
    title: 'Air quality monitoring alert',
    summary: 'Placeholder entry showing how an environmental alert will appear.',
  },
  {
    id: 'evt-london',
    location: 'London',
    region: 'Europe',
    position: [51.5, -0.12],
    category: 'Economic',
    severity: 'low',
    title: 'Economic indicator update',
    summary: 'Placeholder entry showing how an economic update will appear.',
  },
  {
    id: 'evt-newyork',
    location: 'New York',
    region: 'North America',
    position: [40.71, -74.0],
    category: 'International relations',
    severity: 'low',
    title: 'Multilateral session scheduled',
    summary: 'Placeholder entry showing how an international-relations item will appear.',
  },
  {
    id: 'evt-tokyo',
    location: 'Tokyo',
    region: 'Asia',
    position: [35.67, 139.65],
    category: 'Development',
    severity: 'low',
    title: 'Development programme review',
    summary: 'Placeholder entry showing how a development item will appear.',
  },
  {
    id: 'evt-nairobi',
    location: 'Nairobi',
    region: 'Africa',
    position: [-1.28, 36.82],
    category: 'Humanitarian',
    severity: 'high',
    title: 'Food security watch',
    summary: 'Placeholder entry showing how a humanitarian alert will appear.',
  },
  {
    id: 'evt-brasilia',
    location: 'Brasília',
    region: 'South America',
    position: [-15.79, -47.88],
    category: 'Political',
    severity: 'moderate',
    title: 'Policy announcement',
    summary: 'Placeholder entry showing how a political item will appear.',
  },
];

// Illustrative trend series for the overview chart.
export const trendSeries = [
  {
    id: 'sdg-index',
    label: 'Composite SDG progress index',
    unit: 'index (0–100)',
    data: [
      { year: '2018', value: 54 },
      { year: '2019', value: 55 },
      { year: '2020', value: 55 },
      { year: '2021', value: 57 },
      { year: '2022', value: 58 },
      { year: '2023', value: 60 },
      { year: '2024', value: 61 },
    ],
  },
  {
    id: 'renewables',
    label: 'Renewable energy share',
    unit: '% of energy',
    data: [
      { year: '2018', value: 17 },
      { year: '2019', value: 18 },
      { year: '2020', value: 20 },
      { year: '2021', value: 21 },
      { year: '2022', value: 23 },
      { year: '2023', value: 25 },
      { year: '2024', value: 27 },
    ],
  },
  {
    id: 'education',
    label: 'School completion rate',
    unit: '% of age group',
    data: [
      { year: '2018', value: 71 },
      { year: '2019', value: 72 },
      { year: '2020', value: 72 },
      { year: '2021', value: 73 },
      { year: '2022', value: 75 },
      { year: '2023', value: 76 },
      { year: '2024', value: 77 },
    ],
  },
];
