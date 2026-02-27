"""Tests for LangFusePrompts. User-perspective: use LangFuse as a prompt source (requires spidey[langfuse] for real usage)."""

from unittest.mock import MagicMock

from spidey import PromptRegistry
from spidey.langfuse_source import LangFusePrompts
from spidey.prompts import SimplePrompt, SimplePromptTemplate


def test_langfuse_prompts_keys_returns_prompt_names_from_client():
    """I can list prompt keys from LangFuse without loading prompt bodies."""
    mock_client = MagicMock()
    m1, m2 = MagicMock(), MagicMock()
    m1.name = "welcome"
    m2.name = "greeting"
    mock_client.prompts.list.return_value = [m1, m2]
    source = LangFusePrompts(client=mock_client)
    keys = source.keys()
    assert set(keys) == {"welcome", "greeting"}
    mock_client.get_prompt.assert_not_called()


def test_langfuse_prompts_get_prompt_fetches_and_maps_to_simple_prompt():
    """When I get a prompt by key, LangFuse is called once and I get a Spidey prompt."""
    mock_client = MagicMock()
    m = MagicMock()
    m.name = "welcome"
    mock_client.prompts.list.return_value = [m]
    mock_prompt = MagicMock()
    mock_prompt.prompt = "Hello, {{name}}!"
    mock_prompt.config = {}
    mock_client.get_prompt.return_value = mock_prompt

    source = LangFusePrompts(client=mock_client)
    prompt = source.get_prompt("welcome")

    mock_client.get_prompt.assert_called_once_with("welcome")
    assert isinstance(prompt, (SimplePrompt, SimplePromptTemplate))
    assert "Hello" in prompt.content


def test_langfuse_prompts_as_registry_source():
    """I can use LangFusePrompts as a registry source; get_prompt and get work like other sources."""
    mock_client = MagicMock()
    m = MagicMock()
    m.name = "greeting"
    mock_client.prompts.list.return_value = [m]
    mock_prompt = MagicMock()
    mock_prompt.prompt = "Hello"
    mock_prompt.config = {}
    mock_client.get_prompt.return_value = mock_prompt

    registry = PromptRegistry(LangFusePrompts(client=mock_client))
    assert "greeting" in registry.keys()
    prompt = registry.get_prompt("greeting")
    assert prompt.content == "Hello"
    rendered = registry.get("greeting")
    assert rendered.content == "Hello"
