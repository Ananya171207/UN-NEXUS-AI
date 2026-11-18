"""Where did an event happen? Deterministic country extraction with quoted evidence.

This replaces the old "always unknown" `map_country`. It never calls an external
service and never guesses. The rules, in plain words:

  * Only the HEADLINE is trusted first. If the headline names no country at all,
    the first sentence(s) of the description are read instead (UN News gives one).
  * The publisher's country (GDELT `sourcecountry`) is never used.
  * A country counts as the location when:
      - the headline starts with it and a colon      ("Sudan: aid convoy ..."), or
      - it follows a place word                      ("... in Sudan", "across Nigeria"), or
      - it is the ONLY country named in the text.
  * Two or more countries with no single clear place word  -> "ambiguous":
    the event stays unmapped and the candidates are listed for transparency.
  * Names that are also common words or people (Jordan, Chad, Turkey) count only
    after a place word. "Georgia" (country or US state) and bare "Congo" / "Korea"
    are never assigned. "New Mexico" is not Mexico.
  * Demonyms (Russian, Ukrainian ...) are NOT used: they usually describe the
    actor, not where something happened.

  * Cities: a small curated list of unambiguous cities (CITIES below). A city counts
    as a mention of its country. The event gets city coordinates (`precision: "city"`)
    ONLY when the city follows a place word or starts the headline ("strikes in Kyiv")
    and is the only such city for the chosen country. A bare city mention (e.g. "Kyiv
    says ...") gives the country but no coordinates. Country-level events carry no
    coordinates at all: the map endpoint uses the country's centre and says so.

Confidence: "high" = headline prefix or place-word cue; "medium" = single bare
mention. Every decision lists its evidence.
"""
from __future__ import annotations

import logging
import math
import re
import threading
from dataclasses import dataclass
from typing import Callable

from app.services.regions import monitoring_region

logger = logging.getLogger(__name__)

CONFIDENCE_RANK = {"medium": 2, "high": 3}
CONFIDENCE_LEVELS: tuple[str, ...] = ("medium", "high")

# Extra names per ISO alpha-2 code, on top of each country's common name.
ALIASES: dict[str, tuple[str, ...]] = {
    "US": ("United States", "United States of America", "U.S.", "USA", "US"),
    "GB": ("United Kingdom", "U.K.", "UK", "Britain", "Great Britain"),
    "AE": ("United Arab Emirates", "UAE"),
    "CD": ("DR Congo", "Democratic Republic of the Congo", "Democratic Republic of Congo", "DRC"),
    "CG": ("Republic of the Congo", "Congo-Brazzaville"),
    "CZ": ("Czechia", "Czech Republic"),
    "CI": ("Ivory Coast", "Côte d'Ivoire", "Cote d'Ivoire"),
    "MM": ("Myanmar", "Burma"),
    "PS": ("Palestine", "State of Palestine", "Gaza", "Gaza Strip", "West Bank",
           "Palestinian territory", "Palestinian territories",
           "Occupied Palestinian Territory", "Occupied Palestinian territory"),
    "RU": ("Russia", "Russian Federation"),
    "KR": ("South Korea", "Republic of Korea"),
    "KP": ("North Korea", "DPRK"),
    "TR": ("Türkiye", "Turkiye", "Turkey"),
    "IR": ("Iran", "Islamic Republic of Iran"),
    "SY": ("Syria", "Syrian Arab Republic"),
    "VN": ("Vietnam", "Viet Nam"),
    "LA": ("Laos",),
    "TZ": ("Tanzania",),
    "BO": ("Bolivia",),
    "VE": ("Venezuela",),
    "MD": ("Moldova",),
    "MK": ("North Macedonia",),
    "SZ": ("Eswatini", "Swaziland"),
    "TL": ("Timor-Leste", "East Timor"),
    "CV": ("Cabo Verde", "Cape Verde"),
    "BA": ("Bosnia and Herzegovina", "Bosnia"),
}

