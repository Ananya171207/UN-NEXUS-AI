"""India vs World: multi-country comparison built on the existing profile and World Bank services.

Nothing is fetched here that those services do not already fetch and cache:

* indicator definitions come from `worldbank.INDICATORS` (the single registry);
* values, statuses, stale-data fallback and the per-request deadline come from
  `worldbank.fetch_country_indicators`;
* identity comes from `country_data.find_country`, and the per-country shape from
  `country_profile.build_profile`.

What this module adds is request validation, bounded fan-out across countries, and
transparent per-indicator analytics (differences, ordering, coverage, year mismatches).
It never invents a value, never computes a composite score and never ranks countries overall.
"""
from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.services import country_data, country_profile, worldbank

logger = logging.getLogger(__name__)

MIN_COUNTRIES = 2
MAX_COUNTRIES = 5
MAX_RAW_CODES = 12  # cap on distinct codes in the query string, checked before any lookup
DEFAULT_BASELINE = "IND"

HIGHER = "higher_is_better"
LOWER = "lower_is_better"
CONTEXTUAL = "contextual"

CATEGORY_LABELS = {"economic": "Economic", "social": "Social development", "environmental": "Environmental"}

# One bounded pool shared by all requests. Each task blocks on the World Bank service's own
# shared pool (8 workers) and honours its per-country deadline, so total upstream concurrency
# stays bounded no matter how many comparisons are running.
_fetch_pool = ThreadPoolExecutor(max_workers=MAX_COUNTRIES, thread_name_prefix="compare")


# ---------------------------------------------------------------------------
# Errors (the route maps these to HTTP status codes)
# ---------------------------------------------------------------------------

class ComparisonError(Exception):
    pass


class InvalidRequest(ComparisonError):
    """Bad query: wrong number of countries, baseline not selected. -> HTTP 400."""


class UnknownCountry(ComparisonError):
    """One or more codes are not countries. -> HTTP 404."""

    def __init__(self, codes: list[str]):
        self.codes = codes
        super().__init__("Invalid country code: " + ", ".join(codes))


class NoDataAvailable(ComparisonError):
    """Every indicator of every country failed or is still loading. -> HTTP 502."""


# ---------------------------------------------------------------------------
# Interpretation: how a difference should be read. This is NOT a second registry:
# key, label, unit, code and SDGs all come from `worldbank.INDICATORS`; only the
# reading of the numbers lives here, because the registry has no notion of it.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Interpretation:
    direction: str
    note: str


INTERPRETATION: dict[str, Interpretation] = {
    "gdp": Interpretation(CONTEXTUAL, "Size of the economy. Says nothing about living standards or how income is shared; compare with GDP per capita and the social indicators."),
    "gdp_per_capita": Interpretation(HIGHER, "Average income per person. Higher is generally better, but an average hides how income is distributed and is not a measure of development on its own."),
    "gdp_growth": Interpretation(CONTEXTUAL, "Year-on-year change in real GDP. Volatile, and a high rate is easier from a low base, so there is no better/worse reading."),
    "population": Interpretation(CONTEXTUAL, "Number of people. Size, not a quality measure."),
    "inflation": Interpretation(CONTEXTUAL, "Neither high nor low is simply better: very high inflation and falling prices are both problems."),
    "unemployment": Interpretation(LOWER, "Lower is generally better. National definitions and survey methods differ, so small gaps are not meaningful."),
    "life_expectancy": Interpretation(HIGHER, "Years a newborn is expected to live under current mortality rates."),
    "school_enrollment": Interpretation(HIGHER, "Gross ratio, so it can exceed 100% (older or repeating students). It measures participation, not learning quality."),
    "poverty_rate": Interpretation(LOWER, "Share living below the international poverty line. Survey years are sparse and differ widely between countries, so check the reporting years."),
    "undernourishment": Interpretation(LOWER, "Share of people whose food intake is below the minimum energy requirement."),
    "drinking_water": Interpretation(HIGHER, "Share of people using water that is on premises, available when needed and free of contamination."),
    "internet_use": Interpretation(HIGHER, "Share of people who used the Internet in the last three months."),
    "co2_emissions": Interpretation(LOWER, "Lower is generally better for the climate. Per-person emissions exclude historical responsibility and emissions embedded in imports."),
    "renewable_electricity": Interpretation(HIGHER, "Share of electricity generated from renewable sources. Says nothing about total electricity use."),
    "pm25": Interpretation(LOWER, "Population-weighted mean annual exposure to fine particles. Lower is better for health."),
    "forest_area": Interpretation(CONTEXTUAL, "Natural land cover differs (deserts, grasslands, island states), so a lower share is not automatically worse."),
}

