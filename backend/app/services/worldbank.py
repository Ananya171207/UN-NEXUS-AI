"""World Bank Open Data client.

* `INDICATORS` is the single registry of indicators. To add one, add a line
  there; the profile, the transparency fields and the SDG mapping pick it up.
* Each indicator is fetched independently and in parallel. One slow or failing
  indicator yields `status: "error"` for that indicator only; it never fails
  the whole profile.
* Statuses: "available" (value found), "no_data" (World Bank answered but has
  no value for this country), "error" (could not be fetched), "pending" (still
  loading when the request's deadline passed; it keeps loading in the background
  and will be in the cache for the next request).
* Successful results are cached for a day (the data is annual). If a refresh
  fails, the last good value is served with `stale: true`.
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from app.config import settings
from app.services.cache import MISSING, TTLCache

logger = logging.getLogger(__name__)

BASE_URL = "https://api.worldbank.org/v2"
SOURCE_NAME = "World Bank Open Data"
MAX_BULK_PAGES = 25


@dataclass(frozen=True)
class Indicator:
    key: str
    code: str
    label: str
    unit: str
    group: str  # economic | social | environmental
    sdgs: tuple[int, ...] = ()  # used by the SDG signals endpoint (next stage)


# Codes for the first five (the original profile) were already in use. The rest are
# standard World Bank codes but have NOT been confirmed live from this project yet:
# any that return nothing are reported as "no_data"/"error", never guessed.
INDICATORS: tuple[Indicator, ...] = (
    Indicator("gdp", "NY.GDP.MKTP.CD", "GDP", "current US$", "economic", (8,)),
    Indicator("gdp_per_capita", "NY.GDP.PCAP.CD", "GDP per capita", "current US$", "economic", (8,)),
    Indicator("gdp_growth", "NY.GDP.MKTP.KD.ZG", "GDP growth", "annual %", "economic", (8,)),
    Indicator("population", "SP.POP.TOTL", "Population", "people", "economic"),
    Indicator("inflation", "FP.CPI.TOTL.ZG", "Inflation, consumer prices", "annual %", "economic", (8,)),
    Indicator("unemployment", "SL.UEM.TOTL.ZS", "Unemployment", "% of labour force", "economic", (8,)),
    Indicator("life_expectancy", "SP.DYN.LE00.IN", "Life expectancy at birth", "years", "social", (3,)),
    Indicator("school_enrollment", "SE.SEC.ENRR", "Secondary school enrollment", "% gross", "social", (4,)),
    Indicator("poverty_rate", "SI.POV.DDAY", "Poverty headcount ratio (international poverty line)", "% of population", "social", (1,)),
    Indicator("undernourishment", "SN.ITK.DEFC.ZS", "Prevalence of undernourishment", "% of population", "social", (2,)),
    Indicator("drinking_water", "SH.H2O.SMDW.ZS", "Safely managed drinking water", "% of population", "social", (6,)),
    Indicator("internet_use", "IT.NET.USER.ZS", "Individuals using the Internet", "% of population", "social", (9,)),
    Indicator("co2_emissions", "EN.GHG.CO2.PC.CE.AR5", "CO2 emissions per capita (excl. LULUCF)", "t CO2e per capita", "environmental", (13,)),
    Indicator("renewable_electricity", "EG.ELC.RNEW.ZS", "Renewable electricity output", "% of total electricity output", "environmental", (7,)),
    Indicator("pm25", "EN.ATM.PM25.MC.M3", "PM2.5 air pollution, mean annual exposure", "µg/m³", "environmental", (11,)),
    Indicator("forest_area", "AG.LND.FRST.ZS", "Forest area", "% of land area", "environmental", (15,)),
)
BY_KEY = {i.key: i for i in INDICATORS}

_cache = TTLCache()
_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="worldbank")  # shared, bounds total concurrency
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(key: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def reset_cache() -> None:
    _cache.clear()


class WorldBankError(Exception):
    """The World Bank could not be reached or answered with something unusable."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_json(url: str, params: dict):
    """GET with timeout and limited retries (timeouts, connection errors, 5xx only)."""
    attempts = settings.worldbank_retries + 1
    last: object = "unknown error"
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(
                url, params=params, timeout=settings.worldbank_timeout,
                headers={"User-Agent": settings.user_agent},
            )
        except (requests.Timeout, requests.ConnectionError) as error:
            last = f"{type(error).__name__}: {error}"
            logger.warning("World Bank request failed (attempt %s/%s): %s", attempt, attempts, last)
            continue
        except requests.RequestException as error:
            raise WorldBankError(f"{type(error).__name__}: {error}") from error
        if response.status_code >= 500:
            last = f"HTTP {response.status_code}"
            logger.warning("World Bank answered %s (attempt %s/%s)", last, attempt, attempts)
            continue
        if response.status_code >= 400:
            raise WorldBankError(f"HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as error:
            raise WorldBankError("response was not valid JSON") from error
    raise WorldBankError(str(last))


def _split(payload) -> tuple[dict, list]:
    """World Bank replies [meta, records]. Returns (meta, records) or raises."""
    if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[0], dict):
        records = payload[1] or []  # no data at all comes back as [meta, null]
        if isinstance(records, list):
            return payload[0], records
    if isinstance(payload, list) and payload and isinstance(payload[0], dict) and "message" in payload[0]:
        raise WorldBankError(f"World Bank error: {payload[0]['message']}")
    raise WorldBankError("unexpected response shape")


def _year_key(date) -> int:
    return int(date) if isinstance(date, str) and date.isdigit() else -1


def _latest(records: list) -> dict | None:
    valid = [r for r in records if isinstance(r, dict) and r.get("value") is not None]
    return max(valid, key=lambda r: _year_key(r.get("date"))) if valid else None


