"""Tests for PromptRegistry and InMemoryPrompts. User-perspective: get prompts by key."""

from pydantic import BaseModel

from spidey import InMemoryPrompts, PromptRegistry, SimplePrompt


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
