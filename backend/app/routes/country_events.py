"""Events linked to one country (used when a country is selected on the map)."""
from fastapi import APIRouter, HTTPException, Query, Response

from app.models.events import CountryEventsOut
from app.routes import filters
from app.services import country_data, events as events_service
from app.services.classifier import CATEGORIES

router = APIRouter()

NOTE = (
    "Only events whose own wording ties them to this country are listed (headline or lead sentence, "
    "see each event's `location.evidence`). Events that mention several countries without a clear "
    "place, name no country, or are global are NOT included, so the list can be shorter than the "
    "real news about the country. The publisher's country is never used."
)


@router.get(
    "/countries/{country_code}/events",
    response_model=CountryEventsOut,
    summary="Events linked to one country",
    description=(
        "Events whose article text reliably places them in this country. Accepts ISO alpha-2 or "
        "alpha-3. HTTP 404 for an unknown country. A known country with no linked events answers "
        "200 with `total: 0` and an empty list. Newest first. Same filters as `/api/events`, plus "
        "`min_confidence` (`medium` includes everything mapped; `high` keeps only headline-prefix / "
        "place-word matches). The total is also in the `X-Total-Count` header."
    ),
)
def get_country_events(
    country_code: str,
    response: Response,
    limit: int = Query(50, ge=1, le=200, description="Page size."),
    offset: int = Query(0, ge=0, description="Number of matching events to skip."),
    category: str | None = Query(None, description=f"Comma-separated. One or more of: {', '.join(CATEGORIES)}."),
    severity: str | None = Query(None, description="Comma-separated exact levels: low, moderate (or medium), high, critical."),
    min_severity: str | None = Query(None, description="Minimum level: low, moderate (or medium), high, critical."),
    min_confidence: str | None = Query(None, description="Minimum location confidence: medium or high."),
):
    country = country_data.find_country(country_code)
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")

    matching = events_service.filter_events(
        events_service.get_events(),
        categories=filters.parse_categories(category),
        severities=filters.parse_severities(severity),
        min_severity=filters.parse_min_severity(min_severity),
        country=country["id"],
        min_location_confidence=filters.parse_min_confidence(min_confidence),
    )
    response.headers["X-Total-Count"] = str(len(matching))
    return {
        "countryId": country["id"],
        "countryCode": country["code"],
        "countryName": country["name"],
        "total": len(matching),
        "limit": limit,
        "offset": offset,
        "events": matching[offset : offset + limit],
        "note": NOTE,
    }
