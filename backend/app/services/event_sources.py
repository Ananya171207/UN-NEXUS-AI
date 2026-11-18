"""Fetching and normalising articles from UN News (RSS) and GDELT (DOC API).

Design rules:
  * A failing source must never break the feed. UN News keeps working when
    GDELT is rate-limited, and vice versa.
  * GDELT is never retried while it is rate-limited (circuit breaker).
  * Successful results are cached; a failing source falls back to its last
    good result ("stale") instead of returning nothing.
  * Dates are normalised to ISO-8601 UTC (e.g. 2026-11-08T10:15:00Z).

Every article is a plain dict:
    title, description, url, published, source, domain, source_country, topics

`source_country` is the country of the *publisher* (GDELT's `sourcecountry`).
It says nothing about where an event happened and must never be used as an
event location.
"""
from __future__ import annotations

import html
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit

import requests

from app.config import settings
from app.services.cache import MISSING, TTLCache

logger = logging.getLogger(__name__)

UN_NEWS_FEED = "https://news.un.org/feed/subscribe/en/news/all/rss.xml"
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
# GDELT requires OR-terms to be wrapped in parentheses. English only, because the
# rule-based classifier reads English. (Not yet verified against live GDELT.)
GDELT_QUERY = (
    "(conflict OR humanitarian OR climate OR health OR economy OR famine "
    "OR refugees OR sanctions OR election) sourcelang:english"
)
GDELT_MAX_RECORDS = 250
MAX_COOLDOWN_SECONDS = 3600

_cache = TTLCache()
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sources")


@contextmanager
def _try_lock(lock: threading.Lock, timeout: float = 0.0):
    """Yield True if the lock was taken within `timeout` seconds (0 = don't wait)."""
    acquired = lock.acquire(timeout=timeout) if timeout > 0 else lock.acquire(blocking=False)
    try:
        yield acquired
    finally:
        if acquired:
            lock.release()


def _monotonic() -> float:  # wrapped so tests can control time
    return time.monotonic()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Per-source health state (powers GET /api/events/status and the breaker)
# ---------------------------------------------------------------------------
class _SourceState:
    def __init__(self, label: str):
        self.label = label
        self.lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        self.status = "never_fetched"  # never_fetched | ok | error | rate_limited
        self.last_attempt: str | None = None
        self.last_success: str | None = None
        self.last_error: str | None = None
        self.article_count = 0
        self.cooldown_until = 0.0

    def cooldown_remaining(self) -> int:
        return max(0, int(round(self.cooldown_until - _monotonic())))


_un_state = _SourceState("UN News")
_gdelt_state = _SourceState("GDELT")


def _record_success(state: _SourceState, count: int) -> None:
    state.status = "ok"
    state.last_success = _utc_now_iso()
    state.last_error = None
    state.article_count = count
    state.cooldown_until = 0.0


def _record_failure(state: _SourceState, status: str, error: object, cooldown: int) -> None:
    state.status = status
    state.last_error = str(error)
    state.cooldown_until = _monotonic() + min(max(cooldown, 0), MAX_COOLDOWN_SECONDS)
    logger.warning(
        "%s unavailable (%s: %s). Not retrying for %ss.",
        state.label, status, error, int(state.cooldown_until - _monotonic()),
    )


def get_source_status() -> list[dict]:
    """Snapshot of each source's health, for monitoring and the frontend."""
    return [
        {
            "source": state.label,
            "status": state.status,
            "lastAttempt": state.last_attempt,
            "lastSuccess": state.last_success,
            "lastError": state.last_error,
            "articleCount": state.article_count,
            "cooldownRemainingSeconds": state.cooldown_remaining(),
        }
        for state in (_un_state, _gdelt_state)
    ]


def reset_state() -> None:
    """Forget caches and breaker state (used by tests)."""
    _cache.clear()
    _un_state.reset()
    _gdelt_state.reset()


def _stale_or_empty(key: str) -> list[dict]:
    value = _cache.get_stale(key)
    return [] if value is MISSING else value


# ---------------------------------------------------------------------------
# Text and date helpers
# ---------------------------------------------------------------------------
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def clean_text(value: object) -> str:
    """Strip HTML tags and entities, collapse whitespace."""
    if not value:
        return ""
    text = _TAG_RE.sub(" ", str(value))
    return _SPACE_RE.sub(" ", html.unescape(text)).strip()