_CAN_BE_NEGATIVE = {"gdp_growth", "inflation"}


def interpretation_for(key: str) -> Interpretation:
    return INTERPRETATION.get(key, Interpretation(CONTEXTUAL, "No better/worse reading is defined for this indicator."))


def _is_percent_unit(unit: str) -> bool:
    return "%" in unit


def difference_unit(indicator: worldbank.Indicator) -> str:
    """An absolute difference between two percentages is in percentage points."""
    return "percentage points" if _is_percent_unit(indicator.unit) else indicator.unit


def _format_for(indicator: worldbank.Indicator) -> dict:
    unit = indicator.unit
    if unit.startswith("current US$"):
        return {"kind": "currency", "decimals": 0, "prefix": "$", "suffix": "", "compact": indicator.key == "gdp"}
    if unit == "people":
        return {"kind": "count", "decimals": 0, "prefix": "", "suffix": "", "compact": True}
    if _is_percent_unit(unit):
        return {"kind": "percent", "decimals": 1, "prefix": "", "suffix": "%", "compact": False}
    if unit == "years":
        return {"kind": "years", "decimals": 1, "prefix": "", "suffix": " years", "compact": False}
    if unit.startswith("t CO2e"):
        return {"kind": "tonnes_per_capita", "decimals": 2, "prefix": "", "suffix": " t", "compact": False}
    if "µg" in unit:
        return {"kind": "concentration", "decimals": 1, "prefix": "", "suffix": " µg/m³", "compact": False}
    return {"kind": "number", "decimals": 2, "prefix": "", "suffix": "", "compact": False}


# ---------------------------------------------------------------------------
# Indicator catalogue
# ---------------------------------------------------------------------------

def indicator_metadata(indicator: worldbank.Indicator) -> dict:
    reading = interpretation_for(indicator.key)
    return {
        "key": indicator.key,
        "label": indicator.label,
        "unit": indicator.unit,
        "category": indicator.group,
        "worldBankCode": indicator.code,
        "sdgs": list(indicator.sdgs),
        "source": worldbank.SOURCE_NAME,
        "direction": reading.direction,
        "interpretation": reading.note,
        "differenceUnit": difference_unit(indicator),
        "format": _format_for(indicator),
        "chart": {
            "axisLabel": f"{indicator.label} ({indicator.unit})",
            "canBeNegative": indicator.key in _CAN_BE_NEGATIVE,
            "recommendedChart": "bar",
        },
    }


def get_indicator_catalogue() -> dict:
    items = [indicator_metadata(i) for i in worldbank.INDICATORS]
    categories = []
    for group in country_profile.GROUPS:
        keys = [i["key"] for i in items if i["category"] == group]
        if keys:
            categories.append({"id": group, "label": CATEGORY_LABELS.get(group, group.title()), "indicatorKeys": keys})
    return {"source": worldbank.SOURCE_NAME, "count": len(items), "categories": categories, "indicators": items}


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------

def parse_codes(raw: str | None) -> list[str]:
    """'in, usa,IN,' -> ['IN', 'USA']: trimmed, upper-cased, empty items and repeats removed (order kept)."""
    tokens = [part.strip().upper() for part in (raw or "").split(",")]
    return list(dict.fromkeys(t for t in tokens if t))


def _count_message(found: int | None = None) -> str:
    base = f"Please provide between {MIN_COUNTRIES} and {MAX_COUNTRIES} countries"
    return base if found is None else f"{base} (got {found} distinct)"


def resolve_countries(raw: str | None) -> list[dict]:
    """Validated country records (alpha-2 and alpha-3 both accepted), unique, in request order."""
    tokens = parse_codes(raw)
    if len(tokens) < MIN_COUNTRIES or len(tokens) > MAX_RAW_CODES:
        raise InvalidRequest(_count_message(len(tokens)))

    resolved: list[dict] = []
    invalid: list[str] = []
    for token in tokens:
        country = country_data.find_country(token)
        if country is None:
            invalid.append(token)
        else:
            resolved.append(country)
    if invalid:
        raise UnknownCountry(invalid)

    unique = list({c["code"]: c for c in resolved}.values())  # "IN" and "IND" are the same country
    if not (MIN_COUNTRIES <= len(unique) <= MAX_COUNTRIES):
        raise InvalidRequest(_count_message(len(unique)))
    return unique


