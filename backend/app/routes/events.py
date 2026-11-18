"""Global event feed endpoints."""
from fastapi import APIRouter, HTTPException, Query, Response

from app.models.events import EventOut, SourceStatus
from app.services import event_sources, events as events_service
from app.services.classifier import CATEGORIES, SEVERITY_LEVELS, normalize_category, normalize_severity

router = APIRouter()


def _parse_list(raw: str | None, normalizer, allowed: tuple[str, ...], label: str) -> set[str] | None:
    """Parse 'A,B' into a validated set. Unknown values give HTTP 422."""
    if raw is None or raw.strip() == "":
        return None
    values: set[str] = set()
    for part in raw.split(","):
        if not part.strip():
            continue
        value = normalizer(part)
        if value is None:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown {label} '{part.strip()}'. Allowed: {', '.join(allowed)}.",
            )
        values.add(value)
    return values or None


@router.get(
    "/events",
    response_model=list[EventOut],
    summary="Global event feed",
    description=(
        "Real articles from UN News and GDELT, de-duplicated and sorted newest first. "
        "Category and severity are assigned by transparent rules (see `classification`). "
        "Events whose country cannot be determined reliably have `countryId: null` (global/unknown). "
        "The response body is a plain array; the total number of matches is in the `X-Total-Count` header. "
        "If a source is down, the others still answer; see `/api/events/status`."
    ),
)
def list_events(
    response: Response,
    limit: int = Query(100, ge=1, le=500, description="Page size."),
    offset: int = Query(0, ge=0, description="Number of matching events to skip."),
    category: str | None = Query(None, description=f"Comma-separated. One or more of: {', '.join(CATEGORIES)}."),
    severity: str | None = Query(None, description="Comma-separated exact levels: low, moderate (or medium), high, critical."),
    min_severity: str | None = Query(None, description="Minimum level: low, moderate (or medium), high, critical."),
    country: str | None = Query(None, description="ISO alpha-2 or alpha-3 code. Matches only events with a reliable country."),
):
    categories = _parse_list(category, normalize_category, CATEGORIES, "category")
    severities = _parse_list(severity, normalize_severity, SEVERITY_LEVELS, "severity")
    minimum = None
    if min_severity:
        minimum = normalize_severity(min_severity)
        if minimum is None:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown min_severity '{min_severity}'. Allowed: {', '.join(SEVERITY_LEVELS)}.",
            )

    matching = events_service.filter_events(
        events_service.get_events(),
        categories=categories,
        severities=severities,
        min_severity=minimum,
        country=country,
    )
    response.headers["X-Total-Count"] = str(len(matching))
    return matching[offset : offset + limit]


@router.get(
    "/events/status",
    response_model=list[SourceStatus],
    summary="Health of each event source",
    description="Shows whether UN News and GDELT are currently working, rate-limited or failing, and how long until a failing source is tried again.",
)
def events_status():
    return event_sources.get_source_status()