# Unambiguous cities: name -> (ISO alpha-2, latitude, longitude). City centres, WGS84.
# Deliberately short and curated: a wrong pin is worse than no pin. Ambiguous names
# (Tripoli, Jerusalem, Victoria, ...) are left out on purpose.
CITIES: dict[str, tuple[str, float, float]] = {
    "Kyiv": ("UA", 50.4501, 30.5234), "Kharkiv": ("UA", 49.9935, 36.2304),
    "Odesa": ("UA", 46.4825, 30.7234), "Zaporizhzhia": ("UA", 47.8388, 35.1396),
    "Dnipro": ("UA", 48.4647, 35.0462), "Lviv": ("UA", 49.8397, 24.0297),
    "Mariupol": ("UA", 47.0971, 37.5434), "Moscow": ("RU", 55.7558, 37.6173),
    "Gaza City": ("PS", 31.5017, 34.4668), "Rafah": ("PS", 31.2969, 34.2435),
    "Khan Younis": ("PS", 31.3462, 34.3062), "Tel Aviv": ("IL", 32.0853, 34.7818),
    "Beirut": ("LB", 33.8938, 35.5018), "Damascus": ("SY", 33.5138, 36.2765),
    "Aleppo": ("SY", 36.2021, 37.1343), "Idlib": ("SY", 35.9306, 36.6339),
    "Baghdad": ("IQ", 33.3152, 44.3661), "Mosul": ("IQ", 36.3350, 43.1189),
    "Tehran": ("IR", 35.6892, 51.3890), "Sanaa": ("YE", 15.3694, 44.1910),
    "Sana'a": ("YE", 15.3694, 44.1910), "Khartoum": ("SD", 15.5007, 32.5599),
    "El Fasher": ("SD", 13.6279, 25.3493), "Port Sudan": ("SD", 19.6158, 37.2164),
    "Juba": ("SS", 4.8594, 31.5713), "Mogadishu": ("SO", 2.0469, 45.3182),
    "Nairobi": ("KE", -1.2921, 36.8219), "Addis Ababa": ("ET", 9.0320, 38.7469),
    "Kinshasa": ("CD", -4.4419, 15.2663), "Goma": ("CD", -1.6792, 29.2228),
    "Port-au-Prince": ("HT", 18.5944, -72.3074), "Kabul": ("AF", 34.5553, 69.2075),
    "Kandahar": ("AF", 31.6289, 65.7372), "Islamabad": ("PK", 33.6844, 73.0479),
    "Karachi": ("PK", 24.8607, 67.0011), "Dhaka": ("BD", 23.8103, 90.4125),
    "Cox's Bazar": ("BD", 21.4272, 92.0058), "Yangon": ("MM", 16.8409, 96.1735),
    "New Delhi": ("IN", 28.6139, 77.2090), "Cairo": ("EG", 30.0444, 31.2357),
    "Lagos": ("NG", 6.5244, 3.3792), "Maiduguri": ("NG", 11.8311, 13.1510),
    "Niamey": ("NE", 13.5116, 2.1254), "Bamako": ("ML", 12.6392, -8.0029),
    "Ouagadougou": ("BF", 12.3714, -1.5197), "N'Djamena": ("TD", 12.1348, 15.0557),
    "Bangui": ("CF", 4.3947, 18.5582),
}

# Common words / people: counted only after a place word ("in Chad").
WEAK_NAMES = frozenset({"Jordan", "Chad", "Turkey"})

# Never assigned to one country; reported as candidates only.
AMBIGUOUS_NAMES: dict[str, tuple[str, ...]] = {
    "Congo": ("CD", "CG"),
    "Korea": ("KR", "KP"),
    "Georgia": ("GE",),  # the country or the US state
}

_DIRECTION = r"(?:(?:northern|southern|eastern|western|central|north|south|east|west|northeastern|northwestern|southeastern|southwestern)\s+)?"
_PLACE_CUE = re.compile(
    rf"\b(?:in|across|inside|throughout|within|near|around)\s+(?:the\s+)?{_DIRECTION}$", re.IGNORECASE
)
DESCRIPTION_CHARS = 400  # only the lead of the description is read


@dataclass(frozen=True)
class _Gazetteer:
    source: object  # the country list it was built from (identity check)
    pattern: re.Pattern
    surfaces: dict[str, tuple[str, ...]]  # surface name -> alpha-2 code(s)
    countries: dict[str, dict]  # alpha-2 -> country record
    ambiguous: frozenset[str]
    city_pattern: re.Pattern | None
    cities: dict[str, tuple[str, float, float]]  # only cities whose country is in the list


@dataclass(frozen=True)
class _Mention:
    surface: str
    codes: tuple[str, ...]
    ambiguous: bool
    cue: str | None  # "headline_prefix" | "place_word" | None
    city: tuple[str, float, float] | None = None  # (name, lat, lon) when this mention is a city


_provider: Callable[[], list[dict]] | None = None
_gazetteer: _Gazetteer | None = None
_lock = threading.Lock()


def set_country_provider(provider: Callable[[], list[dict]] | None) -> None:
    """Override where the country list comes from (tests). None restores the default."""
    global _provider, _gazetteer
    with _lock:
        _provider = provider
        _gazetteer = None


