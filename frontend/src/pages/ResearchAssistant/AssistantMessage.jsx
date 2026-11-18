import { Bot, ExternalLink, RotateCcw } from 'lucide-react';
import Accordion from '../../components/common/Accordion';
import CopyButton from '../../components/common/CopyButton';
import ProvenanceBadge from '../../components/common/ProvenanceBadge';
import { formatTime } from '../../utils/format';
import CitedText from './CitedText';
import { responseToText } from './utils';

const CLAIM_LABEL = { fact: 'Reported', estimate: 'Estimate', interpretation: 'Analysis' };
const STATUS_TEXT = {
  sufficient: 'Evidence: sufficient',
  limited: 'Evidence: limited',
  insufficient: 'Evidence: insufficient',
};

function SectionHead({ title, kind }) {
  return (
    <div className="ans-head">
      <h4>{title}</h4>
      {kind && <ProvenanceBadge kind={kind} />}
    </div>
  );
}

function ClaimTag({ type }) {
  return <span className={`claim-tag claim-${type}`}>{CLAIM_LABEL[type]}</span>;
}

export default function AssistantMessage({ message, isLast, loading, onAsk, onRegenerate }) {
  const r = message.response;
  const cite = (text, citations = []) => <CitedText text={text} citations={citations} sources={r.sources} />;

  return (
    <article className="msg msg-assistant" aria-label="Research assistant answer">
      <header className="msg-head">
        <span className="bot-avatar"><Bot size={15} /></span>
        <strong>Research assistant</strong>
        <ProvenanceBadge kind="ai" short />
        <span className={`badge evidence-${r.evidenceStatus}`}>{STATUS_TEXT[r.evidenceStatus] || STATUS_TEXT.limited}</span>
        <time dateTime={message.createdAt}>{formatTime(message.createdAt)}</time>
      </header>

      {r.title && <h3 className="ans-title">{r.title}</h3>}

      <section className="ans-section">
        <SectionHead title="Summary" kind={r.summary.provenance} />
        <p className="ans-summary">{cite(r.summary.text)}</p>
      </section>

      {r.keyFindings.items.length > 0 && (
        <section className="ans-section">
          <SectionHead title="Key findings" kind={r.keyFindings.provenance} />
          <ol className="findings">
            {r.keyFindings.items.map((item) => (
              <li key={item.text}>
                <ClaimTag type={item.claimType} /> {cite(item.text, item.citations)}
                {item.quote && <blockquote className="evidence-quote">“{item.quote}” <small>(verified in source)</small></blockquote>}
              </li>
            ))}
          </ol>
        </section>
      )}

      {r.statistics.length > 0 && (
        <section className="ans-section">
          <SectionHead title="Key statistics" />
          <ul className="stats-list">
            {r.statistics.map((stat) => (
              <li key={`${stat.label}-${stat.value}`}>
                <strong className="stat-value">{stat.value}</strong>
                <span className="stat-label">
                  {stat.label}
                  <small>
                    {[stat.geography, stat.year, CLAIM_LABEL[stat.claimType]].filter(Boolean).join(' · ')}
                    {stat.outdated && <em className="outdated-flag"> · may be outdated</em>}
                  </small>
                  <small>{cite('', stat.citations)}</small>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {(r.regions.length > 0 || r.sdgs.length > 0) && (
        <section className="ans-section">
          <div className="ans-head"><h4>Regions and goals</h4></div>
          <div className="related">
            {r.regions.map((region) => <span key={region} className="chip static-chip">{region}</span>)}
            {r.sdgs.map((n) => <span key={n} className="chip static-chip">SDG {n}</span>)}
          </div>
        </section>
      )}

      {r.analysis && (
        <Accordion
          defaultOpen
          title={<span className="acc-title">Detailed analysis <ProvenanceBadge kind={r.analysis.provenance} /></span>}
        >
          {r.analysis.sections.map((section) => (
            <div key={section.heading} className="ans-subsection">
              <h5>{section.heading} <ClaimTag type={section.claimType} /></h5>
              {section.paragraphs.map((paragraph) => (
                <p key={paragraph} className="ans-paragraph">{cite(paragraph, section.citations)}</p>
              ))}
            </div>
          ))}
        </Accordion>
      )}

      {r.recommendations.length > 0 && (
        <section className="ans-section">
          <SectionHead title="Recommendations" kind="ai" />
          <ul className="recs">
            {r.recommendations.map((rec) => (
              <li key={rec.text}>
                <span>{cite(rec.text, rec.citations)}</span>
                <small>
                  {rec.officialUn
                    ? `Stated as a UN position${rec.attributedTo ? ` (${rec.attributedTo})` : ''}; wording confirmed in the cited source`
                    : rec.origin === 'source_stated'
                      ? `Stated in a cited source${rec.attributedTo ? ` (${rec.attributedTo})` : ''}; not confirmed as an official UN position`
                      : 'Analyst inference. Not an official UN position'}
                </small>
              </li>
            ))}
          </ul>
        </section>
      )}

      {r.sources.length > 0 && (
        <section className="ans-section">
          <div className="ans-head"><h4>Source references</h4></div>
          <ul className="sources">
            {r.sources.map((source) => (
              <li key={source.id} className={source.used ? '' : 'source-unused'}>
                <div className="source-main">
                  {source.url ? (
                    <a href={source.url} target="_blank" rel="noopener noreferrer">
                      [{source.id}] {source.title} <ExternalLink size={12} />
                    </a>
                  ) : (
                    <strong>[{source.id}] {source.title}</strong>
                  )}
                  {source.publisher && <small>{source.publisher}</small>}
                  {source.note && <small className="source-note">{source.note}</small>}
                </div>
                <ProvenanceBadge kind={source.provenance} short />
              </li>
            ))}
          </ul>
        </section>
      )}

      {r.relatedTopics.length > 0 && (
        <section className="ans-section">
          <div className="ans-head"><h4>Related topics</h4></div>
          <div className="related">
            {r.relatedTopics.map((topic) => (
              <button key={topic.question} type="button" className="chip" disabled={loading} onClick={() => onAsk(topic.question)}>
                {topic.label}
              </button>
            ))}
          </div>
        </section>
      )}

      {r.limitations.length > 0 && (
        <ul className="limitations" aria-label="Limitations">
          {r.limitations.map((item) => <li key={item}>{item}</li>)}
        </ul>
      )}

      <Accordion title="How this answer was researched">
        <ul className="plain-list process-list">
          <li>Searches run: {r.process.queries.length > 0 ? r.process.queries.map((q) => `“${q}”`).join(', ') : 'none'}</li>
          <li>Sources found {r.process.found} · read {r.process.retrieved} · cited {r.process.used} · distinct sites {r.process.domains}</li>
          {r.process.unreachable.map((u) => <li key={u.url}>Could not read {u.url}: {u.reason}</li>)}
          <li>Model: {r.process.model || 'unknown'}{r.process.durationMs ? ` · ${(r.process.durationMs / 1000).toFixed(1)} s` : ''}</li>
        </ul>
      </Accordion>

      <footer className="msg-actions">
        <CopyButton text={responseToText(r)} label="Copy answer" />
        {isLast && (
          <button type="button" className="btn btn-ghost" onClick={onRegenerate} disabled={loading}>
            <RotateCcw size={13} /> Ask again
          </button>
        )}
      </footer>
    </article>
  );
}
