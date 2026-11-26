import Modal from '../../components/common/Modal';
import CopyButton from '../../components/common/CopyButton';
import DataBadge from '../../components/common/DataBadge';
import { formatDateTime, formatRelative } from '../../utils/format';

export default function EventModal({
  event,
  country,
  onClose,
  onViewCountry,
  now,
}) {
  const isSample = Boolean(event.isSample);

  const sourceLabel =
    event.source || (isSample ? 'Demonstration data' : 'Source not provided');

  const copyText = [
    `${event.title} — ${country?.name ?? 'Unknown country'}`,
    `Severity: ${event.severity} · Category: ${event.category}`,
    `Time: ${formatDateTime(event.occurredAt)}`,
    `Source: ${sourceLabel}`,
    event.sourceDomain ? `Publisher: ${event.sourceDomain}` : null,
    event.url ? `Original article: ${event.url}` : null,
    event.summary,
    isSample
      ? 'DATA TYPE: Demonstration data, not a real event.'
      : null,
  ]
    .filter(Boolean)
    .join('\n');

  return (
    <Modal
      title={event.title}
      subtitle={`${country?.name || event.countryName || 'Global'} · ${
        country?.region || event.region || 'Unknown region'
      }`}
      onClose={onClose}
      footer={
        <>
          <CopyButton text={copyText} label="Copy summary" />

          <button
            type="button"
            className="btn"
            onClick={() => onViewCountry(event.countryId)}
            disabled={!event.countryId}
          >
            View country on map
          </button>
        </>
      }
    >
      <div className="modal-tags">
        <span className={`severity severity-${event.severity}`}>
          {event.severity}
        </span>

        <span className="badge badge-neutral">{event.category}</span>

        {isSample && (
          <DataBadge type="sample">Demonstration entry</DataBadge>
        )}
      </div>

      <p className="modal-text">
        {event.summary || 'No additional description is available.'}
      </p>

      <dl className="facts">
        <div>
          <dt>Published</dt>
          <dd>{formatDateTime(event.occurredAt)}</dd>
        </div>

        <div>
          <dt>Age</dt>
          <dd>{formatRelative(event.occurredAt, now)}</dd>
        </div>

        <div>
          <dt>Source</dt>
          <dd>{sourceLabel}</dd>
        </div>

        <div>
          <dt>Publisher domain</dt>
          <dd>{event.sourceDomain || 'Not provided'}</dd>
        </div>

        <div>
          <dt>Original article</dt>
          <dd>
            {event.url ? (
              <a
                href={event.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open original source
              </a>
            ) : (
              'Link not available'
            )}
          </dd>
        </div>

        <div>
          <dt>Classification</dt>
          <dd>{event.classification?.method || 'Not available'}</dd>
        </div>
      </dl>
    </Modal>
  );
}
