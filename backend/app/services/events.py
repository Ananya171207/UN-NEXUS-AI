"""Builds the Situation Room event feed from raw source articles.

Pipeline: fetch sources -> de-duplicate -> classify -> shape into the event
contract the React frontend reads -> cache.

Field names are camelCase on purpose: they match `services/README.md` in the
frontend (`id, countryId, category, severity, title, summary, occurredAt`),
so switching the frontend to the backend needs no adapter.
"""
from __future__ import annotations

import hashlib
import logging
import threading

from app.config import settings
from app.services.cache import MISSING, TTLCache
from app.services import ai_events, locations
from app.services.classifier import SEVERITY_RANK, classify_event
from app.services.event_sources import collect_articles, normalize_url

logger = logging.getLogger(__name__)

_events_cache = TTLCache()
_build_lock = threading.Lock()

UNMAPPED_LOCATION = locations.UNMAPPED


def map_country(article: dict) -> dict:
    """Where did this event happen? See `services/locations.py` for the exact rules.

    Never uses the publisher's country (GDELT `sourcecountry`). Returns the unknown
    location unless there is quotable evidence in the article's own words.
    """
    return locations.locate(article)


def make_event_id(article: dict) -> str:
    key = normalize_url(article.get("url")) or (article.get("title") or "")
    return "ev-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def build_event(article: dict) -> dict | None:
    """Shape one article into an event. Returns None if it cannot be shown."""
    title = (article.get("title") or "").strip()
    published = article.get("published")
    if not title or not published:
        # No title, or no reliable timestamp: dropping is better than inventing a date.
        return None

    classification = classify_event(title, article.get("description") or "", article.get("topics") or ())
    event = {
        "id": make_event_id(article),
        "title": title,
        "summary": article.get("description") or None,
        "url": article.get("url") or None,
        "occurredAt": published,  # publication time of the article
        "source": article.get("source") or "Unknown",
        "sourceDomain": article.get("domain"),
        "sourceCountry": article.get("source_country"),  # publisher's country, NOT the event location
        "category": classification.category,
        "severity": classification.severity,
        "topics": list(article.get("topics") or []),
        "classification": {
            "method": classification.method,
            "aiGenerated": classification.ai_generated,
            "signals": list(classification.signals),
        },
        "isSample": False,
    }
    event.update(map_country(article))
    return event


def get_events(force_refresh: bool = False) -> list[dict]:
    """All current events, newest first (cached briefly)."""
    if not force_refresh:
        cached = _events_cache.get("events", settings.events_cache_seconds)
        if cached is not MISSING:
            return cached

    with _build_lock:
        if not force_refresh:
            cached = _events_cache.get("events", settings.events_cache_seconds)
            if cached is not MISSING:
                return cached

        articles = collect_articles(settings.un_news_fetch_limit, settings.gdelt_fetch_limit)
        events = [e for e in (build_event(a) for a in articles) if e]
        events.sort(key=lambda e: e["occurredAt"], reverse=True)
        events = ai_events.apply_overlay(events)  # cached AI labels only; never calls the LLM

        if not events:
            stale = _events_cache.get_stale("events")
            if stale is not MISSING:
                logger.warning("All sources returned nothing; serving the last good event list.")
                return stale
            return []  # never cache an empty result

        _events_cache.set("events", events)
        return events


def clear_cache() -> None:
    _events_cache.clear()


def filter_events(
    events: list[dict],
    *,
    categories: set[str] | None = None,
    severities: set[str] | None = None,
    min_severity: str | None = None,
    country: str | None = None,
    min_location_confidence: str | None = None,
    region: str | None = None,
) -> list[dict]:
    """Apply API filters. `country` only matches events with a *reliable* country."""
    min_rank = SEVERITY_RANK[min_severity] if min_severity else 0
    min_conf = locations.CONFIDENCE_RANK[min_location_confidence] if min_location_confidence else 0
    code = country.strip().upper() if country else None
    result = []
    for event in events:
        if categories and event["category"] not in categories:
            continue
        if severities and event["severity"] not in severities:
            continue
        if SEVERITY_RANK[event["severity"]] < min_rank:
            continue
        if code and code not in (event.get("countryId"), event.get("countryCode3")):
            continue
        if region and event.get("monitoringRegion") != region:
            continue
        if min_conf and locations.CONFIDENCE_RANK.get((event.get("location") or {}).get("confidence"), 0) < min_conf:
            continue
        result.append(event)
    return result
