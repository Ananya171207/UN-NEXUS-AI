
import logging

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