def resolve_baseline(requested: str | None, countries: list[dict]) -> tuple[dict, str]:
    """India when selected, else the first country; an explicit choice must be one of the selection."""
    if requested and requested.strip():
        country = country_data.find_country(requested)
        if country is None:
            raise UnknownCountry([requested.strip().upper()])
        match = next((c for c in countries if c["code"] == country["code"]), None)
        if match is None:
            raise InvalidRequest(f"Baseline {country['code']} must be one of the compared countries.")
        return match, "requested"
    india = next((c for c in countries if c["code"] == DEFAULT_BASELINE), None)
    if india is not None:
        return india, "default_india"
    return countries[0], "first_country"


# ---------------------------------------------------------------------------
# Fetching (reuses the World Bank service's cache, stale fallback and deadline)
# ---------------------------------------------------------------------------

def _complete(results: dict[str, dict], reason: str) -> dict[str, dict]:
    """Registry order, registry keys only; an indicator the data service did not return is reported, not dropped."""
    complete = {}
    for indicator in worldbank.INDICATORS:
        complete[indicator.key] = results.get(indicator.key) or worldbank._result(indicator, "error", error=reason)
    return complete


def _sanitise(entry: dict) -> dict:
    """An "available" entry whose value is not a finite number becomes an error, with the reason.

    Guards the response (a NaN cannot be encoded as JSON, and a string must not be coerced into a
    number) and keeps `status` truthful. The World Bank service does not produce such values; this
    protects against a malformed upstream payload.
    """
    if entry.get("status") == "available" and not _is_number(entry.get("value")):
        return {**entry, "value": None, "status": "error",
                "error": f"Received an invalid value ({type(entry.get('value')).__name__}); it was ignored."}
    return entry


def fetch_all(countries: list[dict]) -> dict[str, dict[str, dict]]:
    """Indicator results per country. Countries are fetched concurrently (at most MAX_COUNTRIES at a time)."""
    futures = [(c["code"], _fetch_pool.submit(worldbank.fetch_country_indicators, c["code"])) for c in countries]
    fetched: dict[str, dict[str, dict]] = {}
    for code, future in futures:
        try:
            results = future.result()
            reason = "Indicator was not returned by the data service."
        except Exception as error:  # fetch_country_indicators should not raise; one country must not sink the rest
            logger.exception("Unexpected failure fetching indicators for %s", code)
            results, reason = {}, f"{type(error).__name__}: {error}"
        fetched[code] = {key: _sanitise(entry) for key, entry in _complete(results or {}, reason).items()}
    return fetched


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _unusable_reason(entry: dict, indicator: worldbank.Indicator) -> str | None:
    """None when the value can be compared; otherwise why it cannot."""
    status = entry.get("status")
    if status != "available":
        return status if status in ("no_data", "error", "pending") else "error"
    if not _is_number(entry.get("value")):
        return "invalid_value"
    if entry.get("unit") != indicator.unit:
        return "unit_mismatch"  # never compare values that are not in the registry's unit
    return None


def _year(value) -> int | None:
    return int(value) if isinstance(value, str) and value.isdigit() else None


def _tidy(number: float | int) -> float | int:
    return round(number, 6) if isinstance(number, float) else number


def _competition_ranks(pairs: list[tuple[str, float | int]], descending: bool) -> dict[str, int]:
    ranks: dict[str, int] = {}
    previous, rank = None, 0
    for position, (code, value) in enumerate(sorted(pairs, key=lambda p: (p[1], p[0]), reverse=descending), start=1):
        if value != previous:
            rank, previous = position, value
        ranks[code] = rank
    return ranks


