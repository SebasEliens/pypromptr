"""FilePrompts: PromptSource that loads prompts from a directory of files (lazy)."""

import re
from pathlib import Path
from typing import Any, Type

from pydantic import BaseModel, ConfigDict

from spidey.prompts import Message, MessagesPrompt, SimplePrompt


def _parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter and body from raw file content. Returns (metadata_dict, body)."""
    try:
        import frontmatter as fm

        if hasattr(fm, "loads"):
            post = fm.loads(raw)
            return (dict(post.metadata), post.content)
        # frontmatter 3.x: Frontmatter().read() returns {"attributes", "body"}; no "---" => body is ""
        parser = fm.Frontmatter()
        out = parser.read(raw)
        attrs = out.get("attributes") or {}
        body = out.get("body", "")
        if not body.strip() and not attrs:
            body = raw  # no frontmatter, whole file is body
        return (attrs, body)
    except Exception:
        return ({}, raw)


class FilePromptMetadata(BaseModel):
    """Default metadata for file-loaded prompts; frontmatter keys become attributes. Accepts extra fields."""

    model_config = ConfigDict(extra="allow")
    title: str | None = None
    description: str | None = None


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

    def __init__(
        self,
        path: Path | str,
        config: FilePromptsConfig | dict | None = None,
        *,
        metadata_model: Type[BaseModel] | None = None,
    ) -> None:
        self._path = Path(path)
        if config is None:
            self._config = FilePromptsConfig()
        elif isinstance(config, dict):
            self._config = FilePromptsConfig.model_validate(config)
        else:
            self._config = config
        self._metadata_model = metadata_model or FilePromptMetadata

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
        fm_dict, body = _parse_frontmatter(raw)
        body = body.strip()
        metadata = self._metadata_from_frontmatter(fm_dict or {})
        messages = self._parse_markdown_sections(body)
        if messages:
            return MessagesPrompt(metadata=metadata, messages=messages)
        return SimplePrompt(metadata=metadata, content=body or "")

    def _metadata_from_frontmatter(self, fm: dict) -> BaseModel:
        """Build prompt metadata from frontmatter; use metadata_model if set."""
        return self._metadata_model.model_validate(fm)

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
