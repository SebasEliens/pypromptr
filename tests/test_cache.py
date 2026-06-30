"""Tests for CachedPromptSource — TTL, SWR, invalidation, thread safety, async."""

from __future__ import annotations

import asyncio
import threading
import time

import pytest
from pydantic import BaseModel

from pypromptr import CachedPromptSource, InMemoryPrompts, PromptRegistry, SimplePrompt
from pypromptr.registry import PromptLike


class MinimalMetadata(BaseModel):
    pass


def _prompt(content: str) -> SimplePrompt:
    return SimplePrompt(metadata=MinimalMetadata(), content=content)


# ---------------------------------------------------------------------------
# Spy source — counts get_prompt calls and supports content mutation
# ---------------------------------------------------------------------------


class SpySource:
    def __init__(self, prompts: dict[str, str]) -> None:
        self._prompts = dict(prompts)
        self.call_count: dict[str, int] = {}

    def keys(self) -> list[str]:
        return list(self._prompts.keys())

    def get_prompt(self, key: str) -> PromptLike:
        self.call_count[key] = self.call_count.get(key, 0) + 1
        if key not in self._prompts:
            raise KeyError(key)
        return _prompt(self._prompts[key])

    async def aget_prompt(self, key: str) -> PromptLike:
        return self.get_prompt(key)


# ---------------------------------------------------------------------------
# Basic fetch and caching
# ---------------------------------------------------------------------------


def test_first_call_fetches_from_source():
    source = SpySource({"key": "hello"})
    cached = CachedPromptSource(source, ttl=60)
    result = cached.get_prompt("key")
    assert result.content == "hello"  # type: ignore[attr-defined]
    assert source.call_count["key"] == 1


def test_second_call_hits_cache():
    source = SpySource({"key": "hello"})
    cached = CachedPromptSource(source, ttl=60)
    cached.get_prompt("key")
    cached.get_prompt("key")
    assert source.call_count["key"] == 1


def test_cache_returns_updated_value_after_ttl_expiry():
    source = SpySource({"key": "v1"})
    cached = CachedPromptSource(source, ttl=0.01)  # 10ms TTL
    assert cached.get_prompt("key").content == "v1"  # type: ignore[attr-defined]
    source._prompts["key"] = "v2"
    time.sleep(0.02)
    assert cached.get_prompt("key").content == "v2"  # type: ignore[attr-defined]
    assert source.call_count["key"] == 2


def test_ttl_none_caches_forever():
    source = SpySource({"key": "v1"})
    cached = CachedPromptSource(source, ttl=None)
    cached.get_prompt("key")
    source._prompts["key"] = "v2"
    time.sleep(0.01)
    assert cached.get_prompt("key").content == "v1"  # type: ignore[attr-defined]
    assert source.call_count["key"] == 1


def test_key_error_propagates_and_is_not_cached():
    source = SpySource({})
    cached = CachedPromptSource(source, ttl=60)
    with pytest.raises(KeyError):
        cached.get_prompt("missing")
    with pytest.raises(KeyError):
        cached.get_prompt("missing")
    assert source.call_count.get("missing", 0) == 2  # fetched both times


# ---------------------------------------------------------------------------
# keys() caching
# ---------------------------------------------------------------------------


class SpyKeysSource(SpySource):
    def __init__(self, prompts: dict[str, str]) -> None:
        super().__init__(prompts)
        self.keys_call_count = 0

    def keys(self) -> list[str]:
        self.keys_call_count += 1
        return list(self._prompts.keys())


def test_keys_cached_within_ttl():
    source = SpyKeysSource({"a": "A", "b": "B"})
    cached = CachedPromptSource(source, ttl=60)
    assert set(cached.keys()) == {"a", "b"}
    assert set(cached.keys()) == {"a", "b"}
    assert source.keys_call_count == 1


def test_keys_re_fetched_after_ttl():
    source = SpyKeysSource({"a": "A"})
    cached = CachedPromptSource(source, ttl=0.01)
    cached.keys()
    time.sleep(0.02)
    source._prompts["b"] = "B"
    assert "b" in cached.keys()
    assert source.keys_call_count == 2


def test_keys_returns_empty_for_source_without_keys():
    class NoKeysSource:
        def get_prompt(self, key: str) -> PromptLike:
            raise KeyError(key)

    cached = CachedPromptSource(NoKeysSource())  # type: ignore[arg-type]
    assert cached.keys() == []


# ---------------------------------------------------------------------------
# Invalidation
# ---------------------------------------------------------------------------