def _load_countries() -> list[dict]:
    if _provider is not None:
        return _provider()
    from app.services import country_data  # local import: avoids a circular import at start-up

    return country_data.load_metadata()


def _build(countries: list[dict]) -> _Gazetteer:
    by_code: dict[str, dict] = {}
    surfaces: dict[str, set[str]] = {}
    for country in countries:
        code = country.get("id")
        if not code or not country.get("name"):
            continue
        by_code[code] = country
        for name in (country["name"], *ALIASES.get(code, ())):
            surfaces.setdefault(name, set()).add(code)
    ambiguous: set[str] = set()
    for surface, candidates in AMBIGUOUS_NAMES.items():
        known = tuple(c for c in candidates if c in by_code)
        if known:
            surfaces[surface] = set(known)
            ambiguous.add(surface)
    ordered = sorted(surfaces, key=len, reverse=True)  # longest first: "South Sudan" before "Sudan"
    pattern = re.compile(r"(?<![\w-])(?:" + "|".join(re.escape(s) for s in ordered) + r")(?![\w-])")
    cities = {name: v for name, v in CITIES.items() if v[0] in by_code}
    city_pattern = None
    if cities:
        city_pattern = re.compile(
            r"(?<![\w-])(?:" + "|".join(re.escape(c) for c in sorted(cities, key=len, reverse=True)) + r")(?![\w-])"
        )
    return _Gazetteer(
        source=countries,
        pattern=pattern,
        surfaces={s: tuple(sorted(c)) for s, c in surfaces.items()},
        countries=by_code,
        ambiguous=frozenset(ambiguous),
        city_pattern=city_pattern,
        cities=cities,
    )


def _get_gazetteer() -> _Gazetteer | None:
    global _gazetteer
    countries = _load_countries()
    if not countries:
        return None
    with _lock:
        if _gazetteer is None or _gazetteer.source is not countries:
            _gazetteer = _build(countries)
        return _gazetteer


def _cue_for(text: str, start: int, end: int) -> str | None:
    if text[:start].strip() == "" and text[end:].lstrip().startswith(":"):
        return "headline_prefix"
    if _PLACE_CUE.search(text[max(0, start - 40):start]):
        return "place_word"
    return None


def _find_mentions(text: str, gaz: _Gazetteer) -> list[_Mention]:
    if not text or not any(ch.islower() for ch in text):
        return []  # ALL-CAPS text: proper nouns cannot be told apart from ordinary words
    found: list[_Mention] = []
    city_spans: list[tuple[int, int]] = []
    if gaz.city_pattern is not None:
        for match in gaz.city_pattern.finditer(text):
            name = match.group(0)
            code, lat, lon = gaz.cities[name]
            city_spans.append((match.start(), match.end()))
            found.append(_Mention(name, (code,), False, _cue_for(text, match.start(), match.end()), (name, lat, lon)))
    for match in gaz.pattern.finditer(text):
        surface, start, end = match.group(0), match.start(), match.end()
        if any(start < ce and cs < end for cs, ce in city_spans):
            continue  # part of a longer city name ("Gaza" inside "Gaza City")
        if text[max(0, start - 4):start] == "New ":
            continue  # New Mexico, etc.
        cue = _cue_for(text, start, end)
        if surface in WEAK_NAMES and cue is None:
            continue
        found.append(_Mention(surface, gaz.surfaces[surface], surface in gaz.ambiguous, cue))
    return found


def _rule(m: _Mention) -> str:
    base = m.cue or ("city_mention" if m.city else "single_mention")
    return f"city_{base}" if (m.city and m.cue) else base


def _decide(mentions: list[_Mention], field: str) -> dict:
    """Turn the mentions found in one piece of text into a decision."""
    resolved: dict[str, _Mention] = {}
    ambiguous: list[_Mention] = []
    cued_cities: dict[str, dict[str, tuple[str, float, float]]] = {}
    for m in mentions:
        if m.ambiguous:
            ambiguous.append(m)
            continue
        code = m.codes[0]
        if m.city and m.cue:
            cued_cities.setdefault(code, {})[m.city[0]] = m.city
        if code not in resolved or (m.cue and not resolved[code].cue):
            resolved[code] = m

    evidence = [
        {"field": field, "match": m.surface, "rule": _rule(m), "_code": code} for code, m in resolved.items()
    ] + [{"field": field, "match": m.surface, "rule": "ambiguous_name", "_code": None} for m in ambiguous]
    candidates = sorted(set(resolved) | {c for m in ambiguous for c in m.codes})

    cued = [code for code, m in resolved.items() if m.cue]
    chosen: str | None = None
    confidence: str | None = None
    if not ambiguous:
        if len(resolved) == 1:
            chosen = next(iter(resolved))
            confidence = "high" if resolved[chosen].cue else "medium"
        elif len(cued) == 1:
            chosen, confidence = cued[0], "high"

    if chosen is None:
        return {"status": "ambiguous", "code": None, "confidence": None, "city": None, "field": field,
                "evidence": [{k: v for k, v in e.items() if k != "_code"} for e in evidence],
                "candidates": candidates}
    cities = cued_cities.get(chosen, {})
    city = next(iter(cities.values())) if len(cities) == 1 else None  # two different cities: no pin
    return {"status": "assigned", "code": chosen, "confidence": confidence, "city": city, "field": field,
            "evidence": [{k: v for k, v in e.items() if k != "_code"} for e in evidence if e["_code"] == chosen],
            "candidates": candidates}


