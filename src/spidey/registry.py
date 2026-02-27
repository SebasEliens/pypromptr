"""PromptRegistry and PromptSource: registry API and InMemoryPrompts."""

from typing import Protocol

from spidey.prompts import (
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
    """Protocol for prompt backends: list keys and fetch prompt by key."""

    def keys(self) -> list[str]: ...
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
    """Registry that resolves prompts from a primary source and optional fallback."""

    def __init__(
        self,
        source: PromptSource,
        fallback: PromptSource | None = None,
    ) -> None:
        self._source = source
        self._fallback = fallback

    def get_prompt(self, key: str) -> PromptLike:
        try:
            return self._source.get_prompt(key)
        except KeyError:
            if self._fallback is None:
                raise
            return self._fallback.get_prompt(key)
