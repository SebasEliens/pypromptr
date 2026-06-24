# pypromptr

[![PyPI](https://img.shields.io/pypi/v/pypromptr)](https://pypi.org/project/pypromptr/)

Prompt registry with swappable backends: in-memory dicts, a directory of markdown files, or an external store (e.g. LangFuse). Same API regardless of where prompts live.

## Install

```bash
pip install pypromptr

# with LangFuse support:
pip install pypromptr[langfuse]
```

## Quick start

```python
from pypromptr import PromptRegistry, InMemoryPrompts, FilePrompts
from pypromptr.prompts import SimplePromptTemplate

# In-memory
registry = PromptRegistry(InMemoryPrompts({
    "welcome": SimplePromptTemplate(content="Hello, {{name}}!", metadata={}),
}))

# Or from a directory of markdown files (lazy load on access)
registry = PromptRegistry(FilePrompts("prompts/"))

# Multiple sources tried in order — first match wins
registry = PromptRegistry(FilePrompts("prompts/"), InMemoryPrompts(defaults))
```

**Access:**

```python
# Get the prompt object (loads from file/remote only when requested)
prompt = registry.get_prompt("welcome")

# Get rendered content (pass template variables)
rendered = registry.get("welcome", name="Alice")
```

**Combine registries:**

```python
combined = app_prompts + lib_prompts
```

## Sources

| Source | Use case |
|--------|----------|
| **InMemoryPrompts** | Dict of key → prompt; no I/O. |
| **FilePrompts** | Directory of markdown files; keys from filenames; lazy load on `get_prompt(key)`. |
| **LangFusePrompts** | Optional: `pip install pypromptr[langfuse]`, then `from pypromptr.langfuse_source import LangFusePrompts`. |

FilePrompts is the built-in markdown source (frontmatter + body; no separate "MarkdownPromptSource"). Implement `keys()` and `get_prompt(key)` to create your own store.

## Lazy loading and init

- **Keys** are resolved at init from the source's `keys()` (no full prompt bodies loaded for file/remote sources).
- **Bodies** are loaded on demand when you call `get_prompt(key)` or `get(key, ...)`.
- **validate_at_init**: When `True`, the registry can optionally validate that each key is fetchable at startup; when `False`, only the key set is built.

## Typing and metadata

Prompts carry optional Pydantic metadata. The registry is designed so that `get_prompt("key")` can be typed per key.

## Optional: LangFuse

```bash
pip install pypromptr[langfuse]
```

Configure via environment (`LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_HOST`) or pass a client:

```python
from pypromptr import PromptRegistry
from pypromptr.langfuse_source import LangFusePrompts

registry = PromptRegistry(LangFusePrompts())
rendered = registry.get("my-prompt-name", **variables)
```

Configure env vars or pass a custom client for alternatives (LangSmith, Helicone, generic HTTP).

## Public API

**From `pypromptr`:**
- `PromptRegistry` — main entry point.
- `InMemoryPrompts`, `FilePrompts`, `FilePromptsConfig`, `FilePromptMetadata`.
- `SimplePrompt`, `SimplePromptTemplate`, `MessagesPrompt`, `MessagesPromptTemplate`, `Message`, `RenderedPrompt`.

**Optional (requires `pypromptr[langfuse]`):**
- `from pypromptr.langfuse_source import LangFusePrompts`

Use `PromptRegistry(*sources)` with any `PromptSource` (implement `keys()` and `get_prompt(key)`). There is no separate `from_mapping` or `load_source`; use `InMemoryPrompts(mapping)` or `FilePrompts(path)` and pass them to `PromptRegistry`.

## Feedback & contributing

Found a bug or have a question? [Open an issue](https://github.com/SebasEliens/pypromptr/issues).
Ideas and feature requests welcome too.
