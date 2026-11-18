// Tells the user what kind of data they are looking at.
//   sample    - invented illustrative data (not real)
//   verified  - taken from a named official source
//   reference - fixed facts about the framework itself (e.g. 17 SDGs)
const LABELS = {
  sample: 'Sample data',
  verified: 'Verified data',
  reference: 'Reference',
};

export default function DataBadge({ type = 'sample', children }) {
  return <span className={`badge badge-${type}`}>{children || LABELS[type]}</span>;
}
