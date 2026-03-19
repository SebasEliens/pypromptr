"""Spidey: prompt registry with swappable backends."""

from spideyprompt.prompts import (
    Message,
    MessagesPrompt,
    MessagesPromptTemplate,
    RenderedPrompt,
    SimplePrompt,
    SimplePromptTemplate,
)
from spideyprompt.file_prompts import FilePromptMetadata, FilePrompts, FilePromptsConfig
from spideyprompt.registry import InMemoryPrompts, PromptRegistry

__all__ = [
    "FilePromptMetadata",
    "FilePrompts",
    "FilePromptsConfig",
    "InMemoryPrompts",
    "Message",
    "MessagesPrompt",
    "MessagesPromptTemplate",
    "PromptRegistry",
    "RenderedPrompt",
    "SimplePrompt",
    "SimplePromptTemplate",
]
