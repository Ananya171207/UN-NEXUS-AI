import DataBadge from './DataBadge';
import useCountUp from '../../hooks/useCountUp';

function AnimatedNumber({ value }) {
  return <>{useCountUp(value)}</>;
}

// `value` can be a number (counts up) or text (shown as is).
export default function MetricCard({ label, value, note, icon: Icon, badge, index = 0 }) {
  return (
    <div className="metric-card reveal" style={{ '--i': index }}>
      <div className="metric-label">
        <span>{label}</span>
        {Icon && <Icon size={16} />}
      </div>
      <div className="metric-value">
        {typeof value === 'number' ? <AnimatedNumber value={value} /> : value}
      </div>
      <div className="metric-note">
        {badge && <DataBadge type={badge} />} {note}
      </div>
    </div>
  );
}
