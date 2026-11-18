"""Global Situation Room: regional monitoring, dashboard summary and map data."""
from fastapi import APIRouter, Query

from app.models.situation import MapOut, RegionsOut, SummaryOut
from app.routes import filters
from app.services import ai_insights, country_data, monitoring
from app.services.classifier import CATEGORIES
from app.services.regions import MONITORING_REGIONS

router = APIRouter()

_CATEGORY = Query(None, description=f"Comma-separated. One or more of: {', '.join(CATEGORIES)}.")
_SEVERITY = Query(None, description="Comma-separated exact levels: low, moderate (or medium), high, critical.")
_MIN_SEVERITY = Query(None, description="Minimum level: low, moderate (or medium), high, critical.")
_REGION = Query(None, description=f"One of: {', '.join(MONITORING_REGIONS)}.")
_COUNTRY = Query(None, description="ISO alpha-2 or alpha-3 country code.")
_CONFIDENCE = Query(None, description="Minimum location confidence: medium or high.")


@router.get(
    "/events/regions",
    response_model=RegionsOut,
    summary="Regional monitoring: event counts per region",
    description=(
        "All seven regions are always returned (zero counts included). An event is counted once, in the "
        "region of the country its text reliably places it in; events with no reliable country are not "
        "assigned to any region (`totals.withoutRegion`). `moderate` is medium severity. Accepts the "
        "same filters as `/api/events`."
    ),
)
def regions(category: str | None = _CATEGORY, severity: str | None = _SEVERITY, min_severity: str | None = _MIN_SEVERITY,
            country: str | None = _COUNTRY, min_confidence: str | None = _CONFIDENCE):
    events, _ = filters.load_filtered_events(category=category, severity=severity, min_severity=min_severity,
                                             country=country, min_confidence=min_confidence)
    return monitoring.aggregate_regions(events)


@router.get(
    "/situation-room/summary",
    response_model=SummaryOut,
    summary="Dashboard summary cards",
    description=(
        "Powers the four dashboard cards, computed from the same filtered event list as the feed, regions "
        "and map. `definitions` states exactly what each number counts. Filters: category, severity, "
        "min_severity, country, region, min_confidence."
    ),
)
def summary(category: str | None = _CATEGORY, severity: str | None = _SEVERITY, min_severity: str | None = _MIN_SEVERITY,
            country: str | None = _COUNTRY, region: str | None = _REGION, min_confidence: str | None = _CONFIDENCE):
    events, applied = filters.load_filtered_events(category=category, severity=severity, min_severity=min_severity,
                                                   country=country, region=region, min_confidence=min_confidence)
    code = applied["country"]
    if code:
        found = country_data.find_country(code)
        code = found["id"] if found else code
    return monitoring.build_summary(events, country_data.load_metadata(), region=applied["region"],
                                    country_id=code, filters=applied)


@router.get(
    "/events/map",
    response_model=MapOut,
    summary="Map data: verified event markers plus per-country markers",
    description=(
        "`markers` are events with verified city-level coordinates only. `countryMarkers` pin the country's "
        "centre (`coordinatesMean: country_centre`) for events known only at country level; that is not the "
        "event's location. Events with no reliable country appear in neither list (see `totals`). Accepts the "
        "same filters as the summary."
    ),
)
def event_map(category: str | None = _CATEGORY, severity: str | None = _SEVERITY, min_severity: str | None = _MIN_SEVERITY,
              country: str | None = _COUNTRY, region: str | None = _REGION, min_confidence: str | None = _CONFIDENCE):
    events, _ = filters.load_filtered_events(category=category, severity=severity, min_severity=min_severity,
                                             country=country, region=region, min_confidence=min_confidence)
    return monitoring.build_map(events, country_data.load_metadata())


@router.get(
    "/events/regions/{region}/intelligence",
    summary="Regional intelligence: counts plus an optional, labelled AI summary",
    description=(
        "`development` is deterministic (counts and top events). `narrative` is an optional AI summary whose "
        "every point must cite event ids; it needs at least 3 events and is `disabled` without an LLM key."
    ),
)
def region_intelligence(region: str):
    name = filters.parse_region(region)  # 422 for an unknown region
    events, _ = filters.load_filtered_events(region=name)
    return ai_insights.regional_intelligence(name, events)
