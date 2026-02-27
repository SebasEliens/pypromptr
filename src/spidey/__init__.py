"""Spidey: prompt registry with swappable backends."""

from spidey.prompts import (
    Message,
    MessagesPrompt,
    MessagesPromptTemplate,
    RenderedPrompt,
    SimplePrompt,
    SimplePromptTemplate,
)
from spidey.file_prompts import FilePrompts
from spidey.registry import InMemoryPrompts, PromptRegistry

__all__ = [
    "FilePrompts",
    "InMemoryPrompts",
    "Message",
    "MessagesPrompt",
    "MessagesPromptTemplate",
    "PromptRegistry",
    "RenderedPrompt",
    "SimplePrompt",
    "SimplePromptTemplate",
]
