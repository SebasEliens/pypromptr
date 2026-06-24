"""Tests for PromptRegistry and InMemoryPrompts. User-perspective: get prompts by key."""

import asyncio
import pytest
from pydantic import BaseModel

from pypromptr import (
    InMemoryPrompts,
    PromptRegistry,
    RenderedPrompt,
    SimplePrompt,
    SimplePromptTemplate,
)


class MinimalMetadata(BaseModel):
    pass


def test_registry_keys_returns_union_of_all_sources():
    """I can list all keys from a registry without loading prompt bodies; keys from all sources are combined."""
    source_a = InMemoryPrompts({
        "a": SimplePrompt(metadata=MinimalMetadata(), content=""),
        "b": SimplePrompt(metadata=MinimalMetadata(), content=""),
    })
    source_b = InMemoryPrompts({
        "c": SimplePrompt(metadata=MinimalMetadata(), content=""),
    })
    registry = PromptRegistry(source_a, source_b)
    assert set(registry.keys()) == {"a", "b", "c"}


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


def test_registry_falls_through_to_next_source_when_key_missing():
    """When a key is missing in the first source, the next source is tried."""
    only_in_first = SimplePrompt(metadata=MinimalMetadata(), content="From first")
    only_in_second = SimplePrompt(metadata=MinimalMetadata(), content="From second")
    first = InMemoryPrompts({"a": only_in_first})
    second = InMemoryPrompts({"b": only_in_second})
    registry = PromptRegistry(first, second)
    assert registry.get_prompt("a") is only_in_first
    assert registry.get_prompt("b") is only_in_second


def test_registry_raises_key_error_when_key_missing_in_all_sources():
    """When a key is in none of the sources, KeyError is raised."""
    source_a = InMemoryPrompts({"a": SimplePrompt(metadata=MinimalMetadata(), content="")})
    source_b = InMemoryPrompts({"b": SimplePrompt(metadata=MinimalMetadata(), content="")})
    registry = PromptRegistry(source_a, source_b)
    with pytest.raises(KeyError, match="c"):
        registry.get_prompt("c")


def test_combined_registry_resolves_first_then_second():
    """I combine two registries with +; keys resolve from the first, then the second (first-wins)."""
    prompt_a = SimplePrompt(metadata=MinimalMetadata(), content="From first")
    prompt_b = SimplePrompt(metadata=MinimalMetadata(), content="From second")
    first = PromptRegistry(InMemoryPrompts({"a": prompt_a}))
    second = PromptRegistry(InMemoryPrompts({"b": prompt_b}))
    combined = first + second
    assert combined.get_prompt("a") is prompt_a
    assert combined.get_prompt("b") is prompt_b


def test_combined_registry_first_wins_on_overlapping_key():
    """When both registries have the same key, the first registry wins."""
    prompt_first = SimplePrompt(metadata=MinimalMetadata(), content="First wins")
    prompt_second = SimplePrompt(metadata=MinimalMetadata(), content="Second")
    first = PromptRegistry(InMemoryPrompts({"shared": prompt_first}))
    second = PromptRegistry(InMemoryPrompts({"shared": prompt_second}))
    combined = first + second
    assert combined.get_prompt("shared") is prompt_first


def test_registry_three_sources_tried_in_order():
    """With three sources, resolution falls through each in order until found."""
    prompt_c = SimplePrompt(metadata=MinimalMetadata(), content="From third")
    registry = PromptRegistry(
        InMemoryPrompts({"a": SimplePrompt(metadata=MinimalMetadata(), content="")}),
        InMemoryPrompts({"b": SimplePrompt(metadata=MinimalMetadata(), content="")}),
        InMemoryPrompts({"c": prompt_c}),
    )
    assert registry.get_prompt("c") is prompt_c


def test_registry_validate_at_init_fetches_each_key():
    """With validate_at_init=True, the registry validates that each key is fetchable at construction."""
    source = InMemoryPrompts({
        "a": SimplePrompt(metadata=MinimalMetadata(), content=""),
    })
    registry = PromptRegistry(source, validate_at_init=True)
    assert registry.keys() == ["a"]
    assert registry.get_prompt("a").content == ""


