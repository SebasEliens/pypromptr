"""Tests for HttpPrompts. Uses FakeHttpAdapter — no httpx required."""

import pytest

from pypromptr.sources.http import FakeHttpAdapter, HttpPrompt, HttpPrompts
from pypromptr.prompts import MessagesPrompt, SimplePrompt


PLAIN_TEXT = "Hello, world!"

FRONTMATTER_TEXT = """\
---
title: Greeting
---
Hello from frontmatter!
"""

MESSAGES_TEXT = """\
## system
You are helpful.

## user
Hello
"""


def make_source(mapping, responses):
    return HttpPrompts(mapping, adapter=FakeHttpAdapter(responses))


def test_keys_returns_mapping_keys():
    source = make_source(
        {"greeting": HttpPrompt("https://example.com/greeting")},
        {"https://example.com/greeting": PLAIN_TEXT},
    )
    assert source.keys() == ["greeting"]


def test_get_prompt_returns_simple_prompt():
    url = "https://example.com/greeting"
    source = make_source(
        {"greeting": HttpPrompt(url)},
        {url: PLAIN_TEXT},
    )
    prompt = source.get_prompt("greeting")
    assert isinstance(prompt, SimplePrompt)
    assert prompt.content == PLAIN_TEXT


def test_get_prompt_parses_frontmatter():
    url = "https://example.com/fm"
    source = make_source(
        {"fm": HttpPrompt(url)},
        {url: FRONTMATTER_TEXT},
    )
    prompt = source.get_prompt("fm")
    assert isinstance(prompt, SimplePrompt)
    assert prompt.content == "Hello from frontmatter!"
    assert prompt.metadata.model_extra["title"] == "Greeting"


def test_get_prompt_parses_messages_prompt():
    url = "https://example.com/chat"
    source = make_source(
        {"chat": HttpPrompt(url)},
        {url: MESSAGES_TEXT},
    )
    prompt = source.get_prompt("chat")
    assert isinstance(prompt, MessagesPrompt)
    assert prompt.messages[0]["role"] == "system"
    assert prompt.messages[1]["role"] == "user"


def test_get_prompt_raises_key_error_for_unknown_key():
    source = make_source({}, {})
    with pytest.raises(KeyError):
        source.get_prompt("nonexistent")


def test_get_prompt_raises_key_error_when_adapter_returns_404():
    url = "https://example.com/missing"
    source = make_source(
        {"missing": HttpPrompt(url)},
        {},  # URL not in responses → FakeHttpAdapter raises KeyError
    )
    with pytest.raises(KeyError):
        source.get_prompt("missing")


def test_get_prompt_passes_method_and_headers_to_adapter():
    """Verify that HttpPrompts passes method and headers through to the adapter."""
    url = "https://example.com/secure"
    captured = {}

    class CapturingAdapter:
        def fetch(self, url, method, headers, timeout):
            captured["url"] = url
            captured["method"] = method
            captured["headers"] = headers
            captured["timeout"] = timeout
            return "content"

    source = HttpPrompts(
        {"secure": HttpPrompt(url, method="POST", headers={"X-Token": "abc"}, timeout=10.0)},
        adapter=CapturingAdapter(),
    )
    source.get_prompt("secure")
    assert captured["url"] == url
    assert captured["method"] == "POST"
    assert captured["headers"] == {"X-Token": "abc"}
    assert captured["timeout"] == 10.0
