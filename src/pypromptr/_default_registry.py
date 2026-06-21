"""Module-level default registry: register_prompt, register_prompt_source, get_prompt, get, aget_prompt, aget, clear."""

import asyncio
import threading

from pypromptr.prompts import RenderedPrompt
from pypromptr.registry import PromptLike, PromptSource


class _DefaultRegistry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sources: list[PromptSource] = []  # index 0 = highest priority
        self._overrides: dict[str, PromptLike] = {}

    def register_prompt(self, key: str, prompt: PromptLike) -> None:
        with self._lock:
            self._overrides[key] = prompt

    def register_prompt_source(self, source: PromptSource) -> None:
        # Prepend so last-registered has highest priority. Never calls source.keys() — stays lazy.
        with self._lock:
            self._sources.insert(0, source)

    def get_prompt(self, key: str) -> PromptLike:
        # Snapshot inside lock, do I/O outside — never hold lock during a network call.
        with self._lock:
            overrides = dict(self._overrides)
            sources = list(self._sources)
        if key in overrides:
            return overrides[key]
        for source in sources:
            try:
                return source.get_prompt(key)
            except KeyError:
                continue
        raise KeyError(key)

    def get(self, key: str, **kwargs: object) -> RenderedPrompt:
        return self.get_prompt(key).render(**kwargs)

    async def aget_prompt(self, key: str) -> PromptLike:
        return await asyncio.to_thread(self.get_prompt, key)

    async def aget(self, key: str, **kwargs: object) -> RenderedPrompt:
        # render() is pure Python — no I/O — so no thread needed after the fetch.
        prompt = await self.aget_prompt(key)
        return prompt.render(**kwargs)

    def clear(self) -> None:
        with self._lock:
            self._sources.clear()
            self._overrides.clear()


_registry = _DefaultRegistry()
