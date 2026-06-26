"""pypromptr: prompt registry with swappable backends."""

from pypromptr.prompts import (
    Message,
    MessagesPrompt,
    MessagesPromptTemplate,
    RenderedPrompt,
    SimplePrompt,
    SimplePromptTemplate,
)
from pypromptr.sources.callable import CallablePromptSource
from pypromptr.sources.file import FilePromptMetadata, FilePrompts, FilePromptsConfig
from pypromptr.registry import InMemoryPrompts, PromptLike, PromptRegistry, PromptSource
from pypromptr._default_registry import _registry


def register_prompt(key: str, prompt: PromptLike) -> None:
    """Register a single prompt in the default registry. Overrides any source for the same key."""
    _registry.register_prompt(key, prompt)


def register_prompt_source(source: PromptSource) -> None:
    """Register a prompt source in the default registry. Last registered has highest priority."""
    _registry.register_prompt_source(source)


def get_prompt(key: str) -> PromptLike:
    """Return the prompt for key from the default registry. Raises KeyError if not found."""
    return _registry.get_prompt(key)


def get(key: str, **kwargs: object) -> RenderedPrompt:
    """Return the prompt for key rendered with the given template variables."""
    return _registry.get(key, **kwargs)


async def aget_prompt(key: str) -> PromptLike:
    """Async version of get_prompt; runs blocking source I/O in a thread pool."""
    return await _registry.aget_prompt(key)


async def aget(key: str, **kwargs: object) -> RenderedPrompt:
    """Async version of get; runs blocking source I/O in a thread pool."""
    return await _registry.aget(key, **kwargs)


def clear() -> None:
    """Remove all prompts and sources from the default registry. Useful in tests."""
    _registry.clear()


__all__ = [
    "CallablePromptSource",
    "FilePromptMetadata",
    "FilePrompts",
    "FilePromptsConfig",
    "InMemoryPrompts",
    "Message",
    "MessagesPrompt",
    "MessagesPromptTemplate",
    "PromptLike",
    "PromptRegistry",
    "PromptSource",
    "RenderedPrompt",
    "SimplePrompt",
    "SimplePromptTemplate",
    # default registry
    "aget",
    "aget_prompt",
    "clear",
    "get",
    "get_prompt",
    "register_prompt",
    "register_prompt_source",
]
