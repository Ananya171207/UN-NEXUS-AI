import { Bot, BookOpen, Globe, LayoutDashboard, Settings, Target } from 'lucide-react';

// One list drives the sidebar, the breadcrumb, the top-bar search and the
// "Platform modules" panel, so a module is only defined once.
export const NAV_ITEMS = [
  {
    id: 'overview',
    label: 'Overview',
    icon: LayoutDashboard,
    description: 'Command centre summarising the whole platform.',
    status: 'available',
    keywords: ['home', 'dashboard', 'command centre'],
  },
  {
    id: 'situation-room',
    label: 'Situation Room',
    icon: Globe,
    description: 'Interactive world map, country profiles and a global event feed.',
    status: 'available',
    keywords: ['map', 'country', 'events', 'monitoring', 'regions'],
  },
  {
    id: 'research-assistant',
    label: 'Research Assistant',
    icon: Bot,
    description: 'AI research workspace for questions about global development.',
    status: 'available',
    keywords: ['ai', 'chat', 'research', 'questions', 'sources'],
  },
  {
    id: 'sdg-tracker',
    label: 'SDG Tracker',
    icon: Target,
    description: 'Progress across all 17 Sustainable Development Goals.',
    status: 'available',
    keywords: ['sdg', 'goals', 'sustainable', 'indicators'],
  },
  {
    id: 'india-vs-world',
    label: 'India vs World',
    icon: BookOpen,
    description: 'Compare India with other countries and the world average.',
    status: 'available',
    keywords: ['india', 'compare', 'comparison', 'gdp', 'countries'],
  },
];

export const SETTINGS_ITEM = {
  id: 'settings',
  label: 'Settings',
  icon: Settings,
  description: 'Preferences, data sources and backend connection.',
  status: 'planned',
  phase: 7,
  keywords: ['preferences', 'backend', 'api', 'profile'],
};

export const ALL_PAGES = [...NAV_ITEMS, SETTINGS_ITEM];
