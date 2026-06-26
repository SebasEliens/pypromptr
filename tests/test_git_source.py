"""Tests for GitRepoPrompts. Uses FakeGitAdapter — no gitpython required."""

import pytest

from pypromptr.sources.git import FakeGitAdapter, GitRepoPrompts
from pypromptr.prompts import MessagesPrompt, SimplePrompt


PLAIN_TEXT = "Hello from git!"

FRONTMATTER_TEXT = """\
---
title: Git Prompt
---
Body from git.
"""

MESSAGES_TEXT = """\
## system
You are a git-based assistant.

## user
What is a commit?
"""


def make_source(files):
    return GitRepoPrompts(adapter=FakeGitAdapter(files))


def test_keys_returns_all_file_keys():
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
    assert prompt.content == "Body from git."
    assert prompt.metadata.model_extra["title"] == "Git Prompt"


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
