import Modal from '../../components/common/Modal';
import CopyButton from '../../components/common/CopyButton';
import DataBadge from '../../components/common/DataBadge';
import { formatDateTime, formatRelative } from '../../utils/format';

export default function EventModal({ event, country, onClose, onViewCountry, now }) {
  const copyText = [
    `${event.title} — ${country?.name ?? 'Unknown country'}`,
    `Severity: ${event.severity} · Category: ${event.category}`,
    `Time: ${formatDateTime(event.occurredAt)}`,
    event.summary,
    'DATA TYPE: demonstration entry, not a real event.',
  ].join('\n');

  return (
    <Modal
      title={event.title}
      subtitle={`${country?.name} · ${country?.region}`}
      onClose={onClose}
      footer={
        <>
          <CopyButton text={copyText} label="Copy summary" />
          <button type="button" className="btn" onClick={() => onViewCountry(event.countryId)}>
            View country on map
          </button>
        </>
      }
    >
      <div className="modal-tags">
        <span className={`severity severity-${event.severity}`}>{event.severity}</span>
        <span className="badge badge-neutral">{event.category}</span>
        <DataBadge type="sample">Demonstration entry</DataBadge>
      </div>
      <p className="modal-text">{event.summary}</p>
      <dl className="facts">
        <div><dt>Occurred</dt><dd>{formatDateTime(event.occurredAt)}</dd></div>
        <div><dt>Age</dt><dd>{formatRelative(event.occurredAt, now)}</dd></div>
        <div><dt>Source</dt><dd>None — sample entry</dd></div>
        <div><dt>Verification</dt><dd>Not applicable</dd></div>
      </dl>
      <p className="fine-print">
        Real events, sources and verification status will come from the backend service once it is connected.
      </p>
    </Modal>
  );
}
