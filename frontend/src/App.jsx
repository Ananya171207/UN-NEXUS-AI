import { useEffect, useState } from 'react';
import Sidebar from './components/layout/Sidebar';
import Topbar from './components/layout/Topbar';
import Overview from './pages/Overview/Overview';
import SituationRoom from './pages/SituationRoom/SituationRoom';
import ResearchAssistant from './pages/ResearchAssistant/ResearchAssistant';
import SdgTracker from './pages/SdgTracker/SdgTracker';
import IndiaVsWorld from './pages/IndiaVsWorld/IndiaVsWorld';
import ComingSoon from './pages/ComingSoon/ComingSoon';
import { ALL_PAGES } from './data/navigation';
import './App.css';

// Pages that are fully built. Each later phase adds one entry here
// (for example 'situation-room': SituationRoom) and the placeholder
// is replaced automatically.
const PAGES = {
  overview: Overview,
  'situation-room': SituationRoom,
  'research-assistant': ResearchAssistant,
  'sdg-tracker': SdgTracker,
  'india-vs-world': IndiaVsWorld,
};

export default function App() {
  const [activeId, setActiveId] = useState('overview');
  const [mobileOpen, setMobileOpen] = useState(false);

  const activePage = ALL_PAGES.find((p) => p.id === activeId) || ALL_PAGES[0];
  const PageComponent = PAGES[activePage.id];

  function navigate(id) {
    setActiveId(id);
    setMobileOpen(false);
    window.scrollTo({ top: 0 });
  }

  // Escape closes the mobile menu
  useEffect(() => {
    function onKey(event) {
      if (event.key === 'Escape') setMobileOpen(false);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="app-shell">
      <Sidebar
        activeId={activePage.id}
        onNavigate={navigate}
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
      />

      <main className="main-content">
        <Topbar
          activeLabel={activePage.label}
          onMenu={() => setMobileOpen(true)}
          onNavigate={navigate}
        />
        {/* key makes the page animate in every time you change module */}
        <div className="page-transition" key={activePage.id}>
          {PageComponent ? (
            <PageComponent onNavigate={navigate} />
          ) : (
            <ComingSoon page={activePage} />
          )}
        </div>
      </main>
    </div>
  );
}
