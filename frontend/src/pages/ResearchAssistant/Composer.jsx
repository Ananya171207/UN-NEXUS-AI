import { useEffect, useRef, useState } from 'react';
import { Send, Square } from 'lucide-react';
import { MAX_QUESTION_LENGTH } from './utils';

export default function Composer({ onSend, onStop, loading, focusKey }) {
  const [text, setText] = useState('');
  const areaRef = useRef(null);

  // Grow the box as the user types (up to a limit)
  useEffect(() => {
    const el = areaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [text]);

  // Focus the box when a new chat starts
  useEffect(() => {
    areaRef.current?.focus();
  }, [focusKey]);

  const canSend = text.trim().length > 0 && !loading;

  function submit() {
    if (!canSend) return;
    onSend(text.trim());
    setText('');
  }

  function onKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form
      className="composer"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <div className="composer-box">
        <textarea
          ref={areaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          maxLength={MAX_QUESTION_LENGTH}
          placeholder="Ask a research question about global development, the SDGs or a country…"
          aria-label="Research question"
        />
        {loading ? (
          <button type="button" className="send-btn stop" onClick={onStop} aria-label="Stop">
            <Square size={14} />
            Stop
          </button>
        ) : (
          <button type="submit" className="send-btn" disabled={!canSend} aria-label="Send question">
            <Send size={15} />
            Send
          </button>
        )}
      </div>
      <div className="composer-foot">
        <span>Enter to send · Shift+Enter for a new line</span>
        <span className="composer-mode live">Live research</span>
        <span className="composer-count" aria-live="off">
          {text.length}/{MAX_QUESTION_LENGTH}
        </span>
      </div>
    </form>
  );
}
