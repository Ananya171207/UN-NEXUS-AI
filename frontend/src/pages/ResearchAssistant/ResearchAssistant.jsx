import { useCallback, useEffect, useRef, useState } from 'react';
import { Clock } from 'lucide-react';
import CopyButton from '../../components/common/CopyButton';
import Accordion from '../../components/common/Accordion';
import useLocalStorage from '../../hooks/useLocalStorage';
import useNow from '../../hooks/useNow';
import { askResearchQuestion } from '../../services/researchService';
import ModeBanner from './ModeBanner';
import HistoryPanel from './HistoryPanel';
import EmptyThread from './EmptyThread';
import Thread from './Thread';
import Composer from './Composer';
import ProvenanceLegend from './ProvenanceLegend';
import {
  MAX_CONVERSATIONS,
  conversationToText,
  historyForApi,
  titleFromQuestion,
  uid,
} from './utils';
import './ResearchAssistant.css';

const STORAGE_KEY = 'un-nexus.research.v1';
const NONE = [];

export default function ResearchAssistant() {
  const [conversations, setConversations] = useLocalStorage(STORAGE_KEY, NONE);
  const [activeId, setActiveId] = useState(null); // null = a new, empty chat
  const [pending, setPending] = useState(null); // { conversationId } while a request is running
  const [notice, setNotice] = useState(null); // error or "stopped" message
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyQuery, setHistoryQuery] = useState('');
  const [focusKey, setFocusKey] = useState(0);
  const abortRef = useRef(null);
  const backendIds = useRef({}); // local chat id -> conversation id issued by the backend
  const now = useNow(30000).getTime();

  const active = conversations.find((c) => c.id === activeId) || null;
  const messages = active ? active.messages : NONE;
  const loading = pending !== null;
  const loadingHere = loading && pending.conversationId === activeId;
  const noticeHere = notice && notice.conversationId === activeId ? notice : null;

  // Cancel any running request when leaving the page
  useEffect(() => () => abortRef.current?.abort(), []);

  const runRequest = useCallback(
    async (conversationId, question, history, { fresh = false } = {}) => {
      const controller = new AbortController();
      abortRef.current = controller;
      setPending({ conversationId });
      setNotice(null);

      try {
        const response = await askResearchQuestion({
          question,
          history,
          conversationId: fresh ? null : backendIds.current[conversationId] || null,
          signal: controller.signal,
        });
        if (response.conversationId) backendIds.current[conversationId] = response.conversationId;
        const message = { id: uid(), role: 'assistant', response, createdAt: new Date().toISOString() };
        setConversations((list) =>
          list.map((c) =>
            c.id === conversationId ? { ...c, updatedAt: message.createdAt, messages: [...c.messages, message] } : c
          )
        );
      } catch (error) {
        if (error?.name === 'AbortError') {
          setNotice({ conversationId, kind: 'stopped', question, history });
        } else {
          setNotice({
            conversationId,
            kind: 'error',
            message: error?.message || 'Something went wrong. Please try again.',
            question,
            history,
          });
        }
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
          setPending(null);
        }
      }
    },
    [setConversations]
  );

  function send(rawQuestion) {
    const question = rawQuestion.trim();
    if (!question || loading) return;

    const createdAt = new Date().toISOString();
    const userMessage = { id: uid(), role: 'user', text: question, createdAt };
    const history = historyForApi(messages);
    let conversationId = activeId;

    if (!conversationId) {
      conversationId = uid();
      const conversation = {
        id: conversationId,
        title: titleFromQuestion(question),
        createdAt,
        updatedAt: createdAt,
        messages: [userMessage],
      };
      setConversations((list) => [conversation, ...list].slice(0, MAX_CONVERSATIONS));
      setActiveId(conversationId);
    } else {
      setConversations((list) =>
        list.map((c) => (c.id === conversationId ? { ...c, updatedAt: createdAt, messages: [...c.messages, userMessage] } : c))
      );
    }

    runRequest(conversationId, question, history);
  }

  function stop() {
    abortRef.current?.abort();
  }

  function regenerate() {
    if (!active || loading) return;
    const lastUserIndex = messages.map((m) => m.role).lastIndexOf('user');
    if (lastUserIndex === -1) return;
    // "Ask again" replays the question without the stored server-side turn, so it sends history explicitly.
    runRequest(active.id, messages[lastUserIndex].text, historyForApi(messages.slice(0, lastUserIndex)), { fresh: true });
  }

  function retry() {
    if (!noticeHere || loading) return;
    runRequest(noticeHere.conversationId, noticeHere.question, noticeHere.history);
  }

  function newChat() {
    setActiveId(null);
    setHistoryOpen(false);
    setFocusKey((k) => k + 1);
  }

  function selectConversation(id) {
    setActiveId(id);
    setHistoryOpen(false);
  }

  function deleteConversation(id) {
    if (pending?.conversationId === id) abortRef.current?.abort();
    setConversations((list) => list.filter((c) => c.id !== id));
    if (activeId === id) setActiveId(null);
  }

  function clearAll() {
    abortRef.current?.abort();
    setConversations(NONE);
    setActiveId(null);
  }

  const isEmpty = messages.length === 0 && !loadingHere;

  return (
    <div className="page research">
      <div className="res-layout">
        <HistoryPanel
          conversations={conversations}
          activeId={activeId}
          onSelect={selectConversation}
          onNew={newChat}
          onDelete={deleteConversation}
          onClearAll={clearAll}
          query={historyQuery}
          onQuery={setHistoryQuery}
          now={now}
          open={historyOpen}
          onClose={() => setHistoryOpen(false)}
        />

        <section className="panel res-main reveal">
          <header className="res-head">
            <div>
              <div className="eyebrow">Module 2 · Research</div>
              <h1>AI Global Research Assistant</h1>
            </div>
            <div className="res-head-actions">
              <span className="badge badge-neutral">Live research</span>
              <button type="button" className="btn history-toggle" onClick={() => setHistoryOpen((v) => !v)} aria-expanded={historyOpen}>
                <Clock size={14} /> History
              </button>
              {active && <CopyButton text={conversationToText(active)} label="Copy conversation" />}
            </div>
          </header>

          <div className="res-scroll">
            <div className="res-intro">
              <ModeBanner />
              {!isEmpty && (
                <div className="legend-strip">
                  <Accordion title="How answers are labelled">
                    <ProvenanceLegend />
                  </Accordion>
                </div>
              )}
            </div>
            {isEmpty ? (
              <EmptyThread onAsk={send} loading={loading} />
            ) : (
              <Thread
                messages={messages}
                loading={loadingHere}
                notice={noticeHere}
                onAsk={send}
                onRegenerate={regenerate}
                onRetry={retry}
              />
            )}
          </div>

          <Composer onSend={send} onStop={stop} loading={loading} focusKey={focusKey} />
        </section>
      </div>
    </div>
  );
}