def test_registry_validate_at_init_raises_when_key_not_fetchable():
    """With validate_at_init=True, if a key is not fetchable, construction raises."""
    class BrokenSource:
        def keys(self):
            return ["missing"]

        def get_prompt(self, key):
            raise KeyError(key)

    with pytest.raises(KeyError, match="missing"):
        PromptRegistry(BrokenSource(), validate_at_init=True)


def test_listing_keys_does_not_load_prompt_bodies():
    """I can list all keys without loading any prompt content; only key discovery runs (e.g. for lazy/file sources)."""
    fetched: list[str] = []

    class TrackingSource:
        """Source that records which keys were requested via get_prompt."""

        def __init__(self, mapping):
            self._prompts = dict(mapping)

        def keys(self):
            return list(self._prompts.keys())

        def get_prompt(self, key):
            fetched.append(key)
            if key not in self._prompts:
                raise KeyError(key)
            return self._prompts[key]

    prompt_a = SimplePrompt(metadata=MinimalMetadata(), content="A")
    prompt_b = SimplePrompt(metadata=MinimalMetadata(), content="B")
    source = TrackingSource({"a": prompt_a, "b": prompt_b})
    registry = PromptRegistry(source)
    assert registry.keys() == ["a", "b"]
    assert fetched == [], "keys() must not call get_prompt; no prompt bodies loaded"


def test_get_prompt_loads_only_the_requested_key():
    """When I ask for one prompt by key, only that key is loaded (e.g. one file or one API call), not all prompts."""
    fetched: list[str] = []

    class TrackingSource:
        def __init__(self, mapping):
            self._prompts = dict(mapping)

        def keys(self):
            return list(self._prompts.keys())

        def get_prompt(self, key):
            fetched.append(key)
            if key not in self._prompts:
                raise KeyError(key)
            return self._prompts[key]

    source = TrackingSource({
        "a": SimplePrompt(metadata=MinimalMetadata(), content="A"),
        "b": SimplePrompt(metadata=MinimalMetadata(), content="B"),
    })
    registry = PromptRegistry(source)
    _ = registry.get_prompt("a")
    assert fetched == ["a"]
    _ = registry.get_prompt("b")
    assert fetched == ["a", "b"], "each get_prompt(key) loads only that key"


# --- async ---

def test_registry_aget_prompt_returns_same_result_as_get_prompt():
    """aget_prompt returns the same prompt object as the sync get_prompt."""
    prompt = SimplePrompt(metadata=MinimalMetadata(), content="Hello")
    registry = PromptRegistry(InMemoryPrompts({"key": prompt}))
    result = asyncio.run(registry.aget_prompt("key"))
    assert result is prompt


def test_registry_aget_renders_prompt_with_template_variables():
    """aget() returns a rendered prompt with variables substituted."""
    registry = PromptRegistry(InMemoryPrompts({
        "greeting": SimplePromptTemplate(metadata=MinimalMetadata(), content="Hello, {{name}}!"),
    }))
    rendered = asyncio.run(registry.aget("greeting", name="Alice"))
    assert isinstance(rendered, RenderedPrompt)
    assert rendered.content == "Hello, Alice!"


def test_registry_aget_prompt_raises_key_error_for_missing_key():
    """aget_prompt raises KeyError when the key is in none of the sources."""
    registry = PromptRegistry(InMemoryPrompts({"a": SimplePrompt(metadata=MinimalMetadata(), content="")}))
    with pytest.raises(KeyError, match="missing"):
        asyncio.run(registry.aget_prompt("missing"))


def test_registry_aget_prompt_falls_through_to_next_source():
    """aget_prompt falls through to the next source when the key is missing in the first."""
    fallback_prompt = SimplePrompt(metadata=MinimalMetadata(), content="From second")
    first = InMemoryPrompts({"a": SimplePrompt(metadata=MinimalMetadata(), content="")})
    second = InMemoryPrompts({"b": fallback_prompt})
    registry = PromptRegistry(first, second)
    result = asyncio.run(registry.aget_prompt("b"))
    assert result is fallback_prompt


def test_registry_aget_prompt_with_file_source(tmp_path):
    """aget_prompt works with FilePrompts, running blocking file I/O in a thread pool."""
    from pypromptr import FilePrompts
    (tmp_path / "hello.md").write_text("Hello from file")
    registry = PromptRegistry(FilePrompts(tmp_path))
    result = asyncio.run(registry.aget_prompt("hello"))
    assert result.content == "Hello from file"
