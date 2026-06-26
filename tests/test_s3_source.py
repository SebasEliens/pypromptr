"""Tests for S3Prompts. Uses FakeBucketAdapter — no boto3 required."""

import pytest

from pypromptr.sources.s3 import FakeBucketAdapter, S3Prompts
from pypromptr.prompts import MessagesPrompt, SimplePrompt


PLAIN_TEXT = "Hello from S3!"

FRONTMATTER_TEXT = """\
---
title: S3 Prompt
---
Body from S3.
"""

MESSAGES_TEXT = """\
## system
You are an S3-based assistant.

## user
What is S3?
"""


def make_source(objects):
    return S3Prompts(adapter=FakeBucketAdapter(objects))


def test_keys_returns_all_object_keys():
    source = make_source({"greeting": PLAIN_TEXT, "farewell": "Goodbye!"})
    assert set(source.keys()) == {"greeting", "farewell"}


def test_get_prompt_returns_simple_prompt():
    source = make_source({"greeting": PLAIN_TEXT})
    prompt = source.get_prompt("greeting")
    assert isinstance(prompt, SimplePrompt)
    assert prompt.content == PLAIN_TEXT


def test_get_prompt_parses_frontmatter():
    source = make_source({"fm": FRONTMATTER_TEXT})
    prompt = source.get_prompt("fm")
    assert isinstance(prompt, SimplePrompt)
    assert prompt.content == "Body from S3."
    assert prompt.metadata.model_extra["title"] == "S3 Prompt"


def test_get_prompt_parses_messages_prompt():
    source = make_source({"chat": MESSAGES_TEXT})
    prompt = source.get_prompt("chat")
    assert isinstance(prompt, MessagesPrompt)
    assert prompt.messages[0]["role"] == "system"
    assert prompt.messages[1]["role"] == "user"


def test_get_prompt_raises_key_error_for_unknown_key():
    source = make_source({})
    with pytest.raises(KeyError):
        source.get_prompt("nonexistent")
