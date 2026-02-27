"""Prompt type hierarchy: SimplePrompt, MessagesPrompt, templates, and RenderedPrompt."""

from typing import TypedDict

from pydantic import BaseModel


class Message(TypedDict):
    """A single message with explicit role and content (e.g. user, system, assistant)."""

    role: str
    content: str


class RenderedPrompt(BaseModel):
    """Result of rendering a prompt; carries metadata and final content for use (e.g. by an LLM)."""

    metadata: BaseModel
    content: str = ""
    messages: list[Message] = []


class SimplePrompt(BaseModel):
    """Static single-block prompt; render returns the same content."""

    metadata: BaseModel
    content: str

    def render(self, **kwargs: object) -> RenderedPrompt:
        return RenderedPrompt(
            metadata=self.metadata,
            content=self.content,
            messages=[Message(role="user", content=self.content)],
        )


def _substitute(content: str, **kwargs: str) -> str:
    """Replace {{key}} placeholders in content with values from kwargs."""
    result = content
    for key, value in kwargs.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


class SimplePromptTemplate(BaseModel):
    """Single-block prompt with placeholders; render substitutes variables."""

    metadata: BaseModel
    content: str

    def render(self, **kwargs: object) -> RenderedPrompt:
        content = _substitute(self.content, **kwargs)
        return RenderedPrompt(
            metadata=self.metadata,
            content=content,
            messages=[Message(role="user", content=content)],
        )


class MessagesPrompt(BaseModel):
    """Static multi-block prompt; render returns the same messages."""

    metadata: BaseModel
    messages: list[Message]

    def render(self, **kwargs: object) -> RenderedPrompt:
        return RenderedPrompt(
            metadata=self.metadata,
            content="",
            messages=self.messages,
        )


class MessagesPromptTemplate(BaseModel):
    """Multi-block prompt with placeholders; render substitutes variables in each message."""

    metadata: BaseModel
    messages: list[Message]

    def render(self, **kwargs: object) -> RenderedPrompt:
        rendered_messages: list[Message] = [
            Message(
                role=msg["role"],
                content=_substitute(msg.get("content", ""), **kwargs),
            )
            for msg in self.messages
        ]
        return RenderedPrompt(
            metadata=self.metadata,
            content="",
            messages=rendered_messages,
        )
