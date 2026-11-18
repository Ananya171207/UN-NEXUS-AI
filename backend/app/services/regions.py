"""Country -> monitoring region, and how events are assigned to regions.

Seven monitoring regions (the Situation Room's regional section):
Africa, Asia, Europe, North America, South America, Oceania, Middle East.

Assignment rule (one rule, used by every endpoint):
  * An event belongs to the region of the country it is reliably linked to
    (see services/locations.py). No reliable country = no region. Nothing is guessed.
  * "Middle East" is not a UN region, so it is a curated country list below.
    Those countries are in this region ONLY (never also in Asia or Africa), so an
    event is never counted twice. Egypt and Turkey are included.
  * Every other country uses its continental region from the country dataset.

The older `region` field on countries and events (6 regions, Middle East inside
Asia/Africa) is unchanged, so existing frontend filters keep working.
"""
from __future__ import annotations

MONITORING_REGIONS: tuple[str, ...] = (
    "Africa", "Asia", "Europe", "North America", "South America", "Oceania", "Middle East",
)

# ISO alpha-2 codes.
MIDDLE_EAST: frozenset[str] = frozenset({
    "AE", "BH", "EG", "IQ", "IR", "IL", "JO", "KW", "LB", "OM", "PS", "QA", "SA", "SY", "TR", "YE",
})


def monitoring_region(country: dict | None) -> str | None:
    """Monitoring region for a country record (needs `id`; uses `region` otherwise)."""
    if not country:
        return None
    if country.get("id") in MIDDLE_EAST:
        return "Middle East"
    region = country.get("region")
    return region if region in MONITORING_REGIONS else None


def normalize_region(value: str) -> str | None:
    key = value.strip().lower()
    for region in MONITORING_REGIONS:
        if region.lower() == key:
            return region
    return None
