"""FilePrompts: PromptSource that loads prompts from a directory of files (lazy)."""

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from spidey.prompts import Message, MessagesPrompt, SimplePrompt


class FilePromptMetadata(BaseModel):
    """Metadata for file-loaded prompts; allows extra fields from frontmatter."""

    model_config = ConfigDict(extra="allow")


class MessageDelimiters(BaseModel):
    """Delimiters for message sections in file content (e.g. <user>...</user>)."""

    user: str = "<user>"
    system: str = "<system>"
    assistant: str = "<assistant>"


class FilePromptsConfig(BaseModel):
    """Configuration for FilePrompts: extension, parsing strategy, message delimiters."""

    extension: str = ".md"
    parsing_strategy: str = "markdown"
    message_delimiters: MessageDelimiters = MessageDelimiters()


class FilePrompts:
    """PromptSource that discovers keys from filenames and loads prompt body on get_prompt(key)."""

    def __init__(self, path: Path | str, config: FilePromptsConfig | dict | None = None) -> None:
        self._path = Path(path)
        if config is None:
            self._config = FilePromptsConfig()
        elif isinstance(config, dict):
            self._config = FilePromptsConfig.model_validate(config)
        else:
            self._config = config

    def keys(self) -> list[str]:
        """Return key set from filenames with configured extension; no file bodies loaded."""
        if not self._path.is_dir():
            return []
        ext = self._config.extension
        return sorted(
            p.stem for p in self._path.iterdir()
            if p.is_file() and p.suffix == ext
        )

    def get_prompt(self, key: str) -> SimplePrompt | MessagesPrompt:
        """Load and parse the file for key; raise KeyError if key not in keys()."""
        key_list = self.keys()
        if key not in key_list:
            raise KeyError(key)
        file_path = self._path / f"{key}{self._config.extension}"
        raw = file_path.read_text()
        body = self._strip_frontmatter(raw) if raw.strip().startswith("---") else raw
        body = body.strip()
        messages = self._parse_markdown_sections(body)
        if messages:
            return MessagesPrompt(metadata=FilePromptMetadata(), messages=messages)
        return SimplePrompt(metadata=FilePromptMetadata(), content=body or "")

    def _strip_frontmatter(self, raw: str) -> str:
        """Remove optional YAML frontmatter (--- ... ---); return body only."""
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
        return raw[match.end() :] if match else raw

    def _parse_markdown_sections(self, body: str) -> list[Message]:
        """Parse ## role\\ncontent sections; return [] if no sections."""
        if not body.startswith("## ") and "\n## " not in body:
            return []
        if body.startswith("## "):
            body = body[3:]
        parts = re.split(r"\n## ", body)
        result: list[Message] = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            first_newline = part.find("\n")
            if first_newline == -1:
                role, content = part, ""
            else:
                role, content = part[:first_newline].strip(), part[first_newline + 1 :].strip()
            if role in ("system", "user", "assistant"):
                result.append(Message(role=role, content=content))
        return result
