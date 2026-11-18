import { PROVENANCE } from '../../data/provenance';

// Small label showing where a piece of content came from
// (AI analysis, verified source, external reference or demonstration).
export default function ProvenanceBadge({ kind, short = false }) {
  const meta = PROVENANCE[kind];
  if (!meta) return null;
  return (
    <span className={`badge badge-prov-${kind}`} title={meta.description}>
      {short ? meta.short : meta.label}
    </span>
  );
}
