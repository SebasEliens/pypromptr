"""Tests for FilePrompts. User-perspective: load prompts from a directory of files."""

from pathlib import Path

import pytest
from pydantic import BaseModel

from spidey import FilePrompts, SimplePrompt


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
