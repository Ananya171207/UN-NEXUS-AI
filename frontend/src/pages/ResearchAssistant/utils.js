import { PROVENANCE } from '../../data/provenance';

export const MAX_QUESTION_LENGTH = 1000;
export const MAX_CONVERSATIONS = 30;

export function uid() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function titleFromQuestion(question) {
  const clean = question.replace(/\s+/g, ' ').trim();
  return clean.length > 60 ? `${clean.slice(0, 57)}…` : clean;
}

// Plain-text version of one answer, used by the Copy buttons.
export function responseToText(response) {
  const label = (kind) => PROVENANCE[kind]?.label ?? kind;
  const claim = { fact: 'Reported', estimate: 'Estimate', interpretation: 'Analysis' };
  const lines = [];

  if (response.title) lines.push(response.title.toUpperCase(), '');
  lines.push(`SUMMARY [${label(response.summary.provenance)}]`, response.summary.text, '');

  if (response.keyFindings.items.length > 0) {
    lines.push('KEY FINDINGS');
    response.keyFindings.items.forEach((item, i) => lines.push(`${i + 1}. [${claim[item.claimType]}] ${item.text}`));
    lines.push('');
  }

  if (response.statistics?.length > 0) {
    lines.push('KEY STATISTICS');
    for (const s of response.statistics) {
      const meta = [s.geography, s.year].filter(Boolean).join(', ');
      lines.push(`- ${s.label}: ${s.value}${meta ? ` (${meta})` : ''}${s.outdated ? ' [may be outdated]' : ''} [${s.citations.join(', ')}]`);
    }
    lines.push('');
  }

  for (const section of response.analysis?.sections ?? []) {
    lines.push(section.heading.toUpperCase(), ...section.paragraphs, '');
  }

  if (response.recommendations?.length > 0) {
    lines.push('RECOMMENDATIONS');
    for (const r of response.recommendations) {
      lines.push(`- ${r.text} (${r.officialUn ? 'stated as a UN position' : r.origin === 'source_stated' ? 'stated in a cited source' : 'analyst inference, not an official UN position'})`);
    }
    lines.push('');
  }

  if (response.sources.length > 0) {
    lines.push('SOURCES');
    for (const source of response.sources.filter((x) => x.used)) {
      const parts = [`- [${source.id}] ${source.title}`];
      if (source.publisher) parts.push(`- ${source.publisher}`);
      if (source.note) parts.push(`(${source.note})`);
      if (source.url) parts.push(source.url);
      lines.push(parts.join(' '));
    }
    lines.push('');
  }

  if (response.relatedTopics.length > 0) {
    lines.push('RELATED TOPICS', ...response.relatedTopics.map((t) => `- ${t.label}`), '');
  }

  if (response.limitations.length > 0) {
    lines.push('LIMITATIONS', ...response.limitations.map((l) => `- ${l}`));
  }

  return lines.join('\n').trim();
}

export function conversationToText(conversation) {
  const parts = [`${conversation.title} — UN NEXUS AI research conversation`, ''];
  for (const message of conversation.messages) {
    if (message.role === 'user') parts.push(`QUESTION: ${message.text}`, '');
    else if (message.response) parts.push('ANSWER:', responseToText(message.response), '', '---', '');
  }
  return parts.join('\n').trim();
}

// What is sent to the backend as conversation context.
export function historyForApi(messages) {
  return messages
    .filter((m) => m.role === 'user' || (m.role === 'assistant' && m.response))
    .slice(-10)
    .map((m) => (m.role === 'user' ? { role: 'user', text: m.text } : { role: 'assistant', text: m.response.summary.text }));
}

export function filterConversations(conversations, query) {
  const q = query.trim().toLowerCase();
  if (!q) return conversations;
  return conversations.filter(
    (c) => c.title.toLowerCase().includes(q) || c.messages.some((m) => m.role === 'user' && m.text.toLowerCase().includes(q))
  );
}

// Newest first, grouped under "Today", "Yesterday", dates…
export function groupConversations(conversations, labelFn) {
  const sorted = [...conversations].sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
  const groups = [];
  for (const conversation of sorted) {
    const label = labelFn(conversation.updatedAt);
    const last = groups[groups.length - 1];
    if (last && last.label === label) last.items.push(conversation);
    else groups.push({ label, items: [conversation] });
  }
  return groups;
}
