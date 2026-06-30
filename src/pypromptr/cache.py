"""CachedPromptSource: TTL and stale-while-revalidate caching wrapper for any PromptSource."""

from __future__ import annotations

import asyncio
import threading
import time
import warnings
from dataclasses import dataclass, field
from typing import Literal

from pypromptr.registry import PromptLike, PromptSource


@dataclass
class _CacheEntry:
    prompt: PromptLike
    fetched_at: float
    refreshing: bool = False


class CachedPromptSource:
    """Caching wrapper that sits in front of any PromptSource.

    Two strategies
    --------------
    ``"ttl"`` (default)
        Serve cached value within TTL; block caller on first fetch and on
        every expiry. Simple and predictable.

    ``"swr"`` (stale-while-revalidate)
        Always return cached value immediately after the first fetch.
        When the TTL expires, serve the stale value *and* trigger a
        background refresh so the *next* caller gets a fresh value. The
        caller that triggers the refresh never blocks. Prefer this for
        remote sources (HTTP, S3, LangSmith) where a blocking miss on
        expiry would be expensive.

    Keys caching
    ------------
    The result of ``keys()`` is cached with the same TTL. If the wrapped
    source does not implement ``keys()``, an empty list is returned.

    Error handling
    --------------
    ``KeyError`` is never cached — it propagates immediately.
    Other fetch errors are not cached either. For SWR background refresh
    failures, the stale entry is kept (rather than evicted) and a warning
    is emitted; the next TTL expiry will trigger another refresh attempt.

    Example::

        from pypromptr.cache import CachedPromptSource
        from pypromptr.sources.s3 import S3Prompts

        source = CachedPromptSource(S3Prompts(...), ttl=300, strategy="swr")
        registry = PromptRegistry(source)
    """

    def __init__(
        self,
        source: PromptSource,
        ttl: float | None = 300,
        strategy: Literal["ttl", "swr"] = "ttl",
    ) -> None:
        if strategy not in ("ttl", "swr"):
            raise ValueError(f"strategy must be 'ttl' or 'swr', got {strategy!r}")
        self._source = source
        self._ttl = ttl
        self._strategy = strategy
        self._cache: dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()
        # Per-key locks prevent thundering herd on concurrent cold misses (sync path)
        self._key_locks: dict[str, threading.Lock] = {}
        # keys() cache
        self._keys_cache: list[str] | None = None
        self._keys_fetched_at: float | None = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_expired(self, fetched_at: float) -> bool:
        if self._ttl is None:
            return False
        return time.monotonic() - fetched_at >= self._ttl

    def _get_key_lock(self, key: str) -> threading.Lock:
        with self._lock:
            if key not in self._key_locks:
                self._key_locks[key] = threading.Lock()
            return self._key_locks[key]

    # ------------------------------------------------------------------
    # keys()
    # ------------------------------------------------------------------

    def keys(self) -> list[str]:
        """Return keys from the wrapped source, cached with the same TTL."""
        with self._lock:
            if (
                self._keys_cache is not None
                and self._keys_fetched_at is not None
                and not self._is_expired(self._keys_fetched_at)
            ):
                return list(self._keys_cache)

        source_keys = self._source.keys() if hasattr(self._source, "keys") else []
        with self._lock:
            self._keys_cache = list(source_keys)
            self._keys_fetched_at = time.monotonic()
        return list(source_keys)

    # ------------------------------------------------------------------
    # Sync get_prompt
    # ------------------------------------------------------------------

    def get_prompt(self, key: str) -> PromptLike:
        """Return the prompt for key, fetching from source only on a cache miss or TTL expiry."""
        # Fast path — check cache before acquiring per-key lock
        with self._lock:
            entry = self._cache.get(key)
            if entry is not None:
                if not self._is_expired(entry.fetched_at):
                    return entry.prompt
                if self._strategy == "swr":
                    if not entry.refreshing:
                        entry.refreshing = True
                        threading.Thread(
                            target=self._background_refresh_sync,
                            args=(key,),
                            daemon=True,
                        ).start()
                    return entry.prompt  # return stale while refresh runs

        # Slow path — acquire per-key lock so concurrent callers wait rather
        # than all fetching simultaneously (thundering herd prevention)
        key_lock = self._get_key_lock(key)
        with key_lock:
            # Re-check: another thread may have populated the cache while we waited
            with self._lock:
                entry = self._cache.get(key)
                if entry is not None and not self._is_expired(entry.fetched_at):
                    return entry.prompt

            prompt = self._source.get_prompt(key)  # KeyError / other errors propagate
            with self._lock:
                self._cache[key] = _CacheEntry(prompt=prompt, fetched_at=time.monotonic())
            return prompt

    def _background_refresh_sync(self, key: str) -> None:
        try:
            prompt = self._source.get_prompt(key)
            with self._lock:
                self._cache[key] = _CacheEntry(prompt=prompt, fetched_at=time.monotonic())
        except KeyError:
            # Prompt was deleted from the source — evict
            with self._lock:
                self._cache.pop(key, None)
        except Exception:
            # Transient error — keep stale, clear refreshing flag so next
            # expiry will trigger another attempt
            warnings.warn(
                f"CachedPromptSource: background refresh for '{key}' failed; "
                "keeping stale entry. It will be retried on next TTL expiry.",
                stacklevel=2,
            )
            with self._lock:
                if key in self._cache:
                    self._cache[key].refreshing = False

    # ------------------------------------------------------------------
    # Async aget_prompt
    # ------------------------------------------------------------------

    async def aget_prompt(self, key: str) -> PromptLike:
        """Async version of get_prompt; respects the same TTL / SWR strategy."""
        # Fast path
        with self._lock:
            entry = self._cache.get(key)
            if entry is not None:
                if not self._is_expired(entry.fetched_at):
                    return entry.prompt
                if self._strategy == "swr":
                    if not entry.refreshing:
                        entry.refreshing = True
                        loop = asyncio.get_running_loop()
                        loop.create_task(self._background_refresh_async(key))
                    return entry.prompt

        # Slow path — no per-key async lock here; double-fetch on concurrent
        # cold misses is acceptable (idempotent and rare)
        if hasattr(self._source, "aget_prompt"):
            prompt = await self._source.aget_prompt(key)
        else:
            prompt = await asyncio.to_thread(self._source.get_prompt, key)

        with self._lock:
            # Only write if a fresher entry hasn't arrived while we awaited
            existing = self._cache.get(key)
            if existing is None or self._is_expired(existing.fetched_at):
                self._cache[key] = _CacheEntry(prompt=prompt, fetched_at=time.monotonic())
        return prompt

    async def _background_refresh_async(self, key: str) -> None:
        try:
            if hasattr(self._source, "aget_prompt"):
                prompt = await self._source.aget_prompt(key)
            else:
                prompt = await asyncio.to_thread(self._source.get_prompt, key)
            with self._lock:
                self._cache[key] = _CacheEntry(prompt=prompt, fetched_at=time.monotonic())
        except KeyError:
            with self._lock:
                self._cache.pop(key, None)
        except Exception:
            warnings.warn(
                f"CachedPromptSource: async background refresh for '{key}' failed; "
                "keeping stale entry. It will be retried on next TTL expiry.",
                stacklevel=2,
            )
            with self._lock:
                if key in self._cache:
                    self._cache[key].refreshing = False

    # ------------------------------------------------------------------
    # Invalidation
    # ------------------------------------------------------------------

    def invalidate(self, key: str) -> None:
        """Evict a single key from the cache. Next call will fetch from source."""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Evict all cached prompts and the cached key list."""
        with self._lock:
            self._cache.clear()
            self._keys_cache = None
            self._keys_fetched_at = None
