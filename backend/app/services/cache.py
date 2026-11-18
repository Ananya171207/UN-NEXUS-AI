"""A tiny thread-safe in-memory TTL cache.

`get` honours the TTL. `get_stale` ignores it, so a source that is failing can
still serve its last good result instead of returning nothing.
"""
import threading
import time
from typing import Any, Callable

MISSING = object()  # distinguishes "not cached" from a cached None / empty list


class TTLCache:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._items: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._items[key] = (self._clock(), value)

    def get(self, key: str, ttl: float) -> Any:
        with self._lock:
            entry = self._items.get(key)
        if entry is None:
            return MISSING
        stored_at, value = entry
        return value if (self._clock() - stored_at) < ttl else MISSING

    def get_stale(self, key: str) -> Any:
        with self._lock:
            entry = self._items.get(key)
        return MISSING if entry is None else entry[1]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
