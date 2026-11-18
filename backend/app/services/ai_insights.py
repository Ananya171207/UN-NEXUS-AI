"""Country insights and regional intelligence.

Both are built in two clearly separated layers:
  1. `facts` / `development`: deterministic, taken straight from World Bank values or event records.
  2. `interpretation` / `narrative`: optional AI text that must cite the fact/event ids it relies on,
     and that is dropped if it cites something that does not exist or contains a number the facts do
     not contain. Without an LLM the second layer is simply absent (status "disabled").

Only the latest value of each indicator is available, so no insight may describe a trend or change
over time, and the prompts forbid predictions.
"""
from __future__ import annotations

import json
import logging

from app.services import ai_common, llm, monitoring
from app.services.classifier import SEVERITY_RANK

logger = logging.getLogger(__name__)

PROMPT_VERSION = "in1"
MIN_FACTS = 3
MIN_REGION_EVENTS = 3
MAX_REGION_EVENTS = 12

COUNTRY_SYSTEM = """You write short, careful notes for a UN development dashboard.
Use ONLY the facts provided (JSON). Never invent numbers, never describe trends or changes over time
(only the latest value of each indicator is given), never predict, never claim a country is on or off
track for any goal. Return JSON only:
{"interpretation":"<at most 3 sentences on what these facts show>",
 "challenges":[{"text":"<one possible development challenge the facts point to>","basedOn":["<fact id>", ...]}]}
At most 3 challenges, each citing at least one fact id exactly as given."""

REGION_SYSTEM = """You write short situation notes for a UN monitoring dashboard.
Use ONLY the events provided (JSON, with ids). Do not add facts, numbers or names that are not in the
event titles, and do not predict. Return JSON only:
{"summary":"<at most 3 sentences on the main developments>",
 "developments":[{"text":"<one development>","eventIds":["<event id>", ...]}]}
At most 4 developments, each citing at least one event id exactly as given."""


def _fmt(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    number = float(value)
    return f"{number:,.0f}" if abs(number) >= 1000 else f"{number:.2f}".rstrip("0").rstrip(".")


def build_country_facts(results: dict[str, dict], events: list[dict]) -> dict:
    facts, missing = [], []
    for key, result in results.items():
        if result["status"] != "available":
            missing.append({"indicatorKey": key, "indicatorName": result.get("label"), "availability": result["status"]})
            continue
        unit = f" {result['unit']}" if result.get("unit") else ""
        facts.append({
            "id": f"f_{key}", "type": "indicator", "indicatorKey": key,
            "text": f"{result.get('label')}: {_fmt(result['value'])}{unit} ({result['year']})",
            "value": result["value"], "year": result["year"], "unit": result.get("unit"),
            "source": result.get("source"), "stale": bool(result.get("stale")),
        })
    for event in events[:5]:
        facts.append({
            "id": f"e_{event['id']}", "type": "event", "text": event["title"], "severity": event["severity"],
            "category": event["category"], "occurredAt": event["occurredAt"], "url": event.get("url"),
        })
    return {"facts": facts, "missingIndicators": missing}


def _generate(system: str, payload: dict, cache_key: str, validate) -> dict:
    """Cached, validated LLM call. Returns an ai_block."""
    cache = ai_common.get_cache()
    hit = cache.get(cache_key)
    if hit:
        return ai_common.ai_block("cached", **hit)
    if not llm.is_configured():
        return ai_common.ai_block("disabled")
    try:
        raw = llm.complete_json(system, json.dumps(payload, ensure_ascii=False))
    except llm.LLMError as error:
        logger.warning("AI insight failed: %s", error)
        return ai_common.ai_block("unavailable")
    valid = validate(raw)
    if valid is None:
        return ai_common.ai_block("rejected")
    valid.update({"model": llm.model_name(), "generatedAt": ai_common.now_iso()})
    cache.set(cache_key, valid)
    return ai_common.ai_block("generated", **valid)


def country_insights(country: dict, results: dict[str, dict], events: list[dict]) -> dict:
    built = build_country_facts(results, events)
    facts = built["facts"]
    indicator_facts = [f for f in facts if f["type"] == "indicator"]
    base = {
        "countryId": country["id"], "countryCode": country["code"], "countryName": country["name"],
        "dataType": "facts", "facts": facts, "missingIndicators": built["missingIndicators"],
        "factsNote": "Facts are World Bank values (latest available year) and recent events linked to this country. Nothing here is AI-generated.",
    }
    if len(indicator_facts) < MIN_FACTS:
        return {**base, "interpretation": ai_common.ai_block("insufficient_data")}

    ids = {f["id"] for f in facts}
    source_text = " ".join(f["text"] for f in facts)

    def validate(raw: dict) -> dict | None:
        text = ai_common.clip(raw.get("interpretation"), 600)
        if not text or not ai_common.numbers_supported(text, source_text):
            return None
        challenges = []
        for item in raw.get("challenges") if isinstance(raw.get("challenges"), list) else []:
            if not isinstance(item, dict):
                continue
            claim = ai_common.clip(item.get("text"), 300)
            based = item.get("basedOn")
            if (not claim or not isinstance(based, list) or not based or not all(isinstance(b, str) and b in ids for b in based)
                    or not ai_common.numbers_supported(claim, source_text)):
                continue
            challenges.append({"text": claim, "basedOn": based})
        return {"text": text, "challenges": challenges[:3]}

    key = "country:" + ai_common.digest(PROMPT_VERSION, country["id"], source_text)
    payload = {"country": country["name"], "facts": [{"id": f["id"], "text": f["text"]} for f in facts]}
    return {**base, "interpretation": _generate(COUNTRY_SYSTEM, payload, key, validate)}


def regional_intelligence(region: str, events: list[dict]) -> dict:
    """`events` are the events of this region (already filtered by the caller)."""
    events = monitoring.unique_events(events)
    aggregate = next(r for r in monitoring.aggregate_regions(events)["regions"] if r["region"] == region)
    base = {"region": region, "dataType": "counts", "development": aggregate}
    if len(events) < MIN_REGION_EVENTS:
        return {**base, "narrative": ai_common.ai_block("insufficient_data")}

    chosen = sorted(events, key=lambda e: e["occurredAt"], reverse=True)
    chosen.sort(key=lambda e: SEVERITY_RANK[e["severity"]], reverse=True)
    chosen = chosen[:MAX_REGION_EVENTS]
    ids = {e["id"] for e in chosen}
    source_text = " ".join(e["title"] for e in chosen)

    def validate(raw: dict) -> dict | None:
        text = ai_common.clip(raw.get("summary"), 600)
        if not text or not ai_common.numbers_supported(text, source_text):
            return None
        developments = []
        for item in raw.get("developments") if isinstance(raw.get("developments"), list) else []:
            if not isinstance(item, dict):
                continue
            claim = ai_common.clip(item.get("text"), 300)
            cited = item.get("eventIds")
            if (not claim or not isinstance(cited, list) or not cited or not all(isinstance(c, str) and c in ids for c in cited)
                    or not ai_common.numbers_supported(claim, source_text)):
                continue
            developments.append({"text": claim, "eventIds": cited})
        return {"text": text, "developments": developments[:4]} if developments else None

    key = "region:" + ai_common.digest(PROMPT_VERSION, region, *sorted(e["id"] + e["title"] for e in chosen))
    payload = {"region": region, "events": [{"id": e["id"], "title": e["title"], "severity": e["severity"]} for e in chosen]}
    return {**base, "narrative": _generate(REGION_SYSTEM, payload, key, validate)}
