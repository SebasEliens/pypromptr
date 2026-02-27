"""LangFuse as a PromptSource. Requires pip install spidey[langfuse]."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from spidey.prompts import Message, MessagesPrompt, SimplePrompt, SimplePromptTemplate

if TYPE_CHECKING:
    pass  # langfuse client type not required at type-check time


def _import_langfuse():
    try:
        from langfuse import Langfuse
        return Langfuse
    except ImportError as e:
        raise ImportError("Install LangFuse support with: pip install spidey[langfuse]") from e


class LangFusePromptMetadata(BaseModel):
    """Metadata for LangFuse-loaded prompts; config (model, temperature, etc.) and extra."""

    model_config = ConfigDict(extra="allow")


class LangFusePrompts:
    """PromptSource that lists and fetches prompts from LangFuse (lazy)."""

    def __init__(
        self,
        *,
        client: Any = None,
        secret_key: str | None = None,
        public_key: str | None = None,
        host: str | None = None,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            Langfuse = _import_langfuse()
            kwargs: dict[str, str] = {}
            if secret_key is not None:
                kwargs["secret_key"] = secret_key
            if public_key is not None:
                kwargs["public_key"] = public_key
            if host is not None:
                kwargs["host"] = host
            self._client = Langfuse(**kwargs) if kwargs else Langfuse()

    def keys(self) -> list[str]:
        """Return prompt names from LangFuse; no prompt bodies loaded."""
        data = self._client.prompts.list()
        names = []
        for item in data:
            name = getattr(item, "name", None) or getattr(item, "slug", None)
            if name is not None:
                names.append(str(name))
        return sorted(names)

    def get_prompt(self, key: str) -> SimplePrompt | SimplePromptTemplate | MessagesPrompt:
        """Fetch prompt by name from LangFuse and map to Spidey prompt type."""
        try:
            lf = self._client.get_prompt(key)
        except Exception as e:
            if "not found" in str(e).lower() or "404" in str(e):
                raise KeyError(key) from e
            raise
        content = getattr(lf, "prompt", None)
        config = getattr(lf, "config", None) or {}
        metadata = LangFusePromptMetadata.model_validate(config)

        if content is None:
            content = ""

        if isinstance(content, list):
            messages = [
                Message(
                    role=str(m.get("role", "user")),
                    content=str(m.get("content", "")),
                )
                for m in content
                if isinstance(m, dict)
            ]
            if not messages:
                return SimplePrompt(metadata=metadata, content="")
            return MessagesPrompt(metadata=metadata, messages=messages)

        text = str(content)
        if "{{" in text:
            return SimplePromptTemplate(metadata=metadata, content=text)
        return SimplePrompt(metadata=metadata, content=text)
