"""Optional Redis cache with in-memory TTL fallback."""

from __future__ import annotations

import json
import threading
import time
from typing import Any

from app.config import get_settings


class _MemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            expires, value = item
            if expires and expires < time.time():
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: str, ttl: int = 3600) -> None:
        with self._lock:
            expires = time.time() + ttl if ttl else 0
            self._store[key] = (expires, value)


_memory = _MemoryCache()
_redis_client = None
_redis_checked = False


def _get_redis():
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    settings = get_settings()
    try:
        import redis

        client = redis.from_url(settings.redis_url, socket_connect_timeout=0.5)
        client.ping()
        _redis_client = client
    except Exception:
        _redis_client = None
    return _redis_client


def cache_get(key: str) -> Any | None:
    client = _get_redis()
    raw = None
    if client is not None:
        try:
            raw = client.get(key)
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
        except Exception:
            raw = None
    if raw is None:
        raw = _memory.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    raw = json.dumps(value)
    client = _get_redis()
    if client is not None:
        try:
            client.setex(key, ttl, raw)
            return
        except Exception:
            pass
    _memory.set(key, raw, ttl=ttl)


def cache_delete(key: str) -> None:
    client = _get_redis()
    if client is not None:
        try:
            client.delete(key)
        except Exception:
            pass
    with _memory._lock:
        _memory._store.pop(key, None)


def query_cache_key(query: str) -> str:
    return f"research:query:{query.strip().lower()}"
