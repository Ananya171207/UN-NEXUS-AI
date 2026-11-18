import { useEffect, useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { copyText } from '../../utils/clipboard';

// Copies `text` and briefly shows "Copied".
export default function CopyButton({ text, label = 'Copy' }) {
  const [status, setStatus] = useState('idle'); // idle | copied | failed

  useEffect(() => {
    if (status === 'idle') return undefined;
    const id = setTimeout(() => setStatus('idle'), 1800);
    return () => clearTimeout(id);
  }, [status]);

  async function onClick() {
    setStatus((await copyText(text)) ? 'copied' : 'failed');
  }

  return (
    <button type="button" className="btn" onClick={onClick} aria-live="polite">
      {status === 'copied' ? <Check size={14} /> : <Copy size={14} />}
      {status === 'copied' ? 'Copied' : status === 'failed' ? 'Copy failed' : label}
    </button>
  );
}
