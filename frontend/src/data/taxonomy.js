
import {
  Landmark,
  TrendingUp,
  Leaf,
  LifeBuoy,
  Sprout,
  Network,
  HeartPulse,
  Shield,
  Globe,
} from 'lucide-react';

// Shared vocabulary used by the map, filters and event feeds.

export const REGIONS = [
  'Asia',
  'Europe',
  'Africa',
  'North America',
  'South America',
  'Oceania',
];

export const SEVERITY_LEVELS = ['low', 'moderate', 'high', 'critical'];

// "none" is used for a country with no events matching the current filters.
export const SEVERITY_RANK = {
  none: 0,
  low: 1,
  moderate: 2,
  high: 3,
  critical: 4,
};

export const EVENT_CATEGORIES = [
  { id: 'Development', icon: Sprout },
  { id: 'Environmental', icon: Leaf },
  { id: 'Health', icon: HeartPulse },
  { id: 'Humanitarian', icon: LifeBuoy },
  { id: 'Other', icon: Globe },
  { id: 'Political', icon: Landmark },
  { id: 'Security', icon: Shield },
];

export const WORLD_VIEW = { center: [20, 10], zoom: 2 };

// Where the map flies to when a region filter is chosen.
export const REGION_VIEWS = {
  All: WORLD_VIEW,
  Asia: { center: [30, 95], zoom: 3 },
  Europe: { center: [52, 14], zoom: 4 },
  Africa: { center: [2, 20], zoom: 3 },
  'North America': { center: [45, -100], zoom: 3 },
  'South America': { center: [-18, -60], zoom: 3 },
  Oceania: { center: [-27, 150], zoom: 3 },
};
