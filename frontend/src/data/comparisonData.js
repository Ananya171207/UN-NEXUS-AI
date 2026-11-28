// Selection presets only. All country statistics and indicator definitions
// now come from the live FastAPI comparison endpoints.

export const DEFAULT_COMPARE = ['CN', 'US', 'BR'];

// The backend allows five countries total, including India.
// India is fixed as the baseline here, so users can add at most four others.
export const MAX_COMPARE = 4;

export const QUICK_SETS = [
  { id: 'large', label: 'Largest economies', ids: ['US', 'CN', 'DE', 'JP'] },
  { id: 'asia', label: 'Asian peers', ids: ['CN', 'ID', 'BD', 'JP'] },
  { id: 'emerging', label: 'Emerging economies', ids: ['CN', 'BR', 'ZA', 'ID'] },
  { id: 'africa', label: 'African countries', ids: ['NG', 'EG', 'KE', 'ET'] },
];
