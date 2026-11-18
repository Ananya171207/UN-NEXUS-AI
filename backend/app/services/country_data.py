"""Country identity data and the /api/countries list.

Identity (names, ISO codes, region, subregion, capital, coordinates, flag) comes
from REST Countries v5. Data is cached and saved to a snapshot so the server
can continue working if the API is temporarily unavailable.

If REST Countries has never been successfully fetched, the list falls back to
pycountry (names, codes and flag emoji only).

Regions use the frontend's six regions:
Asia, Europe, Africa, North America, South America and Oceania.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time

import requests

from app.config import settings
from app.services import worldbank
from app.services.cache import MISSING, TTLCache

logger = logging.getLogger(__name__)

# REST Countries v5
REST_COUNTRIES_URL = "https://api.restcountries.com/countries/v5"
REST_LIMIT = 100
REST_FIELDS = (
    "names.common,"
    "codes.alpha_2,"
    "codes.alpha_3,"
    "region,"
    "subregion,"
    "capitals,"
    "coordinates.lat,"
    "coordinates.lng,"
    "flag.emoji,"
    "flag.url_svg,"
    "flag.url_png,"
    "classification.sovereign,"
    "classification.un_member,"
    "classification.dependency,"
    "classification.disputed"
)

MIN_PLAUSIBLE_COUNTRIES = 150

FRONTEND_REGIONS = (
    "Asia",
    "Europe",
    "Africa",
    "North America",
    "South America",
    "Oceania",
)

SOURCE_REST = "REST Countries"
SOURCE_FALLBACK = "pycountry (limited: no region, capital or coordinates)"

# Frontend field -> (World Bank indicator key, divisor, decimals)
LIST_INDICATORS = {
    "population": ("population", 1e6, 3),
    "gdp": ("gdp", 1e9, 2),
    "lifeExpectancy": ("life_expectancy", 1, 1),
    "renewableShare": ("renewable_electricity", 1, 1),
    "internetUse": ("internet_use", 1, 1),
}

_cache = TTLCache()
_lock = threading.Lock()
_retry_after = 0.0


def _monotonic() -> float:
    return time.monotonic()


def reset_state() -> None:
    global _retry_after
    _cache.clear()
    _retry_after = 0.0


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def to_frontend_region(
    continent: str | None,
    subregion: str | None,
) -> str | None:
    if continent in ("Africa", "Europe", "Asia", "Oceania"):
        return continent

    if continent == "Americas":
        return (
            "South America"
            if subregion == "South America"
            else "North America"
        )

    return None


def flag_emoji(alpha2: str | None) -> str | None:
    if not alpha2 or len(alpha2) != 2 or not alpha2.isalpha():
        return None

    return "".join(
        chr(0x1F1E6 + ord(char) - ord("A"))
        for char in alpha2.upper()
    )


def _as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _valid_code(value, expected_length: int) -> bool:
    """Check that an ISO code has the expected length."""
    return (
        isinstance(value, str)
        and len(value.strip()) == expected_length
    )


def _normalise_v3_country(raw: dict) -> dict | None:
    """Support the previous REST Countries v3 response format."""
    alpha2 = raw.get("cca2")
    alpha3 = raw.get("cca3")

    name_field = raw.get("name")
    name = (
        name_field
        if isinstance(name_field, str)
        else _as_dict(name_field).get("common")
    )

    if not (
        _valid_code(alpha2, 2)
        and _valid_code(alpha3, 3)
        and isinstance(name, str)
        and name.strip()
    ):
        return None

    latlng = raw.get("latlng")
    if not isinstance(latlng, list):
        latlng = []

    lat = latlng[0] if len(latlng) >= 2 else None
    lng = latlng[1] if len(latlng) >= 2 else None

    if not (
        isinstance(lat, (int, float))
        and isinstance(lng, (int, float))
    ):
        lat = lng = None

    capitals = raw.get("capital")

    if isinstance(capitals, str):
        capital = capitals or None
    elif isinstance(capitals, list) and capitals:
        capital = (
            capitals[0]
            if isinstance(capitals[0], str)
            else None
        )
    else:
        capital = None

    flags = raw.get("flags")

    if isinstance(flags, str):
        flag = flags
    else:
        flag_data = _as_dict(flags)
        flag = flag_data.get("svg") or flag_data.get("png")

    if not isinstance(flag, str):
        flag = None

    continent = raw.get("region")
    if not isinstance(continent, str):
        continent = None

    subregion = raw.get("subregion")
    if not isinstance(subregion, str):
        subregion = None

    emoji = raw.get("flag")
    if not isinstance(emoji, str) or len(emoji) > 8:
        emoji = None

    return {
        "id": alpha2.upper(),
        "code": alpha3.upper(),
        "name": name.strip(),
        "region": to_frontend_region(continent, subregion),
        "subregion": subregion,
        "capital": capital,
        "position": [lat, lng] if lat is not None else None,
        "latitude": lat,
        "longitude": lng,
        "flag": flag,
        "flagEmoji": emoji or flag_emoji(alpha2),
        "independent": raw.get("independent", True) is not False,
        "metadataSource": SOURCE_REST,
    }


def _normalise_v5_country(raw: dict) -> dict | None:
    """Normalise the REST Countries v5 response format."""
    names = _as_dict(raw.get("names"))
    codes = _as_dict(raw.get("codes"))
    classification = _as_dict(raw.get("classification"))

    alpha2 = codes.get("alpha_2")
    alpha3 = codes.get("alpha_3")
    name = names.get("common")

    if not (
        _valid_code(alpha2, 2)
        and _valid_code(alpha3, 3)
        and isinstance(name, str)
        and name.strip()
    ):
        return None

    # A sovereign state that is not a dependency is treated as independent.
    sovereign = classification.get("sovereign") is True
    dependency = classification.get("dependency") is True
    independent = sovereign and not dependency

    # Coordinates
    coordinates = _as_dict(raw.get("coordinates"))
    lat = coordinates.get("lat")
    lng = coordinates.get("lng")

    if not (
        isinstance(lat, (int, float))
        and isinstance(lng, (int, float))
    ):
        lat = lng = None

    # Capital: prefer the capital explicitly marked as primary.
    capitals = raw.get("capitals")
    capital = None

    if isinstance(capitals, list):
        valid_capitals = [
            item
            for item in capitals
            if isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and item.get("name").strip()
        ]

        primary_capitals = [
            item
            for item in valid_capitals
            if _as_dict(item.get("attributes")).get("primary") is True
        ]

        selected = (
            primary_capitals[0]
            if primary_capitals
            else valid_capitals[0]
            if valid_capitals
            else None
        )

        if selected:
            capital = selected["name"].strip()

    # Region and subregion
    continent = raw.get("region")
    if not isinstance(continent, str):
        continent = None

    subregion = raw.get("subregion")
    if not isinstance(subregion, str):
        subregion = None

    # Flag information
    flag_data = _as_dict(raw.get("flag"))
    flag = flag_data.get("url_svg") or flag_data.get("url_png")

    if not isinstance(flag, str):
        flag = None

    emoji = flag_data.get("emoji")
    if not isinstance(emoji, str) or len(emoji) > 8:
        emoji = None

    return {
        "id": alpha2.upper(),
        "code": alpha3.upper(),
        "name": name.strip(),
        "region": to_frontend_region(continent, subregion),
        "subregion": subregion,
        "capital": capital,
        "position": [lat, lng] if lat is not None else None,
        "latitude": lat,
        "longitude": lng,
        "flag": flag,
        "flagEmoji": emoji or flag_emoji(alpha2),
        "independent": independent,
        "metadataSource": SOURCE_REST,
    }


def normalize_rest_country(raw) -> dict | None:
    """Normalise either v3 or v5 REST Countries records.

    Keeps backward compatibility with existing v3 fixtures and tests.
    """
    if not isinstance(raw, dict):
        return None

    if "codes" in raw or "names" in raw:
        return _normalise_v5_country(raw)

    return _normalise_v3_country(raw)


# ---------------------------------------------------------------------------
# Loading metadata: network -> memory -> snapshot file -> pycountry
# ---------------------------------------------------------------------------

def _write_snapshot(countries: list[dict]) -> None:
    try:
        path = settings.countries_snapshot_path
        directory = os.path.dirname(path)

        if directory:
            os.makedirs(directory, exist_ok=True)

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(countries, handle, ensure_ascii=False)

    except OSError as error:
        logger.warning("Could not save country snapshot: %s", error)


def _read_snapshot() -> list[dict] | None:
    try:
        with open(
            settings.countries_snapshot_path,
            encoding="utf-8",
        ) as handle:
            data = json.load(handle)

        if (
            isinstance(data, list)
            and len(data) >= MIN_PLAUSIBLE_COUNTRIES
        ):
            return data

        return None

    except (OSError, ValueError):
        return None


def _pycountry_fallback() -> list[dict]:
    import pycountry

    countries = []

    for country in pycountry.countries:
        countries.append({
            "id": country.alpha_2,
            "code": country.alpha_3,
            "name": country.name,
            "region": None,
            "subregion": None,
            "capital": None,
            "position": None,
            "latitude": None,
            "longitude": None,
            "flag": None,
            "flagEmoji": flag_emoji(country.alpha_2),
            "independent": True,
            "metadataSource": SOURCE_FALLBACK,
        })

    return sorted(countries, key=lambda country: country["name"])


def _fetch_rest_countries() -> list[dict]:
    """Fetch all REST Countries v5 pages and normalise the records."""
    api_key = getattr(settings, "rest_countries_api_key", "")

    if not api_key:
        raise ValueError(
            "REST_COUNTRIES_API_KEY is not configured"
        )

    headers = {
        "User-Agent": settings.user_agent,
        "Authorization": f"Bearer {api_key}",
    }

    countries = []
    offset = 0

    while True:
        params = {
            "limit": REST_LIMIT,
            "offset": offset,
            "response_fields": REST_FIELDS,
        }

        response = requests.get(
            REST_COUNTRIES_URL,
            params=params,
            timeout=settings.countries_timeout,
            headers=headers,
        )

        response.raise_for_status()
        payload = response.json()

        if not isinstance(payload, dict):
            raise ValueError(
                "Expected a REST Countries v5 response object, "
                f"got {type(payload).__name__}: {str(payload)[:200]}"
            )

        data = payload.get("data")

        if not isinstance(data, dict):
            raise ValueError(
                "REST Countries v5 response is missing its data object: "
                f"{str(payload)[:200]}"
            )

        objects = data.get("objects")

        if not isinstance(objects, list):
            message = (
                payload.get("message")
                or data.get("message")
                or payload.get("errors")
                or payload
            )
            raise ValueError(
                "REST Countries v5 response is missing a valid "
                f"data.objects list: {str(message)[:200]}"
            )

        page_countries = [
            country
            for country in (
                normalize_rest_country(item)
                for item in objects
            )
            if country is not None and country["independent"]
        ]

        countries.extend(page_countries)

        meta = _as_dict(data.get("meta"))

        # The API supplies `more` to indicate whether another page exists.
        more = meta.get("more") is True

        if not more:
            break

        count = meta.get("count")

        if not isinstance(count, int) or count <= 0:
            count = len(objects)

        if count <= 0:
            break

        next_offset = offset + count

        # Defensive check to prevent an infinite pagination loop.
        if next_offset <= offset:
            raise ValueError(
                "REST Countries v5 returned invalid pagination metadata"
            )

        offset = next_offset

    if len(countries) < MIN_PLAUSIBLE_COUNTRIES:
        raise ValueError(
            f"Only {len(countries)} independent countries returned; "
            f"expected at least {MIN_PLAUSIBLE_COUNTRIES}"
        )

    return sorted(countries, key=lambda country: country["name"])


def load_metadata() -> list[dict]:
    """Return country metadata using the best available source.

    This function never raises. It tries the network first, then stale
    memory cache, then the snapshot file, and finally pycountry.
    """
    global _retry_after

    cached = _cache.get(
        "countries",
        settings.countries_cache_seconds,
    )

    if cached is not MISSING:
        return cached

    with _lock:
        cached = _cache.get(
            "countries",
            settings.countries_cache_seconds,
        )

        if cached is not MISSING:
            return cached

        if _monotonic() >= _retry_after:
            try:
                countries = _fetch_rest_countries()

                _cache.set("countries", countries)
                _write_snapshot(countries)

                return countries

            except Exception as error:
                _retry_after = (
                    _monotonic()
                    + settings.countries_retry_seconds
                )

                logger.warning(
                    "REST Countries unavailable (%s: %s). "
                    "Retrying in %ss.",
                    type(error).__name__,
                    error,
                    settings.countries_retry_seconds,
                    exc_info=True,
                )

        stale = _cache.get_stale("countries")

        if stale is not MISSING:
            return stale

        snapshot = _read_snapshot()

        if snapshot is not None:
            return snapshot

        fallback = _cache.get_stale("fallback")

        if fallback is MISSING:
            fallback = _pycountry_fallback()
            _cache.set("fallback", fallback)

        return fallback


def find_country(code: str) -> dict | None:
    """Look up a country by ISO alpha-2 or alpha-3 code."""
    key = (code or "").strip().upper()

    if len(key) not in (2, 3) or not key.isalpha():
        return None

    for country in load_metadata():
        if key in (country["id"], country["code"]):
            return country

    return None


# ---------------------------------------------------------------------------
# The /api/countries list (frontend shape)
# ---------------------------------------------------------------------------

def _matches(country: dict, query: str) -> bool:
    q = query.strip().lower()

    return (
        q in country["name"].lower()
        or q == country["id"].lower()
        or q == country["code"].lower()
    )


def _rank(country: dict, query: str) -> int:
    """0 = exact match, 1 = name starts with query, 2 = contains it."""
    q = query.strip().lower()
    name = country["name"].lower()

    if q in (
        name,
        country["id"].lower(),
        country["code"].lower(),
    ):
        return 0

    return 1 if name.startswith(q) else 2


def list_countries(
    query: str | None = None,
    region: str | None = None,
) -> tuple[list[dict], list[str]]:
    """Return countries in the frontend shape, plus data warnings.

    A missing World Bank value is null, never an estimate.
    """
    metadata = load_metadata()
    warnings: list[str] = []

    if metadata and metadata[0]["metadataSource"] == SOURCE_FALLBACK:
        warnings.append(
            "country metadata limited: REST Countries unavailable"
        )

    selected = [
        country
        for country in metadata
        if (
            not query
            or _matches(country, query)
        )
        and (
            not region
            or country["region"] == region
        )
    ]

    if query:
        selected.sort(
            key=lambda country: (
                _rank(country, query),
                country["name"],
            )
        )

    bulk_keys = sorted({
        key
        for key, _, _ in LIST_INDICATORS.values()
    })

    bulk, errors = worldbank.fetch_bulk_many(bulk_keys)

    warnings += [
        f"{key}: {message}"
        for key, message in sorted(errors.items())
    ]

    def pick(iso3: str, field: str):
        key, divisor, decimals = LIST_INDICATORS[field]
        entry = bulk.get(key, {}).get(iso3)

        if entry is None:
            return None, None

        return (
            round(entry["value"] / divisor, decimals),
            entry["year"],
        )

    result = []

    for country in selected:
        population, population_year = pick(
            country["code"],
            "population",
        )

        gdp, gdp_year = pick(
            country["code"],
            "gdp",
        )

        life, life_year = pick(
            country["code"],
            "lifeExpectancy",
        )

        renewable, renewable_year = pick(
            country["code"],
            "renewableShare",
        )

        internet, internet_year = pick(
            country["code"],
            "internetUse",
        )

        result.append({
            "id": country["id"],
            "code": country["code"],
            "name": country["name"],
            "region": country["region"],
            "subregion": country["subregion"],
            "capital": country["capital"],
            "position": country["position"],
            "latitude": country["latitude"],
            "longitude": country["longitude"],
            "flag": country["flag"],
            "flagEmoji": country["flagEmoji"],
            "populationM": population,
            "gdpB": gdp,
            "indicators": {
                "lifeExpectancy": life,
                "renewableShare": renewable,
                "internetUse": internet,
            },
            "dataYears": {
                "population": population_year,
                "gdp": gdp_year,
                "lifeExpectancy": life_year,
                "renewableShare": renewable_year,
                "internetUse": internet_year,
            },
            "metadataSource": country["metadataSource"],
        })

    return result, warnings