def analyse_indicator(indicator: worldbank.Indicator, entries: dict[str, dict], baseline: str) -> dict:
    """Transparent comparison of one indicator across the selected countries.

    `entries` maps country code -> indicator entry, in request order. Missing or invalid values are
    kept in `values` (with a reason) and excluded from every calculation.
    """
    reading = interpretation_for(indicator.key)
    codes = list(entries)
    reasons = {code: _unusable_reason(entry, indicator) for code, entry in entries.items()}
    usable = [code for code in codes if reasons[code] is None]
    values = {code: entries[code]["value"] for code in usable}
    notes: list[str] = []

    base_entry = entries.get(baseline, {})
    base_value = values.get(baseline)
    base_year = _year(base_entry.get("year")) if base_value is not None else None

    value_ranks = _competition_ranks([(c, values[c]) for c in usable], descending=True)
    performance_ranks: dict[str, int] = {}
    if reading.direction in (HIGHER, LOWER):
        performance_ranks = _competition_ranks([(c, values[c]) for c in usable], descending=reading.direction == HIGHER)

    rows = []
    for code in codes:
        entry = entries[code]
        row = {
            "country": code, "value": entry.get("value") if reasons[code] is None else None, "year": entry.get("year"),
            "status": entry.get("status"), "stale": bool(entry.get("stale")),
            "usable": reasons[code] is None, "reason": reasons[code], "isBaseline": code == baseline,
            "absoluteDifference": None, "percentDifference": None, "percentDifferenceNote": None,
            "yearDifference": None, "comparedWithBaseline": None, "performanceVsBaseline": None,
            "valueRank": value_ranks.get(code), "performanceRank": performance_ranks.get(code),
        }
        if code != baseline:
            if reasons[code] is not None:
                row["percentDifferenceNote"] = "value_unavailable"
            elif base_value is None:
                row["percentDifferenceNote"] = "baseline_unavailable"
            else:
                value = values[code]
                row["absoluteDifference"] = _tidy(value - base_value)
                row["comparedWithBaseline"] = "higher" if value > base_value else "lower" if value < base_value else "equal"
                if reading.direction in (HIGHER, LOWER):
                    if value == base_value:
                        row["performanceVsBaseline"] = "same"
                    else:
                        row["performanceVsBaseline"] = "better" if (value > base_value) == (reading.direction == HIGHER) else "worse"
                if base_value == 0:
                    row["percentDifferenceNote"] = "baseline_is_zero"  # never divide by zero
                else:
                    # |baseline| in the denominator keeps the sign meaning "above / below the baseline" for negative baselines.
                    row["percentDifference"] = round((value - base_value) / abs(base_value) * 100, 2)
                year, other_base = _year(entry.get("year")), base_year
                if year is not None and other_base is not None:
                    row["yearDifference"] = year - other_base
        rows.append(row)

    ordered = sorted(usable, key=lambda c: (-values[c], c))
    best_to_worst = None
    if reading.direction == HIGHER:
        best_to_worst = ordered
    elif reading.direction == LOWER:
        best_to_worst = sorted(usable, key=lambda c: (values[c], c))

    highest = lowest = None
    comparable = len(usable) >= 2
    if comparable:
        top, bottom = ordered[0], ordered[-1]
        highest = {"country": top, "value": values[top], "year": entries[top].get("year"),
                   "tie": sum(1 for c in usable if values[c] == values[top]) > 1}
        lowest = {"country": bottom, "value": values[bottom], "year": entries[bottom].get("year"),
                  "tie": sum(1 for c in usable if values[c] == values[bottom]) > 1}
    else:
        notes.append("Fewer than two selected countries have a usable value, so nothing can be compared.")

    years = {code: entries[code].get("year") if reasons[code] is None else None for code in codes}
    years_differ = len({years[c] for c in usable}) > 1
    if years_differ:
        notes.append("Reporting years differ between countries; differences mix different years.")
    if base_value is None and comparable:
        notes.append("The baseline country has no usable value, so no differences from it are calculated.")
    if base_value == 0:
        notes.append("The baseline value is zero, so percentage differences are not calculated.")
    if any(row["stale"] for row in rows):
        notes.append("At least one value is a stale cached value (the latest refresh failed).")

    missing = [{"country": c, "status": entries[c].get("status"), "reason": reasons[c], "detail": entries[c].get("error")}
               for c in codes if reasons[c] is not None]
    return {
        "key": indicator.key, "label": indicator.label, "unit": indicator.unit, "group": indicator.group,
        "direction": reading.direction, "differenceUnit": difference_unit(indicator),
        "comparable": comparable,
        "baseline": {"country": baseline, "value": base_value, "year": base_entry.get("year") if base_value is not None else None,
                     "available": base_value is not None},
        "values": rows, "orderedByValue": ordered, "orderedBestToWorst": best_to_worst,
        "highest": highest, "lowest": lowest,
        "coverage": {"requested": len(codes), "available": len(usable),
                     "ratio": round(len(usable) / len(codes), 4) if codes else 0.0,
                     "countriesWithData": usable, "countriesMissing": missing},
        "years": years, "yearsDiffer": years_differ, "notes": notes,
    }


# ---------------------------------------------------------------------------
# Data quality and warnings
# ---------------------------------------------------------------------------

