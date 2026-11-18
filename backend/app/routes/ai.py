"""Per-event AI insights and the optional batch enrichment trigger."""
import secrets

from fastapi import APIRouter, Header, HTTPException, Query

from app.config import settings
from app.services import ai_events, llm
from app.services import events as events_service

router = APIRouter()


@router.get(
    "/events/{event_id}/insights",
    summary="One event: grounded summary, SDG links, classification reasoning",
    description=(
        "Everything is labelled. `summary.aiGenerated` tells AI text from the source's own description; SDG "
        "links come from an LLM when cached/available (`sdgMethod: llm`) and from keyword rules otherwise. "
        "A link to a goal means the topic is related, not that any country's SDG progress changed. "
        "`aiStatus`: cached | generated | disabled (no key) | unavailable | rejected. Works without an LLM. "
        "HTTP 404 for an unknown event id."
    ),
)
def event_insights(event_id: str):
    event = next((e for e in events_service.get_events() if e["id"] == event_id), None)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return ai_events.event_insights(event)


@router.post(
    "/events/enrich",
    summary="Pre-compute AI labels for the newest, most severe events (optional)",
    description=(
        "Sends up to `limit` not-yet-processed events to the LLM in small batches; results are cached, so "
        "each article is only ever sent once. Cost is bounded by `LLM_MAX_CALLS_PER_HOUR`. If `ADMIN_TOKEN` "
        "is set, the header `X-Admin-Token` is required. Without an LLM key it reports `disabled`."
    ),
)
def enrich(limit: int = Query(20, ge=1, le=100), x_admin_token: str | None = Header(None)):
    if settings.admin_token and not secrets.compare_digest(x_admin_token or "", settings.admin_token):
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Token")
    stats = ai_events.enrich_events(events_service.get_events(), limit=limit)
    events_service.clear_cache()  # so the next feed request shows the new labels
    return {**stats, "llmConfigured": llm.is_configured()}
