"""Shared pieces of the AI layer: persistent cache, grounding checks, labels."""
from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "AI-generated interpretation of the source text. It can be wrong. The original article is the "
    "authority; the figures come from the cited data."
)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def digest(*parts: object) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()


class AICache:
    """Key -> JSON value. Memory first, SQLite file behind it (survives restarts).

    If the file cannot be opened the cache silently becomes memory-only: AI results are an
    optimisation, never a requirement. Use path ':memory:' (or '') for memory only.
    """

    def __init__(self, path: str | None = None):
        self._path = path
        self._memory: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._ready = False
        self._disk = False

    def _resolve_path(self) -> str:
        return settings.ai_cache_path if self._path is None else self._path

    def _init_disk(self) -> None:
        if self._ready:
            return
        self._ready = True
        path = self._resolve_path()
        if not path or path == ":memory:":
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with contextlib.closing(sqlite3.connect(path)) as db, db:
                db.execute("CREATE TABLE IF NOT EXISTS ai_cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, created_at TEXT NOT NULL)")
            self._disk = True
        except (OSError, sqlite3.Error) as error:
            logger.warning("AI cache file unavailable (%s); using memory only.", error)

    def get(self, key: str) -> dict | None:
        with self._lock:
            if key in self._memory:
                return self._memory[key]
            self._init_disk()
            if not self._disk:
                return None
            try:
                with contextlib.closing(sqlite3.connect(self._resolve_path())) as db:
                    row = db.execute("SELECT value FROM ai_cache WHERE key = ?", (key,)).fetchone()
                if row:
                    value = json.loads(row[0])
                    self._memory[key] = value
                    return value
            except (sqlite3.Error, ValueError) as error:
                logger.warning("AI cache read failed: %s", error)
            return None

    def set(self, key: str, value: dict) -> None:
        with self._lock:
            self._memory[key] = value
            self._init_disk()
            if not self._disk:
                return
            try:
                with contextlib.closing(sqlite3.connect(self._resolve_path())) as db, db:
                    db.execute("INSERT OR REPLACE INTO ai_cache (key, value, created_at) VALUES (?, ?, ?)",
                               (key, json.dumps(value, ensure_ascii=False), now_iso()))
            except sqlite3.Error as error:
                logger.warning("AI cache write failed: %s", error)

    def clear_memory(self) -> None:
        with self._lock:
            self._memory.clear()


_cache = AICache()


def get_cache() -> AICache:
    return _cache


def set_cache(cache: AICache) -> None:
    """Swap the cache (tests)."""
    global _cache
    _cache = cache


_NUMBER = re.compile(r"\d[\d,]*\.?\d*")


def numbers_supported(text: str, source: str) -> bool:
    """Every number in `text` must also appear in `source`: blocks invented figures."""
    haystack = source.replace(",", "")
    for token in _NUMBER.findall(text or ""):
        cleaned = token.replace(",", "").rstrip(".")
        if cleaned and cleaned not in haystack:
            return False
    return True


def clip(value: object, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return text if 0 < len(text) <= limit else None


def ai_block(status: str, **fields) -> dict:
    """Uniform wrapper so the frontend can always tell AI text from data."""
    return {"aiGenerated": True, "status": status, "disclaimer": DISCLAIMER, **fields}
