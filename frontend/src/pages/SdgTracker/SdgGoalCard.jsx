import ProgressBar from '../../components/common/ProgressBar';
import { statusFor } from './utils';

// One of the 17 goals. The coloured top edge is the official SDG colour.
export default function SdgGoalCard({ goal, score, selected, onSelect, index }) {
  const status = statusFor(score);
  return (
    <button
      type="button"
      className={`sdgt-card reveal ${selected ? 'selected' : ''}`}
      style={{ '--goal': goal.color, '--i': Math.min(index, 12) }}
      aria-pressed={selected}
      onClick={() => onSelect(goal.number)}
    >
      <span className="sdgt-num">{goal.number}</span>
      <span className="sdgt-card-body">
        <strong>{goal.name}</strong>
        <span className="sdgt-card-meta">
          <span className={`status-pill tone-${status.tone}`}>{status.label}</span>
          <span className="sdgt-score">{score}<small>/100</small></span>
        </span>
        <ProgressBar value={score} label={`Goal ${goal.number} sample score`} />
      </span>
    </button>
  );
}