def test_invalidate_evicts_key():
    source = SpySource({"key": "v1"})
    cached = CachedPromptSource(source, ttl=60)
    cached.get_prompt("key")
    source._prompts["key"] = "v2"
    cached.invalidate("key")
    assert cached.get_prompt("key").content == "v2"  # type: ignore[attr-defined]
    assert source.call_count["key"] == 2


def test_invalidate_unknown_key_is_noop():
    cached = CachedPromptSource(InMemoryPrompts({}))
    cached.invalidate("nonexistent")  # must not raise


def test_clear_evicts_all():
    source = SpySource({"a": "A", "b": "B"})
    cached = CachedPromptSource(source, ttl=60)
    cached.get_prompt("a")
    cached.get_prompt("b")
    source._prompts["a"] = "A2"
    source._prompts["b"] = "B2"
    cached.clear()
    assert cached.get_prompt("a").content == "A2"  # type: ignore[attr-defined]
    assert cached.get_prompt("b").content == "B2"  # type: ignore[attr-defined]


def test_clear_also_evicts_keys_cache():
    source = SpyKeysSource({"a": "A"})
    cached = CachedPromptSource(source, ttl=60)
    cached.keys()
    cached.clear()
    source._prompts["b"] = "B"
    assert "b" in cached.keys()
    assert source.keys_call_count == 2


# ---------------------------------------------------------------------------
# TTL strategy — blocking re-fetch on expiry
# ---------------------------------------------------------------------------


def test_ttl_strategy_blocks_on_expiry():
    """After TTL expiry, the next caller fetches synchronously (no stale return)."""
    fetched: list[str] = []

    class TrackingSource:
        def keys(self): return ["key"]
        def get_prompt(self, key: str) -> PromptLike:
            fetched.append(key)
            return _prompt("content")

    cached = CachedPromptSource(TrackingSource(), ttl=0.01, strategy="ttl")
    cached.get_prompt("key")
    time.sleep(0.02)
    cached.get_prompt("key")
    assert fetched.count("key") == 2


# ---------------------------------------------------------------------------
# SWR strategy
# ---------------------------------------------------------------------------


def test_swr_returns_stale_on_expiry():
    source = SpySource({"key": "v1"})
    cached = CachedPromptSource(source, ttl=0.01, strategy="swr")
    cached.get_prompt("key")
    source._prompts["key"] = "v2"
    time.sleep(0.02)
    # Should return stale immediately, not block
    result = cached.get_prompt("key")
    assert result.content == "v1"  # type: ignore[attr-defined]


def test_swr_refreshes_in_background():
    refresh_done = threading.Event()
    original_get = None

    class SlowSource:
        def keys(self): return ["key"]
        def get_prompt(self, key: str) -> PromptLike:
            p = _prompt("v2")
            refresh_done.set()
            return p

    source = SlowSource()
    cached = CachedPromptSource(source, ttl=0.01, strategy="swr")
    # Seed the cache manually with v1
    with cached._lock:
        from pypromptr.cache import _CacheEntry
        cached._cache["key"] = _CacheEntry(
            prompt=_prompt("v1"), fetched_at=time.monotonic() - 1.0
        )
    # First call returns stale and triggers refresh
    result = cached.get_prompt("key")
    assert result.content == "v1"  # type: ignore[attr-defined]
    # Wait for background refresh to complete
    assert refresh_done.wait(timeout=2.0), "Background refresh did not complete"
    time.sleep(0.01)  # let cache write settle
    assert cached.get_prompt("key").content == "v2"  # type: ignore[attr-defined]


def test_swr_background_refresh_failure_keeps_stale():
    fail_count = 0

    class FailingSource:
        def keys(self): return ["key"]
        def get_prompt(self, key: str) -> PromptLike:
            nonlocal fail_count
            if fail_count == 0:
                fail_count += 1
                return _prompt("v1")
            raise RuntimeError("source unavailable")

    cached = CachedPromptSource(FailingSource(), ttl=0.01, strategy="swr")
    cached.get_prompt("key")  # warms cache with v1
    time.sleep(0.02)
    with pytest.warns(UserWarning, match="background refresh"):
        cached.get_prompt("key")   # triggers failing background refresh
        time.sleep(0.05)           # wait for background thread

    # Stale v1 must still be in cache
    assert cached.get_prompt("key").content == "v1"  # type: ignore[attr-defined]


