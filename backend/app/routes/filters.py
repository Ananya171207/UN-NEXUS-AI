"""Query-parameter parsing shared by the event endpoints."""
from fastapi import HTTPException

from app.services import events as events_service
from app.services.regions import MONITORING_REGIONS, normalize_region
from app.services.classifier import CATEGORIES, SEVERITY_LEVELS, normalize_category, normalize_severity
from app.services.locations import CONFIDENCE_LEVELS


def parse_list(raw: str | None, normalizer, allowed: tuple[str, ...], label: str) -> set[str] | None:
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


def parse_categories(raw: str | None) -> set[str] | None:
    return parse_list(raw, normalize_category, CATEGORIES, "category")


def parse_severities(raw: str | None) -> set[str] | None:
    return parse_list(raw, normalize_severity, SEVERITY_LEVELS, "severity")


def parse_min_severity(raw: str | None) -> str | None:
    if not raw:
        return None
    value = normalize_severity(raw)
    if value is None:
        raise HTTPException(status_code=422, detail=f"Unknown min_severity '{raw}'. Allowed: {', '.join(SEVERITY_LEVELS)}.")
    return value


def parse_min_confidence(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip().lower()
    if value not in CONFIDENCE_LEVELS:
        raise HTTPException(status_code=422, detail=f"Unknown min_confidence '{raw}'. Allowed: {', '.join(CONFIDENCE_LEVELS)}.")
    return value


def parse_region(raw: str | None) -> str | None:
    if not raw or not raw.strip():
        return None
    value = normalize_region(raw)
    if value is None:
        raise HTTPException(status_code=422, detail=f"Unknown region '{raw}'. Allowed: {', '.join(MONITORING_REGIONS)}.")
    return value


def load_filtered_events(
    *, category: str | None = None, severity: str | None = None, min_severity: str | None = None,
    country: str | None = None, region: str | None = None, min_confidence: str | None = None,
) -> tuple[list[dict], dict]:
    """The one place the event feed, regions, summary and map get their events from.

    Returns (events, applied_filters). Same filters, same data, so the numbers always agree.
    """
    categories = parse_categories(category)
    severities = parse_severities(severity)
    min_sev = parse_min_severity(min_severity)
    monitoring = parse_region(region)
    confidence = parse_min_confidence(min_confidence)
    code = country.strip().upper() if country and country.strip() else None
    events = events_service.filter_events(
        events_service.get_events(), categories=categories, severities=severities, min_severity=min_sev,
        country=code, min_location_confidence=confidence, region=monitoring,
    )
    applied = {
        "category": sorted(categories) if categories else None, "severity": sorted(severities) if severities else None,
        "minSeverity": min_sev, "country": code, "region": monitoring, "minConfidence": confidence,
    }
    return events, applied
