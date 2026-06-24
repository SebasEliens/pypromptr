"""Tests for CallablePromptSource."""
import asyncio
import pytest
from pydantic import BaseModel

from pypromptr import CallablePromptSource, PromptRegistry, SimplePrompt


class Meta(BaseModel):
    pass


def make_prompt(content: str) -> SimplePrompt:
    return SimplePrompt(metadata=Meta(), content=content)


# --- sync callables ---

def test_callable_source_keys_returns_mapping_keys():
    source = CallablePromptSource({
        "a": lambda: make_prompt("A"),
        "b": lambda: make_prompt("B"),
    })
    assert set(source.keys()) == {"a", "b"}


def test_callable_source_get_prompt_invokes_callable():
    prompt = make_prompt("hello")
    source = CallablePromptSource({"greet": lambda: prompt})
    assert source.get_prompt("greet") is prompt


def test_callable_source_get_prompt_raises_key_error_for_unknown_key():
    source = CallablePromptSource({"a": lambda: make_prompt("A")})
    with pytest.raises(KeyError, match="missing"):
        source.get_prompt("missing")


def test_callable_source_get_prompt_raises_type_error_for_async_callable():
    async def async_fn() -> SimplePrompt:
        return make_prompt("async")

    source = CallablePromptSource({"x": async_fn})
    with pytest.raises(TypeError, match="async callable"):
        source.get_prompt("x")


# --- async callables ---

def test_callable_source_aget_prompt_awaits_async_callable():
    async def async_fn() -> SimplePrompt:
        return make_prompt("from async")

    source = CallablePromptSource({"x": async_fn})
    result = asyncio.run(source.aget_prompt("x"))
    assert result.content == "from async"


def test_callable_source_aget_prompt_runs_sync_callable_in_thread():
    source = CallablePromptSource({"x": lambda: make_prompt("from sync")})
    result = asyncio.run(source.aget_prompt("x"))
    assert result.content == "from sync"


def test_callable_source_aget_prompt_raises_key_error_for_unknown_key():
    source = CallablePromptSource({"a": lambda: make_prompt("A")})
    with pytest.raises(KeyError, match="missing"):
        asyncio.run(source.aget_prompt("missing"))


# --- registry integration ---

def test_registry_uses_native_aget_prompt_on_callable_source():
    """PromptRegistry.aget_prompt uses the source's own aget_prompt when available."""
    called_natively: list[bool] = []

    class TrackingSource(CallablePromptSource):
        async def aget_prompt(self, key: str) -> SimplePrompt:
            called_natively.append(True)
            return await super().aget_prompt(key)

    source = TrackingSource({"x": lambda: make_prompt("native")})
    registry = PromptRegistry(source)
    result = asyncio.run(registry.aget_prompt("x"))
    assert result.content == "native"
    assert called_natively == [True]


def test_registry_aget_prompt_falls_through_async_source_on_key_error():
    """aget_prompt falls through to the next source even when using native aget_prompt."""
    async def async_fn() -> SimplePrompt:
        return make_prompt("from async source")

    first = CallablePromptSource({"a": lambda: make_prompt("A")})
    second = CallablePromptSource({"b": async_fn})
    registry = PromptRegistry(first, second)
    result = asyncio.run(registry.aget_prompt("b"))
    assert result.content == "from async source"
