import { Fragment } from 'react';

const MARKER = /(\[S\d+(?:\s*,\s*S\d+)*\])/g;
const IS_MARKER = /^\[(S\d+(?:\s*,\s*S\d+)*)\]$/;

// Renders text and turns citation markers such as [S1, S2] into links to the retrieved sources.
// `citations` (ids) are appended when the text carries no marker of its own.
export default function CitedText({ text, citations = [], sources }) {
  const full = citations.length > 0 && !/\[S\d/.test(text) ? `${text} [${citations.join(', ')}]` : text;
  return (
    <>
      {full.split(MARKER).map((part, i) => {
        const match = part.match(IS_MARKER);
        if (!match) return <Fragment key={i}>{part}</Fragment>;
        const ids = match[1].split(/\s*,\s*/);
        return (
          <span key={i} className="cites">
            [
            {ids.map((id, j) => {
              const source = sources.find((s) => s.id === id);
              return (
                <Fragment key={id}>
                  {j > 0 && ', '}
                  {source?.url ? (
                    <a className="cite" href={source.url} target="_blank" rel="noopener noreferrer" title={`${source.publisher} — ${source.title}`}>
                      {id}
                    </a>
                  ) : (
                    id
                  )}
                </Fragment>
              );
            })}
            ]
          </span>
        );
      })}
    </>
  );
}
