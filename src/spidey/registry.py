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

    def keys(self) -> list[str]:
        """Return the union of keys from source and fallback (no prompt bodies loaded)."""
        result = set(self._source.keys())
        if self._fallback is not None:
            result |= set(self._fallback.keys())
        return sorted(result)

    def __add__(self, other: "PromptRegistry") -> "PromptRegistry":
        """Combine two registries; resolution is first-wins (self then other)."""
        return PromptRegistry(source=self, fallback=other)

    def get_prompt(self, key: str) -> PromptLike:
        try:
            return self._source.get_prompt(key)
        except KeyError:
            if self._fallback is None:
                raise
            return self._fallback.get_prompt(key)

    def get(self, key: str, **kwargs: object) -> RenderedPrompt:
        """Return the prompt for key, rendered with the given template variables."""
        return self.get_prompt(key).render(**kwargs)
