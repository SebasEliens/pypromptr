"""Tests for FilePrompts. User-perspective: load prompts from a directory of files."""

from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from spidey import FilePrompts, MessagesPrompt, SimplePrompt


class MinimalMetadata(BaseModel):
    pass


def test_file_prompts_lists_keys_from_directory_and_loads_on_get(tmp_path: Path):
    """I point FilePrompts at a directory; I can list keys (from filenames) and get a prompt by key loads only that file."""
    (tmp_path / "welcome.md").write_text("Hello")
    (tmp_path / "other.md").write_text("Other content")
    source = FilePrompts(tmp_path)
    assert set(source.keys()) == {"other", "welcome"}
    prompt = source.get_prompt("welcome")
    assert isinstance(prompt, SimplePrompt)
    assert prompt.content == "Hello"


def test_file_prompts_accepts_config_as_dict_and_uses_extension(tmp_path: Path):
    """I can pass config as a dict; extension and delimiters are validated and used."""
    (tmp_path / "readme.txt").write_text("Read me")
    source = FilePrompts(tmp_path, config={"extension": ".txt"})
    assert source.keys() == ["readme"]
    assert source.get_prompt("readme").content == "Read me"


def test_file_prompts_invalid_config_raises_validation_error(tmp_path: Path):
    """Invalid config (e.g. wrong type) is rejected at construction."""
    with pytest.raises(ValidationError):
        FilePrompts(tmp_path, config={"extension": 123})


def test_file_prompts_parses_markdown_with_role_sections_as_messages(tmp_path: Path):
    """A file with ## user / ## assistant (or similar) sections becomes a multi-message prompt."""
    (tmp_path / "chat.md").write_text("""## system
You are helpful.

## user
Hello

## assistant
Hi there
""")
    source = FilePrompts(tmp_path)
    prompt = source.get_prompt("chat")
    assert isinstance(prompt, MessagesPrompt)
    assert prompt.messages == [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]