def _result(indicator: Indicator, status: str, *, value=None, year=None, name=None,
            error=None, source_updated=None) -> dict:
    return {
        "key": indicator.key,
        "label": indicator.label,
        "unit": indicator.unit,
        "group": indicator.group,
        "value": value,
        "year": year,
        "source": SOURCE_NAME,
        "sourceCode": indicator.code,
        "indicatorName": name,  # the World Bank's own name for it
        "status": status,
        "stale": False,
        "error": error,
        "sourceLastUpdated": source_updated,
        "fetchedAt": _now_iso(),
    }


def fetch_indicator(country_iso3: str, indicator: Indicator) -> dict:
    """Latest value of one indicator for one country. Never raises."""
    key = f"{country_iso3}:{indicator.key}"
    cached = _cache.get(key, settings.worldbank_cache_seconds)
    if cached is not MISSING:
        return cached
    with _lock_for(key):
        cached = _cache.get(key, settings.worldbank_cache_seconds)
        if cached is not MISSING:
            return cached
        try:
            # mrnev=1 asks for the most recent non-empty value; per_page=60 keeps the answer
            # correct even if a proxy ignores that parameter.
            payload = _get_json(
                f"{BASE_URL}/country/{country_iso3}/indicator/{indicator.code}",
                {"format": "json", "mrnev": 1, "per_page": 60},
            )
            meta, records = _split(payload)
        except WorldBankError as error:
            stale = _cache.get_stale(key)
            if stale is not MISSING:
                return {**stale, "stale": True}
            return _result(indicator, "error", error=str(error))
        except Exception as error:  # a single indicator must never break the profile
            logger.exception("Unexpected failure fetching %s for %s", indicator.key, country_iso3)
            return _result(indicator, "error", error=f"{type(error).__name__}: {error}")

        latest = _latest(records)
        name = None
        if records and isinstance(records[0], dict):
            name = (records[0].get("indicator") or {}).get("value")
        if latest is None:
            result = _result(indicator, "no_data", name=name, source_updated=meta.get("lastupdated"))
        else:
            result = _result(
                indicator, "available", value=latest["value"], year=latest.get("date"),
                name=(latest.get("indicator") or {}).get("value") or name,
                source_updated=meta.get("lastupdated"),
            )
        _cache.set(key, result)
        return result


def fetch_country_indicators(country_iso3: str, indicators: tuple[Indicator, ...] = INDICATORS) -> dict[str, dict]:
    """All indicators for one country, fetched in parallel. Order follows the registry.

    Waits at most `worldbank_profile_deadline` seconds in total. An indicator that has
    not finished by then is returned as "pending" (the rest are unaffected) and keeps
    loading in the background, so the next request finds it cached.
    """
    futures = [(i, _pool.submit(fetch_indicator, country_iso3, i)) for i in indicators]
    deadline = time.monotonic() + settings.worldbank_profile_deadline
    results: dict[str, dict] = {}
    for indicator, future in futures:
        try:
            results[indicator.key] = future.result(timeout=max(0.0, deadline - time.monotonic()))
        except FutureTimeout:
            results[indicator.key] = _result(
                indicator, "pending", error="Still loading from the World Bank; retry in a few seconds.")
        except Exception as error:  # fetch_indicator should not raise; never fail the profile if it does
            logger.exception("Unexpected failure for %s", indicator.key)
            results[indicator.key] = _result(indicator, "error", error=f"{type(error).__name__}: {error}")
    return results


def fetch_bulk(indicator: Indicator) -> tuple[dict[str, dict], str | None]:
    """Latest value of one indicator for EVERY country in one request.

    Returns ({iso3: {"value", "year"}}, error_or_None). Includes World Bank
    aggregates (e.g. "WLD"); callers keep only the iso3 codes they know.
    """
    key = f"bulk:{indicator.key}"
    cached = _cache.get(key, settings.worldbank_cache_seconds)
    if cached is not MISSING:
        return cached, None
    with _lock_for(key):
        cached = _cache.get(key, settings.worldbank_cache_seconds)
        if cached is not MISSING:
            return cached, None
        data: dict[str, dict] = {}
        try:
            page = 1
            while True:
                payload = _get_json(
                    f"{BASE_URL}/country/all/indicator/{indicator.code}",
                    {"format": "json", "mrnev": 1, "per_page": 1000, "page": page},
                )
                meta, records = _split(payload)
                for record in records:
                    iso3, value, year = record.get("countryiso3code"), record.get("value"), record.get("date")
                    if not iso3 or len(iso3) != 3 or value is None:
                        continue
                    previous = data.get(iso3)
                    if previous is None or _year_key(year) > _year_key(previous["year"]):
                        data[iso3] = {"value": value, "year": year}
                try:
                    pages = int(meta.get("pages") or 1)
                except (TypeError, ValueError):
                    pages = 1
                if page >= pages or page >= MAX_BULK_PAGES:
                    break
                page += 1
        except WorldBankError as error:
            stale = _cache.get_stale(key)
            return (stale if stale is not MISSING else {}), str(error)
        _cache.set(key, data)
        return data, None


def fetch_bulk_many(keys: list[str]) -> tuple[dict[str, dict], dict[str, str]]:
    """Bulk snapshots for several indicators in parallel -> (data_by_key, errors_by_key)."""
    with ThreadPoolExecutor(max_workers=max(1, min(8, len(keys)))) as pool:
        futures = [(k, pool.submit(fetch_bulk, BY_KEY[k])) for k in keys]
        data, errors = {}, {}
        for key, future in futures:
            try:
                values, error = future.result()
            except Exception as error_:  # defensive: never fail the list
                values, error = {}, f"{type(error_).__name__}: {error_}"
            data[key] = values
            if error:
                errors[key] = error
        return data, errors
