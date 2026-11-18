"""Event -> SDG mapping by transparent keyword rules (the non-AI path).

An event being *related* to a goal says nothing about whether any country's actual
progress on that goal has changed. Every mapping lists the words that triggered it.
Confidence: "medium" when the word is in the headline, "low" when only in the description.
"""
from __future__ import annotations

import re

from app.services.sdg import SDG_NAMES

# A trailing "*" means "word starts with".
SDG_TERMS: dict[int, list[str]] = {
    1: ["poverty", "extreme poverty", "social protection", "cash transfer*"],
    2: ["hunger", "famine", "food insecurity", "food security", "malnutrition", "starvation", "undernourish*"],
    3: ["health", "outbreak*", "epidemic*", "pandemic*", "cholera", "measles", "polio", "vaccin*", "malaria",
        "hiv", "tuberculosis", "mpox", "ebola", "disease*", "hospital*", "mental health", "maternal", "dengue"],
    4: ["education", "school*", "literacy", "teacher*", "students", "out of school", "learning"],
    5: ["women", "girls", "gender", "sexual violence", "gender-based"],
    6: ["drinking water", "water supply", "sanitation", "clean water", "water scarcity"],
    7: ["energy", "electricity", "renewable*", "power cuts", "blackout*", "power grid", "fuel"],
    8: ["jobs", "labour", "labor", "unemployment", "decent work", "child labour", "wages", "economic growth"],
    9: ["infrastructure", "internet", "digital", "innovation", "broadband", "connectivity"],
    10: ["inequality", "discrimination", "migrant*", "refugee*", "asylum", "inclusion"],
    11: ["cities", "urban", "housing", "earthquake*", "flood*", "disaster*", "slum*"],
    12: ["plastic*", "waste", "recycling", "food waste", "consumption"],
    13: ["climate", "emission*", "greenhouse", "global warming", "heatwave*", "drought*", "cyclone*",
         "hurricane*", "typhoon*", "wildfire*", "extreme weather", "sea level"],
    14: ["ocean*", "marine", "fisher*", "coral", "sea level"],
    15: ["forest*", "biodiversity", "deforestation", "wildlife", "desertification", "ecosystem*"],
    16: ["war", "armed conflict", "conflict", "peace", "ceasefire*", "justice", "human rights", "violence",
         "terror*", "war crimes", "rule of law", "airstrike*", "hostilities", "civilians"],
    17: ["partnership*", "development finance", "debt relief", "official development assistance"],
}

MAX_SDGS = 3


def _compile(term: str) -> re.Pattern:
    if term.endswith("*"):
        return re.compile(rf"\b{re.escape(term[:-1])}\w*", re.IGNORECASE)
    return re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)


_PATTERNS = {goal: [(t, _compile(t)) for t in terms] for goal, terms in SDG_TERMS.items()}


def map_event_to_sdgs(title: str, description: str = "") -> list[dict]:
    """Up to three goals, best evidence first. Empty list when nothing matches."""
    found: list[tuple[int, int, int, list[dict]]] = []  # (title_hits, text_hits, goal, evidence)
    for goal, patterns in _PATTERNS.items():
        evidence: list[dict] = []
        title_hits = text_hits = 0
        for term, pattern in patterns:
            if pattern.search(title or ""):
                evidence.append({"field": "title", "match": term})
                title_hits += 1
            elif pattern.search(description or ""):
                evidence.append({"field": "description", "match": term})
                text_hits += 1
        if evidence:
            found.append((title_hits, text_hits, goal, evidence))
    found.sort(key=lambda f: (-f[0], -f[1], f[2]))

    result = []
    for title_hits, _, goal, evidence in found[:MAX_SDGS]:
        words = ", ".join(sorted({e["match"] for e in evidence}))
        where = "headline" if title_hits else "description"
        result.append({
            "sdg": goal, "name": SDG_NAMES[goal],
            "reason": f"The {where} mentions: {words}.",
            "evidence": evidence,
            "confidence": "medium" if title_hits else "low",
            "method": "rules", "aiGenerated": False,
        })
    return result
