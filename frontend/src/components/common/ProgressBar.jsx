// Thin horizontal bar. `value` is placed between `min` and `max`.
export default function ProgressBar({ value, min = 0, max = 100, tone = 'accent', label }) {
  const percent = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
  return (
    <div
      className="progress"
      role="meter"
      aria-label={label}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={value}
    >
      <div className={`progress-fill tone-${tone}`} style={{ width: `${percent}%` }} />
    </div>
  );
}
