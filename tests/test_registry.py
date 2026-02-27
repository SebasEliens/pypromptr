"""Tests for PromptRegistry and InMemoryPrompts. User-perspective: get prompts by key."""

import pytest
from pydantic import BaseModel

from spidey import (
    InMemoryPrompts,
    PromptRegistry,
    RenderedPrompt,
    SimplePrompt,
    SimplePromptTemplate,
)


class MinimalMetadata(BaseModel):
    pass


def test_registry_from_in_memory_returns_prompt_by_key():
    """I build a registry from an in-memory mapping; when I ask for a key, I get that prompt."""
    welcome = SimplePrompt(metadata=MinimalMetadata(), content="Hello")
    source = InMemoryPrompts({"welcome": welcome})
    registry = PromptRegistry(source)
    prompt = registry.get_prompt("welcome")
    assert prompt is welcome
    assert prompt.content == "Hello"


def test_registry_get_renders_prompt_with_variables():
    """I ask the registry for a key with template variables; I get the rendered prompt."""
    greeting = SimplePromptTemplate(
        metadata=MinimalMetadata(), content="Hello, {{name}}!"
    )
    registry = PromptRegistry(InMemoryPrompts({"greeting": greeting}))
    rendered = registry.get("greeting", name="Alice")
    assert isinstance(rendered, RenderedPrompt)
    assert rendered.content == "Hello, Alice!"


def test_registry_fallback_when_key_missing_in_source():
    """I use a registry with a fallback; when a key is only in the fallback, I get that prompt."""
    only_in_source = SimplePrompt(
        metadata=MinimalMetadata(), content="From source"
    )
    only_in_fallback = SimplePrompt(
        metadata=MinimalMetadata(), content="From fallback"
    )
    source = InMemoryPrompts({"a": only_in_source})
    fallback = InMemoryPrompts({"b": only_in_fallback})
    registry = PromptRegistry(source, fallback=fallback)
    assert registry.get_prompt("a") is only_in_source
    assert registry.get_prompt("b") is only_in_fallback


def test_registry_raises_key_error_when_key_missing_in_both():
    """When a key is in neither source nor fallback, I get KeyError."""
    source = InMemoryPrompts({"a": SimplePrompt(metadata=MinimalMetadata(), content="")})
    fallback = InMemoryPrompts({"b": SimplePrompt(metadata=MinimalMetadata(), content="")})
    registry = PromptRegistry(source, fallback=fallback)
    with pytest.raises(KeyError, match="c"):
        registry.get_prompt("c")
