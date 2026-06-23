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

# Optional fallback when key is missing in primary source
registry = PromptRegistry(FilePrompts("prompts/"), fallback=InMemoryPrompts(defaults))
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

FilePrompts is the built-in markdown source (frontmatter + body; no separate "MarkdownPromptSource"). See [ADDING_A_PROMPT_STORE.md](docs/ADDING_A_PROMPT_STORE.md) to implement your own store.

## Lazy loading and init

- **Keys** are resolved at init from the source's `keys()` (no full prompt bodies loaded for file/remote sources).
- **Bodies** are loaded on demand when you call `get_prompt(key)` or `get(key, ...)`.
- **validate_at_init**: When `True`, the registry can optionally validate that each key is fetchable at startup; when `False`, only the key set is built. See [LAZY_LOADING.md](docs/LAZY_LOADING.md) and [INIT_VALIDATION.md](docs/INIT_VALIDATION.md).

## Typing and metadata

Prompts carry optional Pydantic metadata. The registry is designed so that `get_prompt("key")` can be typed per key. See [TYPING_DESIGN.md](docs/TYPING_DESIGN.md).

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

See [ADDING_A_PROMPT_STORE.md](docs/ADDING_A_PROMPT_STORE.md) for env vars and alternatives (LangSmith, Helicone, generic HTTP).

## Public API

**From `pypromptr`:**
- `PromptRegistry` — main entry point.
- `InMemoryPrompts`, `FilePrompts`, `FilePromptsConfig`, `FilePromptMetadata`.
- `SimplePrompt`, `SimplePromptTemplate`, `MessagesPrompt`, `MessagesPromptTemplate`, `Message`, `RenderedPrompt`.

**Optional (requires `pypromptr[langfuse]`):**
- `from pypromptr.langfuse_source import LangFusePrompts`

Use `PromptRegistry(source, fallback=...)` with any `PromptSource` (implement `keys()` and `get_prompt(key)`). There is no separate `from_mapping` or `load_source`; use `InMemoryPrompts(mapping)` or `FilePrompts(path)` and pass them to `PromptRegistry`.

## Docs

- [ROADMAP](docs/ROADMAP.md) — planned features for wider adoption (post–first PyPI release).
- [PRD](docs/PRD.md) — goals and user stories.
- [IMPLEMENTATION](docs/IMPLEMENTATION.md) — phased roadmap.
- [ADDING_A_PROMPT_STORE](docs/ADDING_A_PROMPT_STORE.md) — implement a custom store.
- [LAZY_LOADING](docs/LAZY_LOADING.md), [INIT_VALIDATION](docs/INIT_VALIDATION.md), [TYPING_DESIGN](docs/TYPING_DESIGN.md).