def parse_datetime(value: object) -> str | None:
    """Parse RFC-822 (UN News), GDELT (20261108T101500Z) or ISO-8601 into ISO UTC.

    Returns None when the value is missing or unparseable. Never guesses.
    """
    if not value:
        return None
    raw = str(value).strip()
    parsed: datetime | None = None
    try:
        parsed = datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    if parsed is None:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            parsed = None
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# UN News
# ---------------------------------------------------------------------------
def _parse_feed(content: bytes) -> list:
    import feedparser  # imported here so the helpers above are testable without it

    return list(feedparser.parse(content).entries)


def entry_to_article(entry) -> dict | None:
    """Convert one feedparser entry (or a dict shaped like one) to an article."""
    url = (entry.get("link") or "").strip()
    title = clean_text(entry.get("title"))
    if not title or not url:
        return None
    topics = [
        clean_text(tag.get("term"))
        for tag in (entry.get("tags") or [])
        if tag.get("term")
    ]
    return {
        "title": title,
        "description": clean_text(entry.get("summary")),
        "url": url,
        "published": parse_datetime(entry.get("published") or entry.get("updated")),
        "source": "UN News",
        "domain": urlsplit(url).netloc.lower() or None,
        "source_country": None,
        "topics": [t for t in topics if t],
    }


def _fetch_un_news_all() -> list[dict]:
    cached = _cache.get("un_news", settings.un_news_cache_seconds)
    if cached is not MISSING:
        return cached
    with _try_lock(_un_state.lock, settings.un_news_wait_seconds) as acquired:
        if not acquired:  # another request is already loading it and is taking long
            return _stale_or_empty("un_news")
        cached = _cache.get("un_news", settings.un_news_cache_seconds)
        if cached is not MISSING:
            return cached
        if _un_state.cooldown_remaining() > 0:
            return _stale_or_empty("un_news")

        _un_state.last_attempt = _utc_now_iso()
        try:
            response = requests.get(
                UN_NEWS_FEED,
                timeout=settings.un_news_timeout,
                headers={"User-Agent": settings.user_agent},
            )
            response.raise_for_status()
            entries = _parse_feed(response.content)
        except Exception as error:  # a source must never crash the feed
            _record_failure(_un_state, "error", error, settings.source_error_cooldown_seconds)
            return _stale_or_empty("un_news")

        articles = [a for a in (entry_to_article(e) for e in entries) if a]
        if not articles:
            _record_failure(
                _un_state, "error", "feed returned no usable entries",
                settings.source_error_cooldown_seconds,
            )
            return _stale_or_empty("un_news")

        _cache.set("un_news", articles)
        _record_success(_un_state, len(articles))
        return articles


def fetch_un_news(limit: int = 10) -> list[dict]:
    """Latest UN News articles (cached; falls back to the last good result)."""
    return _fetch_un_news_all()[:limit]


# ---------------------------------------------------------------------------
# GDELT
# ---------------------------------------------------------------------------
def _parse_retry_after(value: str | None) -> int | None:
    if value and value.strip().isdigit():
        return int(value.strip())
    return None


def gdelt_entry_to_article(entry: dict) -> dict | None:
    url = (entry.get("url") or "").strip()
    title = clean_text(entry.get("title"))
    if not title or not url:
        return None
    return {
        "title": title,
        "description": "",
        "url": url,
        "published": parse_datetime(entry.get("seendate")),
        "source": "GDELT",
        "domain": (entry.get("domain") or "").strip() or None,
        "source_country": (entry.get("sourcecountry") or "").strip() or None,
        "topics": [],
    }


