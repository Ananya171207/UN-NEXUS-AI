// =====================================================================
// SAMPLE DATA — NOT OFFICIAL STATISTICS
// Every score and indicator value in this file was entered by hand as a
// rounded, illustrative approximation so the SDG Tracker can be designed
// and tested. None of it comes from the UN, the World Bank or any other
// official source. Do not quote it. The backend will replace this file
// with real datasets (for example the UN SDG Global Database).
//
// The 17 goals themselves (names, colours, wording) are official and live
// in data/sdg.js. Only the numbers below are sample data.
// =====================================================================

export const SDG_DATA_NOTE =
  'Illustrative sample scores and indicators for interface design. Not official statistics.';

export const SCOPES = [
  { id: 'world', label: 'World' },
  { id: 'india', label: 'India' },
  { id: 'ssa', label: 'Sub-Saharan Africa' },
  { id: 'europe', label: 'Europe' },
  { id: 'lac', label: 'Latin America & Caribbean' },
];

// Sample progress score per goal (0 to 100), in goal order 1..17.
export const SAMPLE_SCORES = {
  world:  [64, 44, 62, 55, 47, 58, 70, 56, 53, 41, 52, 39, 36, 43, 46, 49, 61],
  india:  [60, 42, 61, 63, 44, 66, 78, 55, 57, 48, 50, 68, 64, 45, 52, 58, 70],
  ssa:    [35, 38, 42, 40, 43, 38, 36, 45, 30, 35, 38, 72, 78, 48, 50, 40, 50],
  europe: [85, 70, 80, 82, 72, 84, 75, 72, 78, 68, 70, 50, 55, 50, 55, 78, 80],
  lac:    [66, 58, 70, 62, 60, 64, 72, 55, 50, 38, 55, 58, 60, 50, 50, 42, 55],
};

// Score bands. These thresholds belong to this prototype, not to the UN.
export const STATUS_BANDS = [
  { id: 'on-track', label: 'On track', min: 70, tone: 'good' },
  { id: 'moderate', label: 'Moderate progress', min: 50, tone: 'mid' },
  { id: 'off-track', label: 'Off track', min: 0, tone: 'low' },
];

// Two sample indicators per goal. Values are [value in 2015, value in 2024]
// for the World and for India. `target` is an illustrative 2030 level
// (null when no simple target applies). `better` says which direction is good.
const ind = (label, unit, better, target, world, india) => ({ label, unit, better, target, world, india });

export const SAMPLE_INDICATORS = {
  1: [
    ind('Population below the international poverty line', '%', 'lower', 3, [11, 9], [22, 12]),
    ind('Population covered by social protection', '%', 'higher', 100, [45, 52], [24, 50]),
  ],
  2: [
    ind('Prevalence of undernourishment', '%', 'lower', 3, [8, 9], [15, 13]),
    ind('Children under 5 who are stunted', '%', 'lower', 10, [24, 22], [38, 31]),
  ],
  3: [
    ind('Under-5 mortality (per 1,000 live births)', '', 'lower', 25, [43, 36], [43, 30]),
    ind('Births attended by skilled health staff', '%', 'higher', 100, [80, 87], [81, 89]),
  ],
  4: [
    ind('Primary school completion rate', '%', 'higher', 100, [86, 89], [93, 95]),
    ind('Youth literacy rate', '%', 'higher', 100, [91, 93], [90, 94]),
  ],
  5: [
    ind('Seats held by women in national parliaments', '%', 'higher', 50, [22, 27], [12, 14]),
    ind('Girls completing secondary school', '%', 'higher', 100, [60, 69], [55, 72]),
  ],
  6: [
    ind('Population using safely managed drinking water', '%', 'higher', 100, [68, 74], [50, 60]),
    ind('Population using safely managed sanitation', '%', 'higher', 100, [47, 57], [30, 45]),
  ],
  7: [
    ind('Population with access to electricity', '%', 'higher', 100, [87, 92], [89, 99]),
    ind('Renewable share of electricity generation', '%', 'higher', null, [23, 30], [16, 21]),
  ],
  8: [
    ind('Unemployment rate', '%', 'lower', null, [5.8, 5.0], [5.6, 4.2]),
    ind('Young people not in education, employment or training', '%', 'lower', null, [22, 21], [30, 28]),
  ],
  9: [
    ind('Individuals using the internet', '%', 'higher', 100, [40, 67], [15, 52]),
    ind('Research and development spending (% of GDP)', '', 'higher', null, [1.9, 2.0], [0.7, 0.7]),
  ],
  10: [
    ind('Income share of the poorest 40% of people', '%', 'higher', null, [18, 19], [20, 20]),
    ind('Average cost of sending remittances', '%', 'lower', 3, [7.0, 6.2], [5.5, 5.0]),
  ],
  11: [
    ind('Urban population living in slums', '%', 'lower', 0, [24, 24], [35, 28]),
    ind('Urban population with convenient public transport', '%', 'higher', 100, [48, 52], [40, 46]),
  ],
  12: [
    ind('Material footprint per person (tonnes)', '', 'lower', null, [11.5, 12.2], [4.2, 5.5]),
    ind('Municipal waste that is recycled', '%', 'higher', null, [15, 19], [10, 13]),
  ],
  13: [
    ind('CO2 emissions per person (tonnes)', '', 'lower', null, [4.5, 4.7], [1.6, 2.0]),
    ind('Deaths and missing persons from disasters (per 100,000)', '', 'lower', null, [1.7, 1.3], [0.7, 0.5]),
  ],
  14: [
    ind('Marine area under protection', '%', 'higher', 30, [5, 8], [4, 6]),
    ind('Fish stocks within sustainable levels', '%', 'higher', 100, [68, 63], [65, 60]),
  ],
  15: [
    ind('Forest area as a share of land', '%', 'higher', null, [31.5, 31.0], [23.8, 24.7]),
    ind('Mountain green cover index', '', 'higher', null, [73, 75], [78, 80]),
  ],
  16: [
    ind('Children under 5 whose birth is registered', '%', 'higher', 100, [73, 77], [79, 89]),
    ind('People who feel safe walking alone at night', '%', 'higher', null, [66, 70], [66, 70]),
  ],
  17: [
    ind('Government revenue as a share of GDP', '%', 'higher', null, [28, 30], [17, 18]),
    ind('Fixed broadband subscriptions per 100 people', '', 'higher', null, [10, 19], [1.3, 2.8]),
  ],
};

export const SERIES_START_YEAR = 2015;
export const SERIES_END_YEAR = 2024;
