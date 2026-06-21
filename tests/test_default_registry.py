"""Tests for the module-level default registry. User-perspective: register once, get anywhere."""

import asyncio
import threading

import pytest
from pydantic import BaseModel

import pypromptr
from pypromptr import (
    InMemoryPrompts,
    RenderedPrompt,
    SimplePrompt,
    SimplePromptTemplate,
)


class MinimalMetadata(BaseModel):
    pass


@pytest.fixture(autouse=True)
def reset_registry():
    """Isolate each test from others by clearing the default registry before and after."""
    pypromptr.clear()
    yield
    pypromptr.clear()


# --- register_prompt / get_prompt ---

def test_register_prompt_and_get_prompt_round_trip():
    """I register a prompt by key; get_prompt returns that exact prompt."""
    prompt = SimplePrompt(metadata=MinimalMetadata(), content="Hello")
    pypromptr.register_prompt("welcome", prompt)
    assert pypromptr.get_prompt("welcome") is prompt


def test_register_prompt_source_and_get_prompt_round_trip():
    """I register a source; get_prompt resolves keys from it."""
    prompt = SimplePrompt(metadata=MinimalMetadata(), content="From source")
    source = InMemoryPrompts({"greeting": prompt})
    pypromptr.register_prompt_source(source)
    assert pypromptr.get_prompt("greeting") is prompt


def test_get_prompt_raises_key_error_when_key_not_registered():
    """When no prompt or source has the key, get_prompt raises KeyError."""
    with pytest.raises(KeyError, match="missing"):
        pypromptr.get_prompt("missing")


# --- priority ---

def test_last_registered_source_wins_over_earlier_source():
    """The most recently registered source takes priority over earlier ones."""
    first = InMemoryPrompts({"key": SimplePrompt(metadata=MinimalMetadata(), content="from first")})
    last = InMemoryPrompts({"key": SimplePrompt(metadata=MinimalMetadata(), content="from last")})
    pypromptr.register_prompt_source(first)
    pypromptr.register_prompt_source(last)
    assert pypromptr.get_prompt("key").content == "from last"


def test_register_prompt_overrides_source_for_same_key():
    """A directly registered prompt always wins over any source for the same key."""
    source_prompt = SimplePrompt(metadata=MinimalMetadata(), content="from source")
    override_prompt = SimplePrompt(metadata=MinimalMetadata(), content="override")
    pypromptr.register_prompt_source(InMemoryPrompts({"key": source_prompt}))
    pypromptr.register_prompt("key", override_prompt)
    assert pypromptr.get_prompt("key") is override_prompt


def test_fallback_to_earlier_source_when_key_missing_in_later():
    """If the highest-priority source doesn't have the key, earlier sources are tried."""
    early = InMemoryPrompts({"only_in_early": SimplePrompt(metadata=MinimalMetadata(), content="early")})
    late = InMemoryPrompts({"only_in_late": SimplePrompt(metadata=MinimalMetadata(), content="late")})
    pypromptr.register_prompt_source(early)
    pypromptr.register_prompt_source(late)
    assert pypromptr.get_prompt("only_in_early").content == "early"
    assert pypromptr.get_prompt("only_in_late").content == "late"


# --- get (render) ---

def test_get_renders_prompt_with_template_variables():
    """get() returns a rendered prompt with variables substituted."""
    pypromptr.register_prompt(
        "greeting",
        SimplePromptTemplate(metadata=MinimalMetadata(), content="Hello, {{name}}!"),
    )
    rendered = pypromptr.get("greeting", name="Alice")
    assert isinstance(rendered, RenderedPrompt)
    assert rendered.content == "Hello, Alice!"


# --- clear ---

def test_clear_removes_all_prompts_and_sources():
    """After clear(), the registry is empty and get_prompt raises KeyError."""
    pypromptr.register_prompt("key", SimplePrompt(metadata=MinimalMetadata(), content=""))
    pypromptr.register_prompt_source(InMemoryPrompts({"other": SimplePrompt(metadata=MinimalMetadata(), content="")}))
    pypromptr.clear()
    with pytest.raises(KeyError):
        pypromptr.get_prompt("key")
    with pytest.raises(KeyError):
        pypromptr.get_prompt("other")


# --- laziness ---

def test_register_prompt_source_never_calls_keys_on_source():
    """Registering a source must not call keys() or get_prompt() — stays fully lazy."""
    keys_called = []
    get_called = []

    class SpySource:
        def keys(self):
            keys_called.append(True)
            return ["spy"]

        def get_prompt(self, key):
            get_called.append(key)
            return SimplePrompt(metadata=MinimalMetadata(), content="spy")

    pypromptr.register_prompt_source(SpySource())
    assert keys_called == [], "register_prompt_source must not call keys()"
    assert get_called == [], "register_prompt_source must not call get_prompt()"


# --- thread safety ---

def test_concurrent_register_and_get_do_not_corrupt_state():
    """Concurrent register_prompt and get_prompt calls from multiple threads don't raise or corrupt."""
    errors: list[Exception] = []

    def writer(n: int) -> None:
        try:
            for i in range(50):
                pypromptr.register_prompt(
                    f"key-{n}-{i}",
                    SimplePrompt(metadata=MinimalMetadata(), content=f"{n}-{i}"),
                )
        except Exception as e:
            errors.append(e)

    def reader() -> None:
        try:
            for _ in range(100):
                try:
                    pypromptr.get_prompt("key-0-0")
                except KeyError:
                    pass  # may not be registered yet — that's fine
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
    threads += [threading.Thread(target=reader) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"Thread errors: {errors}"


# --- async ---

def test_aget_prompt_returns_same_result_as_get_prompt():
    """aget_prompt returns the same prompt as the sync get_prompt."""
    prompt = SimplePrompt(metadata=MinimalMetadata(), content="async test")
    pypromptr.register_prompt("async_key", prompt)
    result = asyncio.run(pypromptr.aget_prompt("async_key"))
    assert result is prompt


def test_aget_renders_prompt_with_template_variables():
    """aget() returns a rendered prompt with variables substituted, same as sync get()."""
    pypromptr.register_prompt(
        "tmpl",
        SimplePromptTemplate(metadata=MinimalMetadata(), content="Hi, {{name}}!"),
    )
    rendered = asyncio.run(pypromptr.aget("tmpl", name="Bob"))
    assert isinstance(rendered, RenderedPrompt)
    assert rendered.content == "Hi, Bob!"


def test_aget_prompt_raises_key_error_for_missing_key():
    """aget_prompt raises KeyError (wrapped in asyncio) when key is not registered."""
    with pytest.raises(KeyError):
        asyncio.run(pypromptr.aget_prompt("nonexistent"))