UNMAPPED: dict = {
    "countryId": None, "countryCode3": None, "countryName": None, "region": None, "monitoringRegion": None,
    "latitude": None, "longitude": None, "locationMethod": None, "location": None,
}


def valid_coordinates(lat, lon) -> bool:
    """True only for real, finite WGS84 coordinates."""
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180


def locate(article: dict) -> dict:
    """Location fields for one article. Never raises; unknown stays unknown."""
    try:
        gaz = _get_gazetteer()
        if gaz is None:
            return dict(UNMAPPED)
        title = (article.get("title") or "").strip()
        description = (article.get("description") or "").strip()[:DESCRIPTION_CHARS]

        title_mentions = _find_mentions(title, gaz)
        if title_mentions:
            decision = _decide(title_mentions, "title")
        else:
            description_mentions = _find_mentions(description, gaz)
            if not description_mentions:
                return dict(UNMAPPED)
            decision = _decide(description_mentions, "description")
            # The description is weaker evidence: a bare mention there is not enough.
            if decision["status"] == "assigned" and decision["confidence"] != "high":
                decision = {**decision, "status": "ambiguous", "code": None, "confidence": None, "city": None}
    except Exception:  # location lookup must never break the feed
        logger.exception("Location extraction failed; leaving the event unmapped.")
        return dict(UNMAPPED)

    method = f"gazetteer-{decision['field']}"
    location = {
        "status": decision["status"], "method": method, "confidence": decision["confidence"],
        "precision": None, "city": None,
        "evidence": decision["evidence"], "candidates": decision["candidates"],
    }
    if decision["status"] != "assigned":
        return {**UNMAPPED, "location": location}
    country = gaz.countries[decision["code"]]
    lat = lon = None
    city = decision["city"]
    if city and valid_coordinates(city[1], city[2]):
        location["precision"], location["city"] = "city", city[0]
        lat, lon = city[1], city[2]
    else:
        location["precision"] = "country"  # no event-specific coordinates
    return {
        "countryId": country["id"], "countryCode3": country.get("code"), "countryName": country["name"],
        "region": country.get("region"), "monitoringRegion": monitoring_region(country),
        "latitude": lat, "longitude": lon,
        "locationMethod": method, "location": location,
    }


def apply_validated_location(event: dict, country: dict, quote: str, field: str = "ai") -> dict:
    """Return a copy of `event` placed in `country` by an LLM, after validation by the caller.

    Used only for events the deterministic engine left unmapped. Always medium
    confidence, never gets coordinates, and keeps the quoted evidence.
    """
    updated = dict(event)
    updated.update({
        "countryId": country["id"], "countryCode3": country.get("code"), "countryName": country["name"],
        "region": country.get("region"), "monitoringRegion": monitoring_region(country),
        "latitude": None, "longitude": None, "locationMethod": "llm-validated",
        "location": {
            "status": "assigned", "method": "llm-validated", "confidence": "medium",
            "precision": "country", "city": None,
            "evidence": [{"field": field, "match": quote, "rule": "llm_quote"}],
            "candidates": [country["id"]],
        },
    })
    return updated


def find_country_in_text(text: str, name: str) -> dict | None:
    """Resolve `name` to exactly one country AND confirm `text` actually names it. Else None."""
    gaz = _get_gazetteer()
    if gaz is None or not text:
        return None
    wanted = [m for m in _find_mentions(text, gaz) if not m.ambiguous]
    codes = {m.codes[0] for m in wanted if name.strip().lower() in (m.surface.lower(), gaz.countries[m.codes[0]]["name"].lower())}
    return gaz.countries[next(iter(codes))] if len(codes) == 1 else None
