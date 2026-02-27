"""Spidey: prompt registry with swappable backends."""

from spidey.prompts import (
    Message,
    MessagesPrompt,
    MessagesPromptTemplate,
    RenderedPrompt,
    SimplePrompt,
    SimplePromptTemplate,
)
from spidey.registry import InMemoryPrompts, PromptRegistry

__all__ = [
    "InMemoryPrompts",
    "Message",
    "MessagesPrompt",
    "MessagesPromptTemplate",
    "PromptRegistry",
    "RenderedPrompt",
    "SimplePrompt",
    "SimplePromptTemplate",
]
