"""India vs World endpoints. Thin: validation and comparison logic live in app.services.comparison."""
from fastapi import APIRouter, HTTPException, Query, Response

from app.models.comparison import ComparisonResponse, IndicatorCatalogueResponse
from app.services import comparison

router = APIRouter()


def _ascii(text: str) -> str:
    return text.encode("ascii", "replace").decode("ascii")


@router.get(
    "/compare/indicators",
    response_model=IndicatorCatalogueResponse,
    summary="India vs World indicator catalogue",
    description=(
        "Every indicator the comparison covers, grouped as economic, social and environmental. "
        "Taken from the World Bank indicator registry: key, label, unit, World Bank code and SDGs, plus how "
        "to read a difference (`direction`: higher_is_better, lower_is_better or contextual) and formatting "
        "hints for charts. Needs no upstream calls."
    ),
)
def get_indicator_catalogue():
    return comparison.get_indicator_catalogue()


@router.get(
    "/compare",
    response_model=ComparisonResponse,
    summary="Compare 2 to 5 countries (India vs World)",
    description=(
        "Compares 2 to 5 countries on the World Bank indicators of the country profile. `countries` is a "
        "comma-separated list of ISO alpha-2 or alpha-3 codes (duplicates are removed). `comparison` maps "
        "ISO alpha-3 -> indicator -> value, year, unit, source and status, and stays compatible with the original "
        "endpoint. `analytics` adds per-indicator differences from the baseline (India when selected), "
        "ordering, highest/lowest, coverage and reporting-year mismatches. There is no composite score and no overall "
        "ranking. Unavailable indicators are reported with their status, never estimated, and never fail the "
        "comparison. HTTP 400: wrong number of countries or baseline not selected; 404: unknown code; "
        "502: nothing could be loaded from the World Bank."
    ),
)
def compare_countries(
    response: Response,
    countries: str = Query(..., description="Comma-separated ISO alpha-2 or alpha-3 codes, 2 to 5. Example: IND,USA,BRA"),
    baseline: str | None = Query(None, description="Country the differences are measured from. Default: IND if selected, else the first country."),
):
    try:
        result = comparison.compare(countries, baseline)
    except comparison.InvalidRequest as error:
        raise HTTPException(status_code=400, detail=str(error))
    except comparison.UnknownCountry as error:
        raise HTTPException(status_code=404, detail=str(error))
    except comparison.NoDataAvailable as error:
        raise HTTPException(status_code=502, detail=str(error))

    if result["warnings"]:
        response.headers["X-Data-Warnings"] = _ascii("; ".join(result["warnings"]))[:1000]
    if result["dataStatus"] != "complete":
        response.headers["X-Data-Status"] = "partial: some indicators are unavailable or stale"
    return result
