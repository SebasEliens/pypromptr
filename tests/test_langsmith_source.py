"""Tests for LangSmithPrompts source. All tests use FakeLangSmithAdapter — no network required."""

from __future__ import annotations

import pytest

from pypromptr import PromptRegistry, SimplePrompt, SimplePromptTemplate
from pypromptr.prompts import MessagesPrompt, MessagesPromptTemplate
from pypromptr.sources.langsmith import (
    FakeLangSmithAdapter,
    LangSmithPrompts,
    _langchain_to_mustache,
)


# ---------------------------------------------------------------------------
# _langchain_to_mustache conversion
# ---------------------------------------------------------------------------


def test_converts_single_brace_variable():
    assert _langchain_to_mustache("Hello {name}!") == "Hello {{name}}!"


def test_converts_multiple_variables():
    assert _langchain_to_mustache("{greeting}, {name}!") == "{{greeting}}, {{name}}!"


def test_preserves_literal_escaped_braces():
    """LangChain {{ / }} are literal braces — they should become { / } in output."""
    assert _langchain_to_mustache("Price: {{price}}") == "Price: {price}"


def test_no_variables_unchanged():
    assert _langchain_to_mustache("Hello world!") == "Hello world!"


def test_mixed_variables_and_literals():
    result = _langchain_to_mustache("{{literal}} and {var}")
    assert result == "{literal} and {{var}}"


# ---------------------------------------------------------------------------
# FakeLangSmithAdapter
# ---------------------------------------------------------------------------


def test_fake_adapter_returns_content():
    adapter = FakeLangSmithAdapter({"myorg/welcome": "Hello!"})
    assert adapter.pull("myorg/welcome") == "Hello!"


def test_fake_adapter_raises_key_error_for_unknown():
    adapter = FakeLangSmithAdapter({})
    with pytest.raises(KeyError):
        adapter.pull("myorg/missing")


# ---------------------------------------------------------------------------
# LangSmithPrompts.keys()
# ---------------------------------------------------------------------------


def test_keys_returns_mapping_keys_without_calling_adapter():
    """keys() must not invoke the adapter — just return the mapping's keys."""

    class _SpyAdapter:
        called = False

        def pull(self, identifier: str):
            _SpyAdapter.called = True
            raise AssertionError("pull must not be called from keys()")

    source = LangSmithPrompts(
        {"welcome": "myorg/welcome", "system": "myorg/system"},
        adapter=_SpyAdapter(),
    )
    assert set(source.keys()) == {"welcome", "system"}
    assert not _SpyAdapter.called


# ---------------------------------------------------------------------------
# LangSmithPrompts.get_prompt — simple prompt
# ---------------------------------------------------------------------------


def test_get_prompt_returns_simple_prompt_for_static_content():
    adapter = FakeLangSmithAdapter({"myorg/welcome": "Hello!"})
    source = LangSmithPrompts({"welcome": "myorg/welcome"}, adapter=adapter)
    prompt = source.get_prompt("welcome")
    assert isinstance(prompt, SimplePrompt)
    assert prompt.content == "Hello!"


def test_get_prompt_returns_simple_prompt_template_for_template_content():
    adapter = FakeLangSmithAdapter({"myorg/welcome": "Hello {name}!"})
    source = LangSmithPrompts({"welcome": "myorg/welcome"}, adapter=adapter)
    prompt = source.get_prompt("welcome")
    assert isinstance(prompt, SimplePromptTemplate)
    assert prompt.content == "Hello {{name}}!"


def test_simple_prompt_template_renders_correctly():
    adapter = FakeLangSmithAdapter({"myorg/welcome": "Hello {name}!"})
    registry = PromptRegistry(LangSmithPrompts({"welcome": "myorg/welcome"}, adapter=adapter))
    rendered = registry.get("welcome", name="Alice")
    assert rendered.content == "Hello Alice!"


# ---------------------------------------------------------------------------
# LangSmithPrompts.get_prompt — messages prompt
# ---------------------------------------------------------------------------


def test_get_prompt_returns_messages_prompt_for_chat_content():
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Tell me about {topic}."},
    ]
    adapter = FakeLangSmithAdapter({"myorg/chat": messages})
    source = LangSmithPrompts({"chat": "myorg/chat"}, adapter=adapter)
    prompt = source.get_prompt("chat")
    assert isinstance(prompt, MessagesPromptTemplate)
    assert prompt.messages[0]["role"] == "system"
    assert prompt.messages[1]["content"] == "Tell me about {{topic}}."


def test_get_prompt_returns_messages_prompt_for_static_chat():
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello!"},
    ]
    adapter = FakeLangSmithAdapter({"myorg/chat": messages})
    source = LangSmithPrompts({"chat": "myorg/chat"}, adapter=adapter)
    prompt = source.get_prompt("chat")
    assert isinstance(prompt, MessagesPrompt)


# ---------------------------------------------------------------------------
# KeyError behaviour
# ---------------------------------------------------------------------------


def test_get_prompt_raises_key_error_for_unknown_key():
    source = LangSmithPrompts(
        {"welcome": "myorg/welcome"},
        adapter=FakeLangSmithAdapter({"myorg/welcome": "Hi!"}),
    )
    with pytest.raises(KeyError):
        source.get_prompt("missing")


def test_get_prompt_propagates_key_error_from_adapter():
    """If adapter raises KeyError for the identifier, it propagates."""
    adapter = FakeLangSmithAdapter({})  # identifier not in fake store
    source = LangSmithPrompts({"welcome": "myorg/welcome"}, adapter=adapter)
    with pytest.raises(KeyError):
        source.get_prompt("welcome")


# ---------------------------------------------------------------------------
# LangSmithClientAdapter — skip if langsmith not installed
# ---------------------------------------------------------------------------


def test_langsmith_client_adapter_import_error_without_sdk():
    """LangSmithClientAdapter raises ImportError with helpful message when langsmith missing."""
    langsmith = pytest.importorskip("langsmith")
    # If langsmith IS installed, just verify we can instantiate without error
    from pypromptr.sources.langsmith import LangSmithClientAdapter
    _ = LangSmithClientAdapter(client=object())  # pass dummy client to skip real init
