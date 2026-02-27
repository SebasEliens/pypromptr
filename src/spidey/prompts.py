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
        return RenderedPrompt(metadata=self.metadata, content=content)
