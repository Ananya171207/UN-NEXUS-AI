import DataBadge from '../../components/common/DataBadge';
import ProgressBar from '../../components/common/ProgressBar';
import CopyButton from '../../components/common/CopyButton';
import IndicatorChart from './IndicatorChart';
import { SAMPLE_INDICATORS, SAMPLE_SCORES } from '../../data/sdgProgress';
import { buildSeries, describeIndicator, statusFor } from './utils';

const fmt = (value, unit) => `${value}${unit ? ` ${unit}` : ''}`;

function indicatorText(goal, scope, score) {
  const lines = [`SDG ${goal.number} ${goal.name} — ${scope.label} (SAMPLE DATA, not official)`, `Sample score: ${score}/100 (${statusFor(score).label})`];
  const key = scope.id === 'india' ? 'india' : 'world';
  if (scope.id === 'world' || scope.id === 'india') {
    for (const item of SAMPLE_INDICATORS[goal.number]) {
      const d = describeIndicator(item, item[key]);
      lines.push(`- ${item.label}: ${fmt(item[key][0], item.unit)} (2015) -> ${fmt(item[key][1], item.unit)} (2024)${item.target !== null ? `; 2030 target ${fmt(item.target, item.unit)}` : ''}${d.flat ? '' : d.improving ? '; improving' : '; moving the wrong way'}`);
    }
  }
  return lines.join('\n');
}

export default function SdgDetail({ goal, scope }) {
  const score = SAMPLE_SCORES[scope.id][goal.number - 1];
  const world = SAMPLE_SCORES.world[goal.number - 1];
  const status = statusFor(score);
  const hasIndicators = scope.id === 'world' || scope.id === 'india';
  const key = scope.id === 'india' ? 'india' : 'world';
  const diff = score - world;

  return (
    <div className="sdgt-detail" style={{ '--goal': goal.color }}>
      <div className="sdgt-detail-head">
        <span className="sdgt-num large">{goal.number}</span>
        <div>
          <h4>{goal.name}</h4>
          <p>{goal.description}</p>
        </div>
      </div>

      <div className="sdgt-detail-score">
        <div className="sdgt-big">{score}<small>/100</small></div>
        <div className="sdgt-detail-score-text">
          <span className={`status-pill tone-${status.tone}`}>{status.label}</span>
          <small>
            {scope.id === 'world'
              ? 'Sample score for the world'
              : `${Math.abs(diff)} ${diff >= 0 ? 'above' : 'below'}${diff === 0 ? ' (equal to)' : ''} the sample world score of ${world}`}
          </small>
        </div>
      </div>
      <ProgressBar value={score} label="Sample score" />
      <p className="fine-print">Bands used here (a prototype choice, not a UN rule): 70+ on track, 50–69 moderate progress, below 50 off track.</p>

      <div className="sdgt-ind-head">
        <h5>Sample indicators · {scope.label}</h5>
        <DataBadge type="sample" />
      </div>

      {hasIndicators ? (
        SAMPLE_INDICATORS[goal.number].map((item, i) => {
          const d = describeIndicator(item, item[key]);
          return (
            <article className="sdgt-indicator" key={item.label}>
              <h6>{item.label}</h6>
              <div className="sdgt-ind-values">
                <span><small>2015</small><strong>{fmt(item[key][0], item.unit)}</strong></span>
                <span aria-hidden="true">→</span>
                <span><small>2024</small><strong>{fmt(item[key][1], item.unit)}</strong></span>
                {item.target !== null && <span><small>2030 target</small><strong>{fmt(item.target, item.unit)}</strong></span>}
              </div>
              <p className={`sdgt-ind-note ${d.flat ? '' : d.improving ? 'good' : 'bad'}`}>
                {d.flat ? 'No change over the period.' : d.improving ? '↑ Moving in the right direction.' : '↓ Moving in the wrong direction.'}
                {d.gap !== null && (d.gap === 0 ? ' Target level reached.' : ` Still ${fmt(d.gap, item.unit)} from the target.`)}
              </p>
              <IndicatorChart data={buildSeries(item[key], goal.number * 3 + i)} unit={item.unit} target={item.target} color={goal.color} />
            </article>
          );
        })
      ) : (
        <p className="sdgt-no-ind">Indicator charts are included for the World and India in this sample. Choose one of those scopes to see them. The score above is still shown for {scope.label}.</p>
      )}

      <div className="sdgt-detail-actions">
        <CopyButton text={indicatorText(goal, scope, score)} label="Copy summary" />
      </div>
    </div>
  );
}
