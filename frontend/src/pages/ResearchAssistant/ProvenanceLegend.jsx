import ProvenanceBadge from '../../components/common/ProvenanceBadge';
import { PROVENANCE, PROVENANCE_ORDER } from '../../data/provenance';

// Explains the four content labels.
export default function ProvenanceLegend() {
  return (
    <dl className="legend-list">
      {PROVENANCE_ORDER.map((kind) => (
        <div key={kind}>
          <dt><ProvenanceBadge kind={kind} /></dt>
          <dd>{PROVENANCE[kind].description}</dd>
        </div>
      ))}
    </dl>
  );
}