def test_swr_background_refresh_evicts_on_key_error():
    """If source raises KeyError during background refresh, entry is evicted."""
    call_count = 0

    class DisappearingSource:
        def keys(self): return ["key"]
        def get_prompt(self, key: str) -> PromptLike:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _prompt("v1")
            raise KeyError(key)

    cached = CachedPromptSource(DisappearingSource(), ttl=0.01, strategy="swr")
    cached.get_prompt("key")
    time.sleep(0.02)
    cached.get_prompt("key")   # triggers background refresh that raises KeyError
    time.sleep(0.05)
    with pytest.raises(KeyError):
        cached.get_prompt("key")


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


def test_concurrent_cold_miss_fetches_once():
    """Under concurrent load, the source should be called exactly once per key.

    The per-key lock means the first thread fetches; all others wait on the
    lock and then hit the cache on re-check — no double-fetch.
    """
    fetch_count = 0
    # Gate lets all threads start their get_prompt call before the first one
    # acquires the key lock, maximising contention
    start_gate = threading.Barrier(10)

    class CountingSource:
        def keys(self): return ["key"]
        def get_prompt(self, key: str) -> PromptLike:
            nonlocal fetch_count
            fetch_count += 1
            time.sleep(0.02)  # hold the key lock briefly so others queue up
            return _prompt("content")

    cached = CachedPromptSource(CountingSource(), ttl=60)
    results: list[PromptLike] = []
    errors: list[Exception] = []

    def fetch():
        start_gate.wait()  # all threads enter get_prompt at roughly the same time
        try:
            results.append(cached.get_prompt("key"))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=fetch) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(results) == 10
    assert fetch_count == 1  # per-key lock ensures only one actual fetch


# ---------------------------------------------------------------------------
# Async
# ---------------------------------------------------------------------------


async def test_async_get_prompt_basic():
    source = SpySource({"key": "hello"})
    cached = CachedPromptSource(source, ttl=60)
    result = await cached.aget_prompt("key")
    assert result.content == "hello"  # type: ignore[attr-defined]
    result2 = await cached.aget_prompt("key")
    assert result2.content == "hello"  # type: ignore[attr-defined]
    assert source.call_count["key"] == 1


async def test_async_uses_aget_prompt_when_available():
    """aget_prompt should call source.aget_prompt directly when available."""
    async_calls: list[str] = []

    class AsyncSource:
        def keys(self): return ["key"]
        def get_prompt(self, key: str) -> PromptLike:
            raise AssertionError("sync get_prompt must not be called")
        async def aget_prompt(self, key: str) -> PromptLike:
            async_calls.append(key)
            return _prompt("async-content")

    cached = CachedPromptSource(AsyncSource(), ttl=60)
    result = await cached.aget_prompt("key")
    assert result.content == "async-content"  # type: ignore[attr-defined]
    assert async_calls == ["key"]


async def test_async_falls_back_to_sync_source():
    """aget_prompt wraps sync source in a thread when aget_prompt is absent."""

    class SyncOnlySource:
        def keys(self): return ["key"]
        def get_prompt(self, key: str) -> PromptLike:
            return _prompt("sync-content")

    cached = CachedPromptSource(SyncOnlySource(), ttl=60)
    result = await cached.aget_prompt("key")
    assert result.content == "sync-content"  # type: ignore[attr-defined]


async def test_async_swr_returns_stale_and_refreshes():
    refresh_done = asyncio.Event()

    class AsyncSource:
        version = "v1"
        def keys(self): return ["key"]
        async def aget_prompt(self, key: str) -> PromptLike:
            p = _prompt(self.version)
            refresh_done.set()
            return p

    source = AsyncSource()
    cached = CachedPromptSource(source, ttl=0.01, strategy="swr")
    # Warm cache
    await cached.aget_prompt("key")
    source.version = "v2"
    await asyncio.sleep(0.02)
    # Stale return + background refresh
    result = await cached.aget_prompt("key")
    assert result.content == "v1"  # type: ignore[attr-defined]
    await asyncio.wait_for(refresh_done.wait(), timeout=2.0)
    await asyncio.sleep(0.01)
    assert (await cached.aget_prompt("key")).content == "v2"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Works with PromptRegistry
# ---------------------------------------------------------------------------


def test_integration_with_prompt_registry():
    source = SpySource({"welcome": "Hello!"})
    registry = PromptRegistry(CachedPromptSource(source, ttl=60))
    registry.get_prompt("welcome")
    registry.get_prompt("welcome")
    assert source.call_count["welcome"] == 1


# ---------------------------------------------------------------------------
# Invalid strategy raises
# ---------------------------------------------------------------------------


def test_invalid_strategy_raises():
    with pytest.raises(ValueError, match="strategy"):
        CachedPromptSource(InMemoryPrompts({}), strategy="invalid")  # type: ignore[arg-type]
