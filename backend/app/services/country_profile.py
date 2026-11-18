"""Builds the full country profile: identity + World Bank indicators + transparency."""
from __future__ import annotations

from app.services import country_data, worldbank

GROUPS = ("economic", "social", "environmental")


class CountryNotFound(Exception):
    pass


class NoDataAvailable(Exception):
    """Every indicator failed or is still loading, and nothing was cached."""


def build_profile(country: dict, results: dict[str, dict]) -> dict:
    indicators = {
        key: {
            # `year` and `value` keep the shape the original profile endpoint returned.
            "year": r["year"], "value": r["value"],
            "label": r["label"], "unit": r["unit"], "group": r["group"],
            "source": r["source"], "sourceCode": r["sourceCode"], "indicatorName": r["indicatorName"],
            "status": r["status"], "stale": r["stale"], "error": r["error"],
            "sourceLastUpdated": r["sourceLastUpdated"], "fetchedAt": r["fetchedAt"],
        }
        for key, r in results.items()
    }
    return {
        "country": country["code"],  # alpha-3, as before
        "source": worldbank.SOURCE_NAME,
        "identity": {
            "id": country["id"], "code": country["code"], "name": country["name"],
            "region": country["region"], "subregion": country["subregion"], "capital": country["capital"],
            "latitude": country["latitude"], "longitude": country["longitude"], "position": country["position"],
            "flag": country["flag"], "flagEmoji": country["flagEmoji"],
            "metadataSource": country["metadataSource"],
        },
        "indicators": indicators,
        "groups": {g: [k for k, v in indicators.items() if v["group"] == g] for g in GROUPS},
        # Everything the profile could not show, and why (no_data = World Bank has none; error = fetch failed)
        "missing": [{"key": k, "status": v["status"], "reason": v["error"]} for k, v in indicators.items() if v["status"] != "available"],
        "lastUpdated": min((r["fetchedAt"] for r in results.values()), default=None),
    }


def get_profile(code: str) -> dict:
    country = country_data.find_country(code)
    if country is None:
        raise CountryNotFound(code)
    results = worldbank.fetch_country_indicators(country["code"])
    if results and all(r["status"] in ("error", "pending") for r in results.values()):
        raise NoDataAvailable("No World Bank data could be loaded yet. Retry in a few seconds.")
    return build_profile(country, results)
