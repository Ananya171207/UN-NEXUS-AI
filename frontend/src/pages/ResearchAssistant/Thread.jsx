import { useEffect, useRef, useState } from 'react';
import { Bot, Info, RotateCcw } from 'lucide-react';
import { Skeleton } from '../../components/common/StateViews';
import { formatTime } from '../../utils/format';
import AssistantMessage from './AssistantMessage';

// The backend answers in one response (it does not stream progress), so this shows
// honest elapsed time instead of invented progress steps.
function LoadingMessage() {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <article className="msg msg-assistant loading" role="status" aria-live="polite" aria-label="Researching your question">
      <header className="msg-head">
        <span className="bot-avatar pulse"><Bot size={15} /></span>
        <strong>Research assistant</strong>
      </header>
      <p className="loading-step">Researching: searching sources, reading documents and writing a cited answer… {seconds}s</p>
      <Skeleton height={12} width="92%" className="mb-sm" />
      <Skeleton height={12} width="78%" className="mb-sm" />
      <Skeleton height={12} width="64%" />
      <p className="fine-print">This can take up to a minute. You can press Stop at any time.</p>
    </article>
  );
}

function Notice({ notice, onRetry }) {
  const isError = notice.kind === 'error';
  return (
    <div className={`notice ${notice.kind}`} role={isError ? 'alert' : 'status'}>
      <Info size={15} />
      <div>
        <strong>{isError ? 'Could not get an answer' : 'Request stopped'}</strong>
        <p>{isError ? notice.message : 'You stopped this request. Your question is saved above.'}</p>
      </div>
      <button type="button" className="btn" onClick={onRetry}>
        <RotateCcw size={13} /> {isError ? 'Try again' : 'Ask again'}
      </button>
    </div>
  );
}

export default function Thread({ messages, loading, notice, onAsk, onRegenerate, onRetry }) {
  const endRef = useRef(null);
  const threadRef = useRef(null);
  const lastAssistantId = [...messages].reverse().find((m) => m.role === 'assistant')?.id;
  const lastMessageIsAssistant = messages[messages.length - 1]?.role === 'assistant';

  // While waiting (or after an error) show the bottom. When an answer arrives,
  // show the START of it, so the summary is the first thing the reader sees.
  useEffect(() => {
    if (!lastMessageIsAssistant) {
      endRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' });
      return;
    }
    const answers = threadRef.current?.querySelectorAll('.msg-assistant:not(.loading)');
    answers?.[answers.length - 1]?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
  }, [messages.length, loading, notice, lastMessageIsAssistant]);

  return (
    <div className="thread" aria-live="off" ref={threadRef}>
      {messages.map((message) =>
        message.role === 'user' ? (
          <div key={message.id} className="msg msg-user">
            <p>{message.text}</p>
            <time dateTime={message.createdAt}>{formatTime(message.createdAt)}</time>
          </div>
        ) : (
          <AssistantMessage
            key={message.id}
            message={message}
            isLast={message.id === lastAssistantId && lastMessageIsAssistant}
            loading={loading}
            onAsk={onAsk}
            onRegenerate={onRegenerate}
          />
        )
      )}
      {loading && <LoadingMessage />}
      {notice && !loading && <Notice notice={notice} onRetry={onRetry} />}
      <div ref={endRef} />
    </div>
  );
}
