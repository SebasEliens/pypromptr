"""Shared parsing utilities: frontmatter splitting and role-section parsing."""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict

from pypromptr.prompts import Message, MessagesPrompt, SimplePrompt


def _parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter and body. Returns (metadata_dict, body). Handles python-frontmatter and frontmatter 3.x."""
    try:
        import frontmatter as fm

        if hasattr(fm, "loads"):
            post = fm.loads(raw)
            return (dict(post.metadata), post.content)
        parser = fm.Frontmatter()
        out = parser.read(raw)
        attrs = out.get("attributes") or {}
        body = out.get("body", "")
        if not body.strip() and not attrs:
            body = raw
        return (attrs, body)
    except Exception:
        return ({}, raw)


def _parse_role_sections(body: str) -> list[Message]:
    """Parse ## role\\ncontent blocks. Returns [] if no sections."""
    if not body.startswith("## ") and "\n## " not in body:
        return []
    text = body[3:] if body.startswith("## ") else body
    result: list[Message] = []
    for part in re.split(r"\n## ", text):
        part = part.strip()
        if not part:
            continue
        first_newline = part.find("\n")
        role, content = (part, "") if first_newline == -1 else (part[:first_newline].strip(), part[first_newline + 1:].strip())
        if role in ("system", "user", "assistant"):
            result.append(Message(role=role, content=content))
    return result


class _MinimalMetadata(BaseModel):
    """Minimal metadata model that accepts any extra fields."""

    model_config = ConfigDict(extra="allow")


def parse_prompt_text(raw: str, metadata_model: type[BaseModel] | None = None) -> SimplePrompt | MessagesPrompt:
    """Parse raw text (with optional YAML frontmatter) into a SimplePrompt or MessagesPrompt.

    If the body contains ## role sections, returns a MessagesPrompt.
    Otherwise returns a SimplePrompt.
    """
    fm_dict, body = _parse_frontmatter(raw)
    body = body.strip()
    model = metadata_model or _MinimalMetadata
    metadata = model.model_validate(fm_dict or {})
    messages = _parse_role_sections(body)
    if messages:
        return MessagesPrompt(metadata=metadata, messages=messages)
    return SimplePrompt(metadata=metadata, content=body or "")
