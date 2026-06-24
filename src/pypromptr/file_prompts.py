"""FilePrompts: PromptSource that loads prompts from a directory of files (lazy)."""

from pathlib import Path
from typing import Type

from pydantic import BaseModel, ConfigDict

from pypromptr.prompts import MessagesPrompt, SimplePrompt
from pypromptr._parsing import _parse_frontmatter, _parse_role_sections


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
        """Load and parse the file for key; raise KeyError if file does not exist."""
        file = self._path / f"{key}{self._config.extension}"
        try:
            raw = file.read_text()
        except (FileNotFoundError, IsADirectoryError):
            raise KeyError(key)
        fm_dict, body = _parse_frontmatter(raw)
        body = body.strip()
        metadata = self._metadata_model.model_validate(fm_dict or {})
        messages = _parse_role_sections(body)
        if messages:
            return MessagesPrompt(metadata=metadata, messages=messages)
        return SimplePrompt(metadata=metadata, content=body or "")