def build_data_quality(profile: dict) -> dict:
    indicators = profile["indicators"]
    counts = {s: sum(1 for v in indicators.values() if v["status"] == s) for s in ("available", "no_data", "error", "pending")}
    stale = [k for k, v in indicators.items() if v["stale"]]
    total = len(indicators)
    return {
        "total": total, "available": counts["available"], "noData": counts["no_data"], "error": counts["error"],
        "pending": counts["pending"], "stale": len(stale),
        "coverage": round(counts["available"] / total, 4) if total else 0.0,
        "complete": counts["available"] == total and not stale,
        "staleIndicators": stale,
        "missing": profile["missing"],  # {key, status, reason}, straight from the profile
    }


def _keys(keys: list[str], limit: int = 6) -> str:
    return ", ".join(keys[:limit]) + (f" and {len(keys) - limit} more" if len(keys) > limit else "")


def build_warnings(codes: list[str], profiles: dict[str, dict], analytics: dict[str, dict],
                   baseline: dict, basis: str) -> list[str]:
    warnings: list[str] = []
    if basis == "first_country":
        warnings.append(f"India (IND) is not among the selected countries; {baseline['code']} is used as the baseline for differences.")
    for code in codes:
        indicators = profiles[code]["indicators"]
        by_status = {s: [k for k, v in indicators.items() if v["status"] == s] for s in ("error", "pending", "no_data")}
        stale = [k for k, v in indicators.items() if v["stale"] and v["status"] == "available"]
        if len(by_status["error"]) == len(indicators):
            warnings.append(f"{code}: no indicator could be loaded from the World Bank.")
        elif by_status["error"]:
            warnings.append(f"{code}: {len(by_status['error'])} indicator(s) could not be loaded ({_keys(by_status['error'])}).")
        if by_status["pending"]:
            warnings.append(f"{code}: {len(by_status['pending'])} indicator(s) still loading ({_keys(by_status['pending'])}); retry shortly.")
        if by_status["no_data"]:
            warnings.append(f"{code}: the World Bank has no value for {_keys(by_status['no_data'])}.")
        if stale:
            warnings.append(f"{code}: showing stale cached values for {_keys(stale)} because the latest refresh failed.")
    for key, item in analytics.items():
        invalid = [(m["country"], m["reason"]) for m in item["coverage"]["countriesMissing"] if m["reason"] in ("invalid_value", "unit_mismatch")]
        for country, reason in invalid:
            warnings.append(f"{country}: {item['label']} has an unusable value ({reason}); it was excluded from the comparison.")
        if item["yearsDiffer"]:
            shown = ", ".join(f"{c} {item['years'][c]}" for c in item["coverage"]["countriesWithData"])
            warnings.append(f"Reporting years differ for {item['label']}: {shown}.")
    return warnings


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def compare(countries_raw: str | None, baseline_raw: str | None = None) -> dict:
    countries = resolve_countries(countries_raw)
    baseline_country, basis = resolve_baseline(baseline_raw, countries)
    codes = [c["code"] for c in countries]

    fetched = fetch_all(countries)
    if all(r["status"] in ("error", "pending") for results in fetched.values() for r in results.values()):
        raise NoDataAvailable("No World Bank data could be loaded yet. Retry in a few seconds.")

    profiles = {c["code"]: country_profile.build_profile(c, fetched[c["code"]]) for c in countries}

    comparison = {
        code: {key: {"key": key, **value} for key, value in profiles[code]["indicators"].items()}
        for code in codes
    }
    analytics = {
        indicator.key: analyse_indicator(
            indicator, {code: comparison[code][indicator.key] for code in codes}, baseline_country["code"])
        for indicator in worldbank.INDICATORS
    }
    data_quality = {code: build_data_quality(profiles[code]) for code in codes}
    country_metadata = {
        code: {**profiles[code]["identity"], "alpha2": profiles[code]["identity"]["id"], "alpha3": code,
               "isBaseline": code == baseline_country["code"]}
        for code in codes
    }
    return {
        "source": worldbank.SOURCE_NAME,
        "comparison": comparison,
        "countries": codes,
        "baseline": {"country": baseline_country["code"], "name": baseline_country["name"], "basis": basis},
        "countryMetadata": country_metadata,
        "indicatorMetadata": [indicator_metadata(i) for i in worldbank.INDICATORS],
        "analytics": analytics,
        "dataQuality": data_quality,
        "dataStatus": "complete" if all(q["complete"] for q in data_quality.values()) else "partial",
        "warnings": build_warnings(codes, profiles, analytics, baseline_country, basis),
        "lastUpdated": min((p["lastUpdated"] for p in profiles.values() if p["lastUpdated"]), default=None),
    }
