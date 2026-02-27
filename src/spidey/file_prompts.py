"""FilePrompts: PromptSource that loads prompts from a directory of files (lazy)."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from spidey.prompts import SimplePrompt


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

    def get_prompt(self, key: str) -> SimplePrompt:
        """Load and parse the file for key; raise KeyError if key not in keys()."""
        key_list = self.keys()
        if key not in key_list:
            raise KeyError(key)
        file_path = self._path / f"{key}{self._config.extension}"
        body = file_path.read_text()
        # Minimal parsing: treat whole body as content (no frontmatter/messages yet).
        return SimplePrompt(metadata=FilePromptMetadata(), content=body.strip())
