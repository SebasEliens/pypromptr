"""Prompt type hierarchy: SimplePrompt, MessagesPrompt, templates, and RenderedPrompt."""

from pydantic import BaseModel


class RenderedPrompt(BaseModel):
    """Result of rendering a prompt; carries metadata and final content for use (e.g. by an LLM)."""

    metadata: BaseModel
    content: str


class SimplePrompt(BaseModel):
    """Static single-block prompt; render returns the same content."""

    metadata: BaseModel
    content: str

    def render(self) -> RenderedPrompt:
        return RenderedPrompt(metadata=self.metadata, content=self.content)
