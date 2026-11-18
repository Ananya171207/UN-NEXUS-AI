import { useState } from 'react';
import { ChevronDown } from 'lucide-react';

// Expandable information panel.
export default function Accordion({ title, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={`accordion ${open ? 'open' : ''}`}>
      <button type="button" className="accordion-toggle" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span>{title}</span>
        <ChevronDown size={16} />
      </button>
      <div className="accordion-content" aria-hidden={!open}>
        <div className="accordion-inner">{children}</div>
      </div>
    </div>
  );
}
