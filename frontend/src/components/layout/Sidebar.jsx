import { Globe, X } from 'lucide-react';
import { NAV_ITEMS, SETTINGS_ITEM } from '../../data/navigation';

function NavButton({ item, active, onNavigate }) {
  const Icon = item.icon;
  return (
    <button
      type="button"
      className={`nav-item ${active ? 'active' : ''}`}
      onClick={() => onNavigate(item.id)}
      aria-current={active ? 'page' : undefined}
    >
      <Icon size={17} />
      <span>{item.label}</span>
    </button>
  );
}

export default function Sidebar({ activeId, onNavigate, open, onClose }) {
  return (
    <>
      {open && <div className="sidebar-backdrop" onClick={onClose} aria-hidden="true" />}

      <aside className={`sidebar ${open ? 'sidebar-open' : ''}`} aria-label="Main navigation">
        <div className="brand">
          <div className="brand-icon">
            <Globe size={20} />
          </div>
          <div className="brand-text">
            <strong>UN NEXUS AI</strong>
            <span>Global Intelligence</span>
          </div>
          <button type="button" className="icon-btn mobile-only" onClick={onClose} aria-label="Close navigation">
            <X size={18} />
          </button>
        </div>

        <div className="nav-label">Workspace</div>
        <nav className="navigation">
          {NAV_ITEMS.map((item) => (
            <NavButton key={item.id} item={item} active={activeId === item.id} onNavigate={onNavigate} />
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="system-status" role="status">
            <span className="status-dot status-dot-amber" />
            <div>
              <strong>Sample data mode</strong>
              <small>Backend not connected</small>
            </div>
          </div>
          <NavButton item={SETTINGS_ITEM} active={activeId === SETTINGS_ITEM.id} onNavigate={onNavigate} />
        </div>
      </aside>
    </>
  );
}
