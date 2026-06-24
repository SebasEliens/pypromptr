"""CallablePromptSource: a dict of callables that return prompts on demand."""
from __future__ import annotations
import asyncio
import inspect
from collections.abc import Callable, Coroutine
from typing import Any

from pypromptr.registry import PromptLike

SyncCallable = Callable[[], PromptLike]
AsyncCallable = Callable[[], Coroutine[Any, Any, PromptLike]]
AnyCallable = SyncCallable | AsyncCallable


class CallablePromptSource:
    """PromptSource backed by a dict of callables invoked on demand.

    Each value in the mapping is a zero-argument callable that returns a
    PromptLike. Both sync and async callables are supported:

    - Sync callables are called directly in get_prompt and run in a thread
      pool in aget_prompt.
    - Async callables are awaited directly in aget_prompt. Calling get_prompt
      on a key backed by an async callable raises TypeError — use aget_prompt.

    This is the most flexible source: wrap any custom logic, one-off fetches,
    or dynamic prompt generation not covered by other sources.

    KeyError contract: raises KeyError(key) for unknown keys, consistent with
    the PromptSource protocol.
    """

    def __init__(self, mapping: dict[str, AnyCallable]) -> None:
        self._callables = dict(mapping)

    def keys(self) -> list[str]:
        return list(self._callables.keys())

    def get_prompt(self, key: str) -> PromptLike:
        if key not in self._callables:
            raise KeyError(key)
        fn = self._callables[key]
        if inspect.iscoroutinefunction(fn):
            raise TypeError(
                f"Prompt '{key}' is backed by an async callable; use aget_prompt()."
            )
        return fn()

    async def aget_prompt(self, key: str) -> PromptLike:
        if key not in self._callables:
            raise KeyError(key)
        fn = self._callables[key]
        if inspect.iscoroutinefunction(fn):
            return await fn()
        return await asyncio.to_thread(fn)
