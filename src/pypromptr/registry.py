"""PromptRegistry and PromptSource: registry API and InMemoryPrompts."""
from __future__ import annotations
import asyncio
from typing import Protocol

from pypromptr.prompts import (
    MessagesPrompt,
    MessagesPromptTemplate,
    RenderedPrompt,
    SimplePrompt,
    SimplePromptTemplate,
)

PromptLike = (
    SimplePrompt
    | SimplePromptTemplate
    | MessagesPrompt
    | MessagesPromptTemplate
)


class PromptSource(Protocol):
    """Protocol for prompt backends. Only get_prompt is required.

    KeyError contract
    -----------------
    get_prompt must raise ``KeyError(key)`` when the key does not exist in
    this source. The registry catches KeyError to fall through to the next
    source in the chain. Raising any other exception for a missing key
    (e.g. FileNotFoundError, ValueError) will break the chain and propagate
    to the caller — convert those to KeyError inside your implementation.
    Other errors (network failures, parse errors, etc.) may propagate freely.

    Optional: keys() -> list[str]
    ------------------------------
    Implement keys() to support key enumeration. When present, PromptRegistry
    uses it to build the known key set at init and to support validate_at_init.
    Sources without keys() are skipped for enumeration but still participate
    fully in resolution.
    """

    def get_prompt(self, key: str) -> PromptLike: ...


class InMemoryPrompts:
    """PromptSource that holds a dict of key -> prompt; no I/O."""

    def __init__(self, mapping: dict[str, PromptLike]) -> None:
        self._prompts = dict(mapping)

    def keys(self) -> list[str]:
        return list(self._prompts.keys())

    def get_prompt(self, key: str) -> PromptLike:
        if key not in self._prompts:
            raise KeyError(key)
        return self._prompts[key]


class PromptRegistry:
    """Registry that resolves prompts from one or more sources tried in order (first wins)."""

    def __init__(
        self,
        *sources: PromptSource,
        validate_at_init: bool = False,
    ) -> None:
        # Note: __init__ calls source.keys() synchronously for each source. For remote sources
        # (e.g. LangFuse) inside an async context, construct via:
        #   registry = await asyncio.to_thread(PromptRegistry, source)
        self._sources = list(sources)
        self._key_set = sorted(
            set().union(*(set(s.keys()) for s in sources if hasattr(s, "keys")))
        )
        if validate_at_init:
            for key in self._key_set:
                self.get_prompt(key)

    def keys(self) -> list[str]:
        """Return the union of keys across all sources (built at init)."""
        return self._key_set

    def __add__(self, other: PromptRegistry) -> PromptRegistry:
        """Combine two registries; sources are merged and tried in order (self first)."""
        return PromptRegistry(*self._sources, *other._sources)

    def get_prompt(self, key: str) -> PromptLike:
        for source in self._sources:
            try:
                return source.get_prompt(key)
            except KeyError:
                continue
        raise KeyError(key)

    def get(self, key: str, **kwargs: object) -> RenderedPrompt:
        """Return the prompt for key, rendered with the given template variables."""
        return self.get_prompt(key).render(**kwargs)

    async def aget_prompt(self, key: str) -> PromptLike:
        """Async version of get_prompt; runs blocking source I/O in a thread pool."""
        return await asyncio.to_thread(self.get_prompt, key)

    async def aget(self, key: str, **kwargs: object) -> RenderedPrompt:
        """Async version of get; runs blocking source I/O in a thread pool."""
        prompt = await self.aget_prompt(key)
        return prompt.render(**kwargs)
