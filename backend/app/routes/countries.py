
import logging
import time

import pycountry
import requests
from fastapi import HTTPException
from fastapi import APIRouter, Query, Response

from app.models.countries import CountryOut
from app.services import country_data, country_profile

logger = logging.getLogger(__name__)

router = APIRouter()

def _ascii(text: str) -> str:
    return text.encode("ascii", "replace").decode("ascii")


@router.get(
    "/countries",
    response_model=list[CountryOut],
    summary="List and search countries",
    description=(
        "Every country with its identity (ISO codes, region, capital, coordinates, flag) and headline "
        "World Bank figures, in the shape the Situation Room frontend reads. "
        "`q` searches by name or ISO alpha-2/alpha-3 code. `region` filters by one of the six regions. "
        "A value that is unavailable is null, never estimated; `dataYears` gives the year of each figure. "
        "Problems with underlying data are listed in the `X-Data-Warnings` response header."
    ),
)
def get_countries(
    response: Response,
    q: str | None = Query(None, description="Name or ISO alpha-2/alpha-3 code."),
    region: str | None = Query(None, description=", ".join(country_data.FRONTEND_REGIONS)),
):
    if region and region not in country_data.FRONTEND_REGIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown region '{region}'. Allowed: {', '.join(country_data.FRONTEND_REGIONS)}.",
        )
    items, warnings = country_data.list_countries(q, region)
    if warnings:
        response.headers["X-Data-Warnings"] = _ascii("; ".join(warnings))[:1000]
    return items


@router.get(
    "/countries/{country_code}",
    summary="One country's identity",
    description="Identity data for a country by ISO alpha-2 or alpha-3 code. HTTP 404 if the code is unknown.",
)
def get_country(country_code: str):
    country = country_data.find_country(country_code)
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return country


@router.get("/countries/{country_code}/indicators/{indicator_code}")
def get_country_indicator(country_code: str, indicator_code: str):

    url = (
        f"https://api.worldbank.org/v2/country/"
        f"{country_code}/indicator/{indicator_code}"
    )

    params = {
        "format": "json",
        "per_page": 10
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        result = response.json()

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Unable to connect to World Bank API"
        )

    if not isinstance(result, list) or len(result) < 2:
        raise HTTPException(
            status_code=404,
            detail="Invalid response from World Bank API"
        )

    records = result[1]

    if not records:
        raise HTTPException(
            status_code=404,
            detail="No indicator data found"
        )

    return {
        "country": country_code.upper(),
        "indicator": indicator_code,
        "indicator_name": records[0]["indicator"]["value"],
        "data": [
            {
                "year": record["date"],
                "value": record["value"]
            }
            for record in records
            if record["value"] is not None
        ]
    }


INDICATORS = {
    "gdp_per_capita": "NY.GDP.PCAP.CD",
    "population": "SP.POP.TOTL",
    "life_expectancy": "SP.DYN.LE00.IN",
    "co2_emissions": "EN.GHG.CO2.PC.CE.AR5",
    "school_enrollment": "SE.SEC.ENRR"
}

PROFILE_CACHE = {}
CACHE_DURATION = 3600  # 1 hour


def fetch_latest_indicator(country_code, indicator_code):

    url = (
        f"https://api.worldbank.org/v2/country/"
        f"{country_code}/indicator/{indicator_code}"
    )

    params = {
        "format": "json",
        "per_page": 10
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()

    result = response.json()

    if not isinstance(result, list) or len(result) < 2:
        logger.warning(
            "Invalid World Bank response for indicator %s: %r", indicator_code, result
        )

        raise HTTPException(
           status_code=502,
           detail=f"Invalid response for indicator: {indicator_code}"
        )

    records = result[1] or []

    latest = next(
        (record for record in records if record["value"] is not None),
        None
    )

    if latest is None:
        return {
            "year": None,
            "value": None
        }

    return {
        "year": latest["date"],
        "value": latest["value"]
    }


def validate_country_code(country_code: str):

    country_code = country_code.upper()

    country = pycountry.countries.get(alpha_3=country_code)

    if country is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid country code"
        )

    return country_code


@router.get(
    "/countries/{country_code}/profile",
    summary="Country profile",
    description=(
        "Identity plus up to 16 World Bank indicators grouped as economic, social and environmental. "
        "Each indicator carries value, year, unit, source, status (available / no_data / error), "
        "and when it was fetched; `missing` lists everything unavailable and why. "
        "Indicators load in parallel and fail independently, so one slow indicator no longer breaks the profile. "
        "Accepts ISO alpha-2 or alpha-3. HTTP 404 for an unknown code; HTTP 502 only if every indicator failed."
    ),
)
def get_country_profile(country_code: str):
    try:
        return country_profile.get_profile(country_code)
    except country_profile.CountryNotFound:
        raise HTTPException(status_code=404, detail="Invalid country code")
    except country_profile.NoDataAvailable as error:
        raise HTTPException(status_code=502, detail=str(error))


@router.get("/compare")
def compare_countries(countries: str):

    # Convert comma-separated country codes into a list
    country_codes = [
        code.strip().upper()
        for code in countries.split(",")
    ]

    # Remove duplicates
    country_codes = list(dict.fromkeys(country_codes))

    # Require at least 2 and at most 5 countries
    if len(country_codes) < 2 or len(country_codes) > 5:
        raise HTTPException(
            status_code=400,
            detail="Please provide between 2 and 5 countries"
        )

    comparison = {}

    try:
        for code in country_codes:

            # Validate country code
            code = validate_country_code(code)

            # Check cache first
            if code in PROFILE_CACHE:
                cached_data, cached_time = PROFILE_CACHE[code]

                if time.time() - cached_time < CACHE_DURATION:
                    profile = cached_data

                else:
                    profile = None
            else:
                profile = None

            # Fetch data if not cached
            if profile is None:

                indicators = {}

                for name, indicator_code in INDICATORS.items():
                    indicators[name] = fetch_latest_indicator(
                        code,
                        indicator_code
                    )

                profile = {
                    "country": code,
                    "source": "World Bank Open Data",
                    "indicators": indicators
                }

                PROFILE_CACHE[code] = (profile, time.time())

            comparison[code] = profile["indicators"]

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Unable to fetch comparison data from World Bank"
        )

    return {
        "source": "World Bank Open Data",
        "comparison": comparison
    }