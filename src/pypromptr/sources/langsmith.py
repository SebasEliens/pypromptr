"""LangSmithPrompts: PromptSource that fetches prompts from LangSmith Hub. Requires pip install pypromptr[langsmith]."""

from __future__ import annotations

import re
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from pypromptr.prompts import Message, MessagesPrompt, MessagesPromptTemplate, SimplePrompt, SimplePromptTemplate
from pypromptr.registry import PromptLike


class LangSmithPromptMetadata(BaseModel):
    """Metadata for LangSmith-loaded prompts. Accepts any extra fields from the SDK."""

    model_config = ConfigDict(extra="allow")


def _langchain_to_mustache(template: str) -> str:
    """Convert LangChain {var} syntax to pypromptr {{var}} syntax.

    LangChain uses single braces for variables ({name}) and double braces for
    literal brace characters ({{). pypromptr uses double braces for variables
    ({{name}}). This function converts between the two representations.
    """
    # Stash escaped braces so they aren't touched by the variable substitution
    result = template.replace("{{", "\x00LBRACE\x00").replace("}}", "\x00RBRACE\x00")
    result = re.sub(r"\{(\w+)\}", r"{{\1}}", result)
    # Restore escaped braces as literal characters (no longer template variables)
    return result.replace("\x00LBRACE\x00", "{").replace("\x00RBRACE\x00", "}")


def _extract_content(lc_prompt: object) -> str | list[dict[str, str]]:
    """Extract raw content from a LangChain prompt object.

    Returns a string for PromptTemplate / plain text, or a list of
    {"role": ..., "content": ...} dicts for ChatPromptTemplate.
    Raises TypeError for unrecognised prompt types.
    """
    type_name = type(lc_prompt).__name__

    # ChatPromptTemplate — messages-based prompt
    messages_attr = getattr(lc_prompt, "messages", None)
    if messages_attr is not None and isinstance(messages_attr, list):
        result: list[dict[str, str]] = []
        for msg in messages_attr:
            role = getattr(msg, "role", None)
            if role is None:
                # HumanMessage / AIMessage / SystemMessage pattern
                class_name = type(msg).__name__.lower()
                if "human" in class_name or "user" in class_name:
                    role = "user"
                elif "ai" in class_name or "assistant" in class_name:
                    role = "assistant"
                elif "system" in class_name:
                    role = "system"
                else:
                    role = "user"
            content_val = getattr(msg, "content", None) or getattr(msg, "prompt", {})
            if hasattr(content_val, "template"):
                content_str = str(content_val.template)
            else:
                content_str = str(content_val)
            result.append({"role": str(role), "content": content_str})
        return result

    # PromptTemplate — string-based
    template_attr = getattr(lc_prompt, "template", None)
    if template_attr is not None:
        return str(template_attr)

    # Fallback: stringify whatever we got
    return str(lc_prompt)


class LangSmithAdapter(Protocol):
    """Port for LangSmith prompt retrieval. Implement to swap out the real client in tests."""

    def pull(self, identifier: str) -> str | list[dict[str, str]]:
        """Fetch prompt content for identifier.

        Returns a string for simple/template prompts, or a list of
        {"role", "content"} dicts for chat prompts.
        Raises KeyError(identifier) if not found.
        """
        ...


class FakeLangSmithAdapter:
    """Test double: in-memory dict of identifier → raw content.

    Content may be a plain string (simple/template prompt) or a list of
    {"role": ..., "content": ...} dicts (chat prompt).
    """

    def __init__(self, prompts: dict[str, str | list[dict[str, str]]]) -> None:
        self._prompts = dict(prompts)

    def pull(self, identifier: str) -> str | list[dict[str, str]]:
        if identifier not in self._prompts:
            raise KeyError(identifier)
        return self._prompts[identifier]


class LangSmithClientAdapter:
    """Real adapter using the langsmith SDK. Requires pip install pypromptr[langsmith]."""

    def __init__(
        self,
        client: object | None = None,
        *,
        api_key: str | None = None,
        api_url: str | None = None,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            try:
                from langsmith import Client
            except ImportError as e:
                raise ImportError(
                    "Install LangSmith support with: pip install pypromptr[langsmith]"
                ) from e
            kwargs: dict[str, str] = {}
            if api_key is not None:
                kwargs["api_key"] = api_key
            if api_url is not None:
                kwargs["api_url"] = api_url
            self._client = Client(**kwargs)

    def pull(self, identifier: str) -> str | list[dict[str, str]]:
        try:
            lc_prompt = self._client.pull_prompt(identifier)  # type: ignore[attr-defined]
        except Exception as e:
            msg = str(e).lower()
            if "not found" in msg or "404" in msg or "does not exist" in msg:
                raise KeyError(identifier) from e
            raise
        return _extract_content(lc_prompt)


class LangSmithPrompts:
    """PromptSource that fetches prompts from LangSmith Hub (lazy).

    Mapping keys are simple strings; values are LangSmith identifiers in the
    form ``"owner/repo-name"`` or ``"owner/repo-name:commit-hash"``.

    Example::

        from pypromptr.sources.langsmith import LangSmithPrompts

        source = LangSmithPrompts({
            "welcome": "myorg/welcome-prompt",
            "system":  "myorg/system-prompt:abc123",
        })
    """

    def __init__(
        self,
        mapping: dict[str, str],
        *,
        adapter: LangSmithAdapter | None = None,
        api_key: str | None = None,
        api_url: str | None = None,
    ) -> None:
        self._mapping = dict(mapping)
        if adapter is not None:
            self._adapter: LangSmithAdapter = adapter
        else:
            self._adapter = LangSmithClientAdapter(api_key=api_key, api_url=api_url)

    def keys(self) -> list[str]:
        """Return mapping keys. No API call."""
        return list(self._mapping.keys())

    def get_prompt(self, key: str) -> PromptLike:
        """Fetch and parse the prompt for key. Raises KeyError if key not in mapping."""
        if key not in self._mapping:
            raise KeyError(key)
        identifier = self._mapping[key]
        raw = self._adapter.pull(identifier)

        metadata = LangSmithPromptMetadata()

        if isinstance(raw, list):
            # Chat prompt — list of role/content dicts
            messages = [
                Message(
                    role=m["role"],
                    content=_langchain_to_mustache(m["content"]),
                )
                for m in raw
            ]
            has_template = any("{{" in msg["content"] for msg in messages)
            if has_template:
                return MessagesPromptTemplate(metadata=metadata, messages=messages)
            return MessagesPrompt(metadata=metadata, messages=messages)

        # Simple / template prompt
        converted = _langchain_to_mustache(raw)
        if "{{" in converted:
            return SimplePromptTemplate(metadata=metadata, content=converted)
        return SimplePrompt(metadata=metadata, content=converted)
