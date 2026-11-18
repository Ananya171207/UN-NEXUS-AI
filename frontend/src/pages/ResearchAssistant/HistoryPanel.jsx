import { useMemo, useState } from 'react';
import { MessageSquare, Plus, Search, Trash2, X } from 'lucide-react';
import Modal from '../../components/common/Modal';
import EmptyState from '../../components/common/EmptyState';
import { dayLabel, formatRelative } from '../../utils/format';
import { filterConversations, groupConversations } from './utils';

export default function HistoryPanel({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onClearAll,
  query,
  onQuery,
  now,
  open,
  onClose,
}) {
  const [confirm, setConfirm] = useState(null); // { kind: 'one', id, title } | { kind: 'all' }

  const visible = useMemo(() => filterConversations(conversations, query), [conversations, query]);
  const groups = useMemo(() => groupConversations(visible, (iso) => dayLabel(iso, now)), [visible, now]);

  function confirmAction() {
    if (confirm.kind === 'all') onClearAll();
    else onDelete(confirm.id);
    setConfirm(null);
  }

  return (
    <aside className={`history ${open ? 'open' : ''}`} aria-label="Conversation history">
      <div className="history-head">
        <h3>History</h3>
        <button type="button" className="icon-btn mobile-only" onClick={onClose} aria-label="Close history">
          <X size={16} />
        </button>
      </div>

      <button type="button" className="btn new-chat" onClick={onNew}>
        <Plus size={15} /> New research
      </button>

      <div className="search-field history-search">
        <Search size={14} />
        <input
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="Search history…"
          aria-label="Search conversation history"
        />
      </div>

      <div className="history-list">
        {conversations.length === 0 ? (
          <EmptyState icon={MessageSquare} title="No conversations yet">
            Your questions are saved here, in this browser only.
          </EmptyState>
        ) : visible.length === 0 ? (
          <EmptyState icon={Search} title="No matches">No conversation matches “{query}”.</EmptyState>
        ) : (
          groups.map((group) => (
            <section key={group.label}>
              <h4 className="history-group">{group.label}</h4>
              <ul>
                {group.items.map((conversation) => {
                  const questions = conversation.messages.filter((m) => m.role === 'user').length;
                  return (
                    <li key={conversation.id} className={conversation.id === activeId ? 'active' : ''}>
                      <button
                        type="button"
                        className="history-item"
                        onClick={() => onSelect(conversation.id)}
                        aria-current={conversation.id === activeId ? 'true' : undefined}
                      >
                        <strong>{conversation.title}</strong>
                        <small>
                          {questions} question{questions === 1 ? '' : 's'} · {formatRelative(conversation.updatedAt, now)}
                        </small>
                      </button>
                      <button
                        type="button"
                        className="icon-btn small history-delete"
                        aria-label={`Delete conversation: ${conversation.title}`}
                        onClick={() => setConfirm({ kind: 'one', id: conversation.id, title: conversation.title })}
                      >
                        <Trash2 size={13} />
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))
        )}
      </div>

      {conversations.length > 0 && (
        <button type="button" className="btn btn-ghost clear-all" onClick={() => setConfirm({ kind: 'all' })}>
          <Trash2 size={13} /> Clear all history
        </button>
      )}
      <p className="fine-print history-note">Saved only in this browser. Not synced to any server.</p>

      {confirm && (
        <Modal
          title={confirm.kind === 'all' ? 'Clear all history?' : 'Delete this conversation?'}
          onClose={() => setConfirm(null)}
          footer={
            <>
              <button type="button" className="btn" onClick={() => setConfirm(null)}>Cancel</button>
              <button type="button" className="btn btn-danger" onClick={confirmAction}>
                {confirm.kind === 'all' ? 'Clear all' : 'Delete'}
              </button>
            </>
          }
        >
          <p className="modal-text">
            {confirm.kind === 'all'
              ? `All ${conversations.length} saved conversations will be removed from this browser. This cannot be undone.`
              : `“${confirm.title}” will be removed from this browser. This cannot be undone.`}
          </p>
        </Modal>
      )}
    </aside>
  );
}
