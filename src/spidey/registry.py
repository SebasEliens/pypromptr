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
        *,
        validate_at_init: bool = False,
    ) -> None:
        self._source = source
        self._fallback = fallback
        # Build key set at init from source and fallback keys only (no prompt bodies loaded).
        self._key_set = sorted(
            set(source.keys()) | (set(fallback.keys()) if fallback else set())
        )
        if validate_at_init:
            for key in self._key_set:
                self.get_prompt(key)

    def keys(self) -> list[str]:
        """Return the union of keys from source and fallback (built at init)."""
        return self._key_set

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
