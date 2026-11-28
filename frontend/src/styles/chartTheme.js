// Chart libraries (Recharts, Leaflet) need real colour values in JavaScript.
// These values mirror tokens.css — keep both files in sync.

export const chartColors = {
  // Primary pastel palette
  accent: '#79699B',       // Lavender
  teal: '#64836F',         // Sage green
  blue: '#6486A5',         // Sky blue
  green: '#64836F',        // Sage green

  // Supporting semantic colours
  amber: '#6486A5',
  red: '#594875',

  // Chart surfaces and structure
  grid: '#E4E5E8',
  axis: '#898E98',
  tooltipBg: '#FFFFFF',
  tooltipBorder: '#E4E5E8',
};

export const severityColors = {
  low: '#64836F',
  moderate: '#6486A5',
  high: '#79699B',
  critical: '#594875',
};