def fetch_gdelt_news(limit: int = 5) -> list[dict]:
    """Latest GDELT articles.

    Rate limiting: on HTTP 429 (or any other failure) GDELT is not contacted
    again until the cooldown ends. Meanwhile the last good result is served,
    or an empty list if there never was one.
    """
    cached = _cache.get("gdelt", settings.gdelt_cache_seconds)
    if cached is not MISSING:
        return cached[:limit]
    with _try_lock(_gdelt_state.lock) as acquired:
        if not acquired:  # a slow GDELT call is already in flight: never queue behind it
            return _stale_or_empty("gdelt")[:limit]
        cached = _cache.get("gdelt", settings.gdelt_cache_seconds)
        if cached is not MISSING:
            return cached[:limit]
        if _gdelt_state.cooldown_remaining() > 0:
            return _stale_or_empty("gdelt")[:limit]

        _gdelt_state.last_attempt = _utc_now_iso()
        params = {
            "query": GDELT_QUERY,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": min(GDELT_MAX_RECORDS, max(limit, settings.gdelt_fetch_limit)),
            "sort": "DateDesc",
        }
        try:
            response = requests.get(
                GDELT_URL,
                params=params,
                timeout=settings.gdelt_timeout,
                headers={"User-Agent": settings.user_agent},
            )
            if response.status_code == 429:
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                _record_failure(
                    _gdelt_state, "rate_limited", "HTTP 429 Too Many Requests",
                    retry_after or settings.gdelt_cooldown_seconds,
                )
                return _stale_or_empty("gdelt")[:limit]
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            _record_failure(_gdelt_state, "error", error, settings.source_error_cooldown_seconds)
            return _stale_or_empty("gdelt")[:limit]

        raw_articles = payload.get("articles", []) if isinstance(payload, dict) else []
        articles = [a for a in (gdelt_entry_to_article(e) for e in raw_articles) if a]
        _cache.set("gdelt", articles)
        _record_success(_gdelt_state, len(articles))
        return articles[:limit]


# ---------------------------------------------------------------------------
# Combining sources
# ---------------------------------------------------------------------------
_TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "ref"}


def normalize_url(url: str | None) -> str:
    """Canonical form of a URL for duplicate detection (not for linking)."""
    if not url:
        return ""
    parts = urlsplit(url.strip())
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    query = urlencode(
        sorted(
            (k, v)
            for k, v in parse_qsl(parts.query)
            if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
        )
    )
    path = parts.path.rstrip("/")
    return f"{host}{path}" + (f"?{query}" if query else "")


def normalize_title(title: str | None) -> str:
    return _SPACE_RE.sub(" ", re.sub(r"[^a-z0-9]+", " ", (title or "").lower())).strip()


def dedupe_articles(articles: list[dict]) -> list[dict]:
    """Drop repeats by canonical URL or (long enough) identical title.

    The first occurrence wins, so list preferred sources first.
    """
    unique: list[dict] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    for article in articles:
        url_key = normalize_url(article.get("url"))
        title_key = normalize_title(article.get("title"))
        if not url_key:
            continue
        if url_key in seen_urls or (len(title_key) >= 25 and title_key in seen_titles):
            continue
        seen_urls.add(url_key)
        if len(title_key) >= 25:
            seen_titles.add(title_key)
        unique.append(article)
    return unique


def _safe_fetch(fetcher, limit: int) -> list[dict]:
    try:
        return fetcher(limit)
    except Exception:
        logger.exception("Unexpected failure in %s", getattr(fetcher, "__name__", fetcher))
        return []


def _within(future, seconds: float, label: str) -> list[dict]:
    try:
        return future.result(timeout=max(0.0, seconds))
    except FutureTimeout:
        logger.warning("%s did not answer within %.0fs; continuing without it (it keeps loading).", label, seconds)
        return []


def collect_articles(un_limit: int, gdelt_limit: int) -> list[dict]:
    """Fetch both sources in parallel, de-duplicate, sort newest first.

    Each source degrades independently, and a slow source never holds up the answer:
    GDELT is waited for at most `gdelt_wait_seconds`. If it is not ready, the feed is
    served without it while the call finishes in the background and fills the cache.
    Undated articles sort last.
    """
    started = _monotonic()
    un_future = _pool.submit(_safe_fetch, fetch_un_news, un_limit)
    gdelt_future = _pool.submit(_safe_fetch, fetch_gdelt_news, gdelt_limit)
    un = _within(un_future, settings.un_news_wait_seconds, "UN News")
    gdelt = _within(gdelt_future, settings.gdelt_wait_seconds - (_monotonic() - started), "GDELT")
    articles = dedupe_articles(un + gdelt)
    articles.sort(key=lambda a: a.get("published") or "", reverse=True)
    return articles


def fetch_all_events(limit: int = 20) -> list[dict]:
    """Newest `limit` unique articles across all available sources.

    Same name and meaning as before, but it now sorts *before* slicing, so GDELT
    articles are no longer dropped just because UN News filled the list.
    """
    return collect_articles(limit, limit)[:limit]
