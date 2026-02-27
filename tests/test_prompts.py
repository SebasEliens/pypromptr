"""Tests for prompt types. User-perspective: create prompts and render them."""

import pytest
from pydantic import BaseModel, ValidationError

from spidey.prompts import (
    MessagesPrompt,
    MessagesPromptTemplate,
    RenderedPrompt,
    SimplePrompt,
    SimplePromptTemplate,
)


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


def test_messages_prompt_render_returns_same_messages():
    """I have a prompt made of multiple role/content blocks; when I render it, I get those same messages back."""
    messages = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hi there"},
    ]
    prompt = MessagesPrompt(metadata=MinimalMetadata(), messages=messages)
    result = prompt.render()
    assert result.messages == messages


def test_messages_prompt_template_render_substitutes_variables():
    """I have a multi-message prompt with placeholders; when I render it with variables, I get the final messages."""
    messages = [{"role": "user", "content": "Hello, {{name}}"}]
    prompt = MessagesPromptTemplate(
        metadata=MinimalMetadata(), messages=messages
    )
    result = prompt.render(name="Alice")
    assert result.messages == [{"role": "user", "content": "Hello, Alice"}]


class MetadataWithRequired(BaseModel):
    """Metadata with a required field for validation tests."""

    required_id: int


def test_simple_prompt_rejects_invalid_metadata():
    """Invalid metadata is rejected when I create a prompt, so I see errors early."""
    with pytest.raises(ValidationError):
        SimplePrompt(
            metadata=MetadataWithRequired(required_id="not_an_int"),  # type: ignore[arg-type]
            content="Hello",
        )
