"""Country SDG signals (real indicator data) and country insights (facts + optional AI note)."""
from fastapi import APIRouter, HTTPException, Query, Response

from app.models.situation import CountrySDGSignalsOut
from app.services import ai_insights, country_data, sdg, worldbank
from app.services import events as events_service

router = APIRouter()


def _country_or_404(country_code: str) -> dict:
    country = country_data.find_country(country_code)
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return country


@router.get(
    "/countries/{country_code}/sdg-signals",
    response_model=CountrySDGSignalsOut,
    summary="SDG signals: real World Bank indicator values grouped by goal",
    description=(
        "Real indicator data (value, year, unit, source) grouped under the Sustainable Development Goals "
        "they relate to. **Not** an SDG progress score: nothing is compared with targets and there is no "
        "'on track / off track'. `relation` says whether an indicator matches an official UN SDG indicator "
        "or is related context. `availability` is available | no_data | error | pending; `outdated` flags "
        "old values. HTTP 404 for an unknown country; 502 only when every indicator failed."
    ),
)
def country_sdg_signals(
    country_code: str,
    response: Response,
    sdg_numbers: str | None = Query(None, alias="sdg", description="Comma-separated goal numbers to keep, e.g. `3,7`."),
):
    country = _country_or_404(country_code)
    only: set[int] | None = None
    if sdg_numbers and sdg_numbers.strip():
        try:
            only = {int(p) for p in sdg_numbers.split(",") if p.strip()}
        except ValueError:
            raise HTTPException(status_code=422, detail="sdg must be comma-separated whole numbers, e.g. 3,7")
        if not only or any(n not in sdg.SDG_NAMES for n in only):
            raise HTTPException(status_code=422, detail="sdg numbers must be between 1 and 17")
    signals = sdg.get_signals(country, only)
    if sdg.all_unavailable(signals):
        raise HTTPException(status_code=502, detail="World Bank data could not be loaded. Try again shortly.")
    if any(s["availability"] == "pending" for g in signals["goals"] for s in g["signals"]):
        response.headers["X-Data-Status"] = "partial: some indicators still loading"
    return signals


@router.get(
    "/countries/{country_code}/insights",
    summary="Country insights: data-backed facts plus an optional, labelled AI note",
    description=(
        "`facts` are real World Bank values and recent events linked to the country (never AI). "
        "`interpretation` is an optional AI-generated note that must cite fact ids; it is dropped if it "
        "cites unknown facts or invents numbers. `interpretation.status`: ok-states are `generated` and "
        "`cached`; otherwise `disabled` (no LLM key), `unavailable`, `rejected` or `insufficient_data`. "
        "Only the latest value of each indicator exists, so no trends are described."
    ),
)
def country_insights(country_code: str):
    country = _country_or_404(country_code)
    results = worldbank.fetch_country_indicators(country["code"])
    events = events_service.filter_events(events_service.get_events(), country=country["id"])
    return ai_insights.country_insights(country, results, events)
