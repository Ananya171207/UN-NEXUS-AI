"""Regional monitoring, dashboard summary and map markers, all from ONE event list.

Every function here takes the same already-filtered list of events, so the feed, the
regional cards, the dashboard numbers and the map can never disagree. Events are
de-duplicated by id first, so nothing is counted twice.

Definitions (also returned by the API so the frontend can show them):
  eventsShown        unique events matching the filters
  highCriticalEvents unique matching events with severity high or critical
  regionsWithEvents  distinct monitoring regions among matching events that have a reliable country
  countriesInView    countries in the country dataset inside the selected region
                     (all countries when no region is selected; 1 for a country filter)
Events with no reliable country count in eventsShown but belong to no region.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.services import locations
from app.services.classifier import SEVERITY_RANK
from app.services.regions import MONITORING_REGIONS, monitoring_region

ASSIGNMENT_RULE = (
    "An event belongs to the monitoring region of the country its own text reliably places it in "
    "(see each event's `location.evidence`). Events with no reliable country belong to no region and "
    "are reported separately. Middle East countries are counted in Middle East only, so no event is "
    "counted twice."
)

DEFINITIONS = {
    "eventsShown": "Unique events matching the current filters, including events with no reliable country.",
    "highCriticalEvents": "Unique matching events whose severity is high or critical.",
    "regionsWithEvents": "Distinct monitoring regions that contain at least one matching event with a reliable country.",
    "countriesInView": "Countries in the country dataset that fall inside the selected region (all countries when none is selected).",
}


def unique_events(events: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result = []
    for event in events:
        if event["id"] in seen:
            continue
        seen.add(event["id"])
        result.append(event)
    return result


def _empty_counts() -> dict[str, int]:
    return {"critical": 0, "high": 0, "moderate": 0, "low": 0}


def _highest(counts: dict[str, int]) -> str | None:
    for level in ("critical", "high", "moderate", "low"):
        if counts[level]:
            return level
    return None


def _brief(event: dict) -> dict:
    return {
        "id": event["id"], "title": event["title"], "severity": event["severity"],
        "category": event["category"], "countryId": event.get("countryId"),
        "countryName": event.get("countryName"), "occurredAt": event["occurredAt"], "url": event.get("url"),
    }


def aggregate_regions(events: list[dict]) -> dict:
    events = unique_events(events)
    buckets = {r: {"counts": _empty_counts(), "countries": set(), "events": []} for r in MONITORING_REGIONS}
    without_region = 0
    for event in events:
        region = event.get("monitoringRegion")
        if region not in buckets:
            without_region += 1
            continue
        bucket = buckets[region]
        bucket["counts"][event["severity"]] += 1
        if event.get("countryId"):
            bucket["countries"].add(event["countryId"])
        bucket["events"].append(event)

    regions = []
    for name in MONITORING_REGIONS:
        bucket = buckets[name]
        top = sorted(bucket["events"], key=lambda e: e["occurredAt"], reverse=True)
        top.sort(key=lambda e: SEVERITY_RANK[e["severity"]], reverse=True)
        regions.append({
            "region": name,
            "total": len(bucket["events"]),
            "critical": bucket["counts"]["critical"], "high": bucket["counts"]["high"],
            "moderate": bucket["counts"]["moderate"], "low": bucket["counts"]["low"],
            "countryCount": len(bucket["countries"]),
            "countryCodes": sorted(bucket["countries"]),
            "highestSeverity": _highest(bucket["counts"]),
            "topEvents": [_brief(e) for e in top[:3]],
        })
    return {
        "regions": regions,
        "totals": {
            "events": len(events), "withRegion": len(events) - without_region, "withoutRegion": without_region,
            "regionsWithEvents": sum(1 for r in regions if r["total"]),
        },
        "assignmentRule": ASSIGNMENT_RULE,
    }


def _countries_in_view(countries: list[dict], region: str | None, country_id: str | None) -> tuple[int, list[str]]:
    warnings: list[str] = []
    if country_id:
        return (1 if any(c["id"] == country_id for c in countries) else 0), warnings
    if not region:
        return len(countries), warnings
    if countries and all(c.get("region") is None for c in countries):
        warnings.append("country metadata limited: regions unavailable, countriesInView may be 0")
    return sum(1 for c in countries if monitoring_region(c) == region), warnings


def build_summary(events: list[dict], countries: list[dict], *, region: str | None = None,
                  country_id: str | None = None, filters: dict | None = None) -> dict:
    events = unique_events(events)
    severity = _empty_counts()
    categories: dict[str, int] = {}
    regions_hit: set[str] = set()
    unmapped = 0
    for event in events:
        severity[event["severity"]] += 1
        categories[event["category"]] = categories.get(event["category"], 0) + 1
        if event.get("monitoringRegion"):
            regions_hit.add(event["monitoringRegion"])
        if not event.get("countryId"):
            unmapped += 1
    in_view, warnings = _countries_in_view(countries, region, country_id)
    return {
        "countriesInView": {"value": in_view, "of": len(countries)},
        "eventsShown": len(events),
        "highCriticalEvents": severity["critical"] + severity["high"],
        "regionsWithEvents": {"value": len(regions_hit), "of": len(MONITORING_REGIONS)},
        "severityBreakdown": severity,
        "categoryBreakdown": dict(sorted(categories.items())),
        "unmappedEvents": unmapped,
        "filters": filters or {},
        "definitions": DEFINITIONS,
        "warnings": warnings,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def build_map(events: list[dict], countries: list[dict]) -> dict:
    """Event markers (only with verified city coordinates) + one marker per country with events."""
    events = unique_events(events)
    by_id = {c["id"]: c for c in countries}
    markers = []
    per_country: dict[str, dict] = {}
    no_country = 0
    dropped_invalid = 0
    for event in events:
        cid = event.get("countryId")
        if not cid:
            no_country += 1
            continue
        bucket = per_country.setdefault(cid, {"counts": _empty_counts(), "ids": []})
        bucket["counts"][event["severity"]] += 1
        bucket["ids"].append(event["id"])

        lat, lon = event.get("latitude"), event.get("longitude")
        if lat is None or lon is None:
            continue
        if not locations.valid_coordinates(lat, lon):
            dropped_invalid += 1  # never draw a marker from bad coordinates
            continue
        loc = event.get("location") or {}
        markers.append({
            "eventId": event["id"], "title": event["title"],
            "latitude": float(lat), "longitude": float(lon), "precision": loc.get("precision") or "city",
            "city": loc.get("city"),
            "countryId": cid, "countryCode": event.get("countryCode3"), "countryName": event.get("countryName"),
            "region": event.get("region"), "monitoringRegion": event.get("monitoringRegion"),
            "category": event["category"], "severity": event["severity"],
            "occurredAt": event["occurredAt"], "url": event.get("url"),
            "locationConfidence": loc.get("confidence"), "evidence": loc.get("evidence", []),
        })

    country_markers = []
    without_position = 0
    for cid, bucket in sorted(per_country.items()):
        country = by_id.get(cid)
        position = country.get("position") if country else None
        if not country or not position or not locations.valid_coordinates(position[0], position[1]):
            without_position += 1
            continue
        country_markers.append({
            "countryId": cid, "countryCode": country["code"], "countryName": country["name"],
            "region": country.get("region"), "monitoringRegion": monitoring_region(country),
            "latitude": position[0], "longitude": position[1],
            "coordinatesMean": "country_centre",
            "eventCount": len(bucket["ids"]), "highestSeverity": _highest(bucket["counts"]),
            "severityCounts": bucket["counts"], "eventIds": bucket["ids"],
        })
    return {
        "markers": markers,
        "countryMarkers": country_markers,
        "totals": {
            "events": len(events), "eventMarkers": len(markers),
            "eventsWithoutCoordinates": len(events) - len(markers) - no_country,
            "eventsWithoutCountry": no_country, "countriesWithoutPosition": without_position,
            "invalidCoordinatesDropped": dropped_invalid,
        },
        "note": (
            "`markers` are events with verified city-level coordinates (a named city after a place word). "
            "`countryMarkers` pin the country's CENTRE for events known only at country level; the centre is "
            "not where the event happened. Events with no reliable country appear in neither list."
        ),
    }
