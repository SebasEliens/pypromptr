"""Tests for prompt types. User-perspective: create prompts and render them."""

import pytest
from pydantic import BaseModel

from spidey.prompts import RenderedPrompt, SimplePrompt, SimplePromptTemplate


class MinimalMetadata(BaseModel):
    """Minimal metadata for tests."""

    pass


def test_simple_prompt_render_returns_same_content():
    """I have a static prompt with content; when I render it, I get the same content back."""
    prompt = SimplePrompt(metadata=MinimalMetadata(), content="Hello")
    result = prompt.render()
    assert isinstance(result, RenderedPrompt)
    assert result.content == "Hello"
    assert result.metadata == prompt.metadata


def test_simple_prompt_template_render_substitutes_variables():
    """I have a prompt with placeholders; when I render it with variables, I get the final string."""
    prompt = SimplePromptTemplate(
        metadata=MinimalMetadata(), content="Hello, {{name}}!"
    )
    result = prompt.render(name="Alice")
    assert result.content == "Hello, Alice!"
