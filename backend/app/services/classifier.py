"""Rule-based event classification (category + severity).

This is a transparent baseline: every decision lists the words that caused it
in `signals`, so a wrong label can be traced and fixed by editing the term lists
below. It never calls an external service.

Vocabulary matches the frontend (`data/taxonomy.js`) plus Security, Health and
Other, which the frontend does not have yet.

Severity philosophy (deliberately conservative):
  * Title evidence counts fully; evidence found only in the description or UN
    topic tags counts one tier lower.
  * "critical" needs an unmistakable title term (genocide, massacre...) or a
    reported toll of 100+ in the title.
  * Routine items (observance days, appointments, awards) are capped at "low".
  * Words like "climate" or "conflict" alone never raise severity above
    "moderate".
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Order is the tie-break priority when two categories score the same.
CATEGORIES: tuple[str, ...] = (
    "Security",
    "Humanitarian",
    "Health",
    "Environmental",
    "Economic",
    "Political",
    "Development",
    "International relations",
    "Other",
)
SEVERITY_LEVELS: tuple[str, ...] = ("low", "moderate", "high", "critical")
SEVERITY_RANK = {"none": 0, "low": 1, "moderate": 2, "high": 3, "critical": 4}

CATEGORY_ALIASES = {
    "conflict": "Security",
    "conflict / security": "Security",
    "conflict/security": "Security",
    "social": "Development",
}
SEVERITY_ALIASES = {"medium": "moderate"}

# A trailing "*" means "word starts with"; otherwise the whole word must match.
# A term written in CAPITALS (e.g. "WHO") is matched case-sensitively, so the
# pronoun "who" is not mistaken for the World Health Organization.
CATEGORY_TERMS: dict[str, list[str]] = {
    "Security": [
        "war", "armed conflict", "airstrike*", "air strike*", "shelling", "bombardment",
        "missile*", "militia*", "militant*", "insurgen*", "terror*", "ceasefire*",
        "hostilities", "fighting", "troops", "coup", "hostage*", "peacekeep*",
        "peace and security", "violence", "weapons", "attack*", "offensive",
        "clashes", "armed group*", "landmine*", "strikes on",
    ],
    "Humanitarian": [
        "humanitarian", "refugee*", "displace*", "famine", "hunger", "food insecurity",
        "starvation", "aid", "relief", "asylum", "migrant*", "evacuat*", "civilians",
        "shelter", "malnutrition", "unhcr", "ocha", "wfp", "migrants and refugees",
        "survivors",
    ],
    "Health": [
        "health", "disease*", "outbreak*", "epidemic*", "pandemic*", "cholera", "measles",
        "polio", "vaccin*", "malaria", "hiv", "aids", "tuberculosis", "mpox", "ebola",
        "WHO", "world health organization", "hospital*", "maternal", "mental health", "dengue", "medical",
    ],
    "Environmental": [
        "climate", "flood*", "drought*", "cyclone*", "hurricane*", "typhoon*", "wildfire*",
        "heatwave*", "emission*", "biodiversity", "pollution", "deforestation", "cop29",
        "cop30", "cop31", "glacier*", "sea level", "plastic*", "environment*", "ocean*",
        "earthquake*", "tsunami*", "ecosystem*", "greenhouse", "global warming",
        "climate and environment", "temperature*", "extreme weather", "warming",
    ],
    "Economic": [
        "economy", "economic", "trade", "tariff*", "debt", "inflation", "gdp", "financ*",
        "invest*", "jobs", "labour", "labor", "unemployment", "market*", "remittance*",
        "ilo", "imf", "world bank", "economic development", "growth", "unctad",
    ],
    "Political": [
        "election*", "government*", "president", "parliament*", "vote*", "voting",
        "democra*", "human rights", "rights council", "justice", "court", "tribunal",
        "constitution*", "opposition", "law and crime prevention", "prime minister",
        "detention", "arrest*", "rights",
    ],
    "Development": [
        "development", "sdg*", "sustainable development", "education", "school*", "girls",
        "women", "gender", "poverty", "inclusion", "infrastructure", "internet", "digital",
        "agricultur*", "sanitation", "undp", "unicef", "unesco", "skills", "youth",
        "children", "literacy",
    ],
    "International relations": [
        "treaty", "summit", "diplomat*", "bilateral", "sanction*", "general assembly",
        "security council", "envoy", "negotiat*", "talks", "agreement*", "cooperation",
        "multilateral", "secretary-general", "partnership*", "member states", "un80",
        "resolution",
    ],
}

SEVERITY_TERMS: dict[str, list[str]] = {
    "critical": [
        "genocide", "ethnic cleansing", "massacre*", "mass casualt*", "mass grave*",
        "famine declared", "declares famine", "famine confirmed", "chemical attack",
    ],
    "high": [
        "airstrike*", "air strike*", "shelling", "bombardment", "offensive", "fighting",
        "hostilities", "armed conflict", "famine", "humanitarian catastrophe",
        "catastroph*", "state of emergency", "mass displacement", "atrocit*", "war crimes",
        "siege", "coup", "hostage*", "terror*", "missile*", "attack*", "strikes on",
    ],
    "moderate": [
        "crisis", "conflict", "tension*", "clashes", "violence", "outbreak*", "epidemic*",
        "drought*", "flood*", "cyclone*", "hurricane*", "typhoon*", "earthquake*",
        "wildfire*", "heatwave*", "displace*", "refugee*", "hunger", "food insecurity",
        "sanction*", "protest*", "unrest", "warns", "warning", "urgent*", "appeal*",
        "ceasefire", "killed", "dead", "deaths", "injured",
    ],
}

# Observances and announcements. A title containing one of these is routine news.
ROUTINE_TERMS = [
    "international day", "world day", "anniversary", "appoints", "appointment",
    "celebrat*", "commemorat*", "award*", "photo exhibition", "remembrance",
]


def _compile(term: str) -> re.Pattern:
    flags = 0 if (len(term) > 1 and term.isupper()) else re.IGNORECASE
    if term.endswith("*"):
        return re.compile(rf"\b{re.escape(term[:-1])}\w*", flags)
    return re.compile(rf"\b{re.escape(term)}\b", flags)


_CATEGORY_PATTERNS = {c: [(t, _compile(t)) for t in terms] for c, terms in CATEGORY_TERMS.items()}
_SEVERITY_PATTERNS = {s: [(t, _compile(t)) for t in terms] for s, terms in SEVERITY_TERMS.items()}
_ROUTINE_PATTERNS = [(t, _compile(t)) for t in ROUTINE_TERMS]

# --- casualty figures --------------------------------------------------------
_NUMBER = r"(?P<n>\d[\d,]*|dozens|scores|hundreds|thousands)"
_VICTIM = r"(?:killed|dead|deaths|died|casualties|fatalit\w+|lives lost)"
_CASUALTY_FORWARD = re.compile(rf"\b{_NUMBER}\s+(?:[\w-]+\s+){{0,2}}?{_VICTIM}\b", re.IGNORECASE)
_CASUALTY_REVERSE = re.compile(
    rf"\b(?:kill(?:s|ed|ing)?|claim(?:s|ed)?\s+(?:the\s+)?lives\s+of)\s+"
    rf"(?:at least |more than |over |nearly |about |around |some )?{_NUMBER}\b",
    re.IGNORECASE,
)
_WORD_NUMBERS = {"dozens": 24, "scores": 40, "hundreds": 200, "thousands": 2000}


def _casualty_count(text: str) -> int:
    """Largest reported death toll in the text (0 if none is stated)."""
    best = 0
    for pattern in (_CASUALTY_FORWARD, _CASUALTY_REVERSE):
        for match in pattern.finditer(text):
            raw = match.group("n").lower()
            if re.fullmatch(r"(19|20|21)\d\d", raw):
                continue  # a bare four-digit number in this range is far more likely a year
            try:
                value = _WORD_NUMBERS.get(raw) or int(raw.replace(",", ""))
            except ValueError:
                continue
            if value < 10_000_000:  # ignore things like years or phone numbers
                best = max(best, value)
    return best


@dataclass(frozen=True)
class Classification:
    category: str
    severity: str
    signals: tuple[str, ...]
    method: str = "rules"
    ai_generated: bool = False


def normalize_category(value: str) -> str | None:
    """Map user input (any case, plus aliases) to a known category, else None."""
    key = value.strip().lower()
    if key in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[key]
    for category in CATEGORIES:
        if category.lower() == key:
            return category
    return None


def normalize_severity(value: str) -> str | None:
    key = value.strip().lower()
    key = SEVERITY_ALIASES.get(key, key)
    return key if key in SEVERITY_LEVELS else None


def _matches(patterns: list[tuple[str, re.Pattern]], text: str) -> list[str]:
    return [term for term, pattern in patterns if pattern.search(text)]


def _classify_category(title: str, body: str) -> tuple[str, list[str]]:
    scores: dict[str, int] = {}
    signals: dict[str, list[str]] = {}
    for category, patterns in _CATEGORY_PATTERNS.items():
        in_title = _matches(patterns, title)
        in_body = [t for t in _matches(patterns, body) if t not in in_title]
        scores[category] = 3 * len(in_title) + len(in_body)
        signals[category] = [f"title:{t}" for t in in_title] + [f"text:{t}" for t in in_body]

    best_category = "Other"
    best_score = 1  # need at least 2 points to leave "Other"
    for category in CATEGORIES[:-1]:  # priority order breaks ties
        if scores[category] > best_score:
            best_category, best_score = category, scores[category]
    return best_category, signals.get(best_category, [])


def _classify_severity(title: str, body: str) -> tuple[str, list[str]]:
    routine = _matches(_ROUTINE_PATTERNS, title)
    if routine:
        return "low", [f"routine:{t}" for t in routine]

    rank = 1  # low
    signals: list[str] = []
    for level in ("critical", "high", "moderate"):
        tier = SEVERITY_RANK[level]
        for term in _matches(_SEVERITY_PATTERNS[level], title):
            rank = max(rank, tier)
            signals.append(f"title:{term}")
        for term in _matches(_SEVERITY_PATTERNS[level], body):
            rank = max(rank, max(tier - 1, 1))  # outside the title: one tier lower
            signals.append(f"text:{term}")

    title_toll = _casualty_count(title)
    body_toll = _casualty_count(body)
    if title_toll >= 100:
        rank = max(rank, SEVERITY_RANK["critical"])
    elif title_toll >= 10:
        rank = max(rank, SEVERITY_RANK["high"])
    elif title_toll >= 1:
        rank = max(rank, SEVERITY_RANK["moderate"])
    if title_toll:
        signals.append(f"title:reported toll {title_toll}")
    if body_toll >= 100:
        rank = max(rank, SEVERITY_RANK["high"])
    elif body_toll >= 10:
        rank = max(rank, SEVERITY_RANK["moderate"])
    if body_toll:
        signals.append(f"text:reported toll {body_toll}")

    level = next(name for name, value in SEVERITY_RANK.items() if value == rank)
    return level, signals


def classify_event(title: str, description: str = "", topics: list[str] | tuple[str, ...] = ()) -> Classification:
    """Assign a category and severity from the article's own words.

    `topics` are optional tags supplied by the source (e.g. UN News topic tags).
    They are read like description text, never like title text.
    """
    title = title or ""
    body = " ".join(part for part in (description or "", " ".join(topics or ())) if part)
    category, category_signals = _classify_category(title, body)
    severity, severity_signals = _classify_severity(title, body)
    signals = tuple(dict.fromkeys([f"category/{s}" for s in category_signals] + [f"severity/{s}" for s in severity_signals]))
    return Classification(category=category, severity=severity, signals=signals)
