import { RotateCcw, Info } from 'lucide-react';

// Grey shimmering placeholder shown while data loads.
export function Skeleton({ height = 16, width = '100%', className = '' }) {
  return <div className={`skeleton ${className}`} style={{ height, width }} aria-hidden="true" />;
}

// Shown when loading data fails.
export function ErrorState({ title = 'Something went wrong', message, onRetry }) {
  return (
    <div className="empty-state error-state" role="alert">
      <Info size={26} />
      <strong>{title}</strong>
      {message && <p>{message}</p>}
      {onRetry && (
        <button type="button" className="btn" onClick={onRetry}>
          <RotateCcw size={14} /> Try again
        </button>
      )}
    </div>
  );
}
