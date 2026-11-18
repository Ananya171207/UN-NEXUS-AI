import { RESEARCH_API_BASE_URL } from './api';

// =====================================================================
// Data access for the AI Global Research Assistant.
//
// Every question goes to the FastAPI backend (POST /api/research/ask). The
// backend searches real sources, reads them and asks the AI model to write a cited
// answer. The browser NEVER talks to the AI provider and holds no API keys.
// See backend/README.md for the full contract.
// =====================================================================

const asArray = (value) => (Array.isArray(value) ? value : []);
const asText = (value) => (typeof value === 'string' ? value : '');
const safeUrl = (value) => (typeof value === 'string' && /^https?:\/\//i.test(value) ? value : null);
const claimType = (value) => (['fact', 'estimate', 'interpretation'].includes(value) ? value : 'interpretation');
const citeIds = (value) => asArray(value).filter((id) => typeof id === 'string' && /^S\d+$/.test(id));

// "verified" = a UN-system / international-organisation page that the backend actually retrieved in full.
function sourceProvenance(source) {
  return source.category !== 'other' && source.retrieval === 'full_text' ? 'verified' : 'external';
}

function sourceNote(source) {
  const bits = [];
  if (source.published_date) bits.push(`Published ${source.published_date}${source.date_kind === 'modified' ? ' (last modified)' : ''}`);
  else bits.push('Publication date not stated');
  if (source.is_outdated) bits.push('may be outdated');
  if (source.retrieval === 'snippet_only') bits.push('only a search excerpt was available');
  if (!source.used) bits.push('retrieved but not cited');
  return bits.join(' · ');
}

// Makes sure whatever comes back has every field the interface expects.
function normalizeResponse(raw) {
  const body = raw && typeof raw === 'object' ? raw : {};
  const meta = body.research_metadata && typeof body.research_metadata === 'object' ? body.research_metadata : {};
  const sections = asArray(body.sections).map((section) => ({
    kind: asText(section?.kind),
    heading: asText(section?.heading),
    paragraphs: asArray(section?.paragraphs).map(asText).filter(Boolean),
    citations: citeIds(section?.citations),
    claimType: claimType(section?.claim_type),
  })).filter((section) => section.paragraphs.length > 0);

  return {
    mode: 'live',
    conversationId: asText(body.conversation_id) || null,
    title: asText(body.title),
    evidenceStatus: asText(meta.evidence_status) || 'limited',
    summary: { text: asText(body.summary) || 'No summary was returned.', provenance: 'ai' },
    keyFindings: {
      items: asArray(body.findings).map((f) => ({
        text: asText(f?.text),
        claimType: claimType(f?.claim_type),
        citations: citeIds(f?.citations),
        quote: f?.quote_verified ? asText(f?.evidence_quote) : '',
      })).filter((f) => f.text),
      provenance: 'ai',
    },
    statistics: asArray(body.statistics).map((s) => ({
      label: asText(s?.label),
      value: [asText(s?.value), asText(s?.unit)].filter(Boolean).join(' '),
      year: Number.isInteger(s?.year) ? s.year : null,
      geography: asText(s?.geography),
      claimType: s?.claim_type === 'estimate' ? 'estimate' : 'fact',
      outdated: s?.is_outdated === true,
      citations: citeIds(s?.citations),
    })).filter((s) => s.label && s.value),
    analysis: sections.length > 0 ? { sections, provenance: 'ai' } : null,
    recommendations: asArray(body.recommendations).map((r) => ({
      text: asText(r?.text),
      origin: r?.origin === 'source_stated' ? 'source_stated' : 'analyst_inference',
      attributedTo: asText(r?.attributed_to),
      officialUn: r?.official_un_position === true,
      citations: citeIds(r?.citations),
    })).filter((r) => r.text),
    regions: asArray(body.countries_and_regions).map(asText).filter(Boolean),
    sdgs: asArray(body.sdgs).filter((n) => Number.isInteger(n) && n >= 1 && n <= 17),
    sources: asArray(body.sources).map((source, i) => ({
      id: asText(source?.id) || `S${i + 1}`,
      title: asText(source?.title) || 'Untitled source',
      publisher: asText(source?.organisation),
      url: safeUrl(source?.url),
      provenance: sourceProvenance(source || {}),
      note: sourceNote(source || {}),
      used: source?.used === true,
    })).sort((a, b) => Number(b.used) - Number(a.used)),
    relatedTopics: asArray(body.related_questions).map(asText).filter(Boolean).map((q) => ({ label: q, question: q })),
    limitations: asArray(body.limitations).map(asText).filter(Boolean),
    process: {
      model: asText(meta.model),
      queries: asArray(meta.queries).map(asText),
      found: meta.sources_found ?? 0,
      retrieved: meta.sources_retrieved ?? 0,
      used: meta.sources_used ?? 0,
      domains: meta.distinct_domains ?? 0,
      durationMs: meta.duration_ms ?? null,
      unreachable: asArray(meta.unreachable_sources).map((u) => ({ url: asText(u?.url), reason: asText(u?.reason) })),
    },
  };
}

// Turns a failed HTTP response into an Error carrying the backend's own message.
async function errorFromResponse(response) {
  let message = '';
  let code = '';
  try {
    const body = await response.json();
    message = asText(body?.error?.message);
    code = asText(body?.error?.code);
  } catch {
    /* body was not JSON */
  }
  const error = new Error(message || `The research service answered with an error (${response.status}).`);
  error.code = code;
  error.status = response.status;
  return error;
}

function unreachableError() {
  return new Error(
    `Could not reach the research service at ${RESEARCH_API_BASE_URL}. Start the backend (see backend/README.md) and check that VITE_API_URL and the backend's CORS_ORIGINS are correct.`
  );
}

// question:       the text the user typed
// history:        earlier turns as [{ role: 'user' | 'assistant', text }]
// conversationId: the id the backend returned earlier (null for a new chat)
// signal:         an AbortSignal, so the Stop button can cancel the request
export async function askResearchQuestion({ question, history = [], conversationId = null, signal }) {
  const payload = {
    question,
    conversation_history: history.map((turn) => ({ role: turn.role, text: String(turn.text).slice(0, 3900) })),
  };
  if (conversationId) payload.conversation_id = conversationId;

  let response;
  try {
    response = await fetch(`${RESEARCH_API_BASE_URL}/api/research/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError') throw error;
    throw unreachableError();
  }
  if (!response.ok) throw await errorFromResponse(response);
  return normalizeResponse(await response.json());
}

// Readiness of the backend: { ready, problems, missing, ai, search }
export async function getResearchStatus({ signal } = {}) {
  let response;
  try {
    response = await fetch(`${RESEARCH_API_BASE_URL}/api/research/status`, { signal });
  } catch (error) {
    if (error?.name === 'AbortError') throw error;
    throw unreachableError();
  }
  if (!response.ok) throw await errorFromResponse(response);
  return response.json();
}
