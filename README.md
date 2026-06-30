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

The fastest path is the module-level default registry — no `PromptRegistry` instance needed:

```python
import pypromptr
from pypromptr import FilePrompts, InMemoryPrompts, SimplePromptTemplate

# Register a directory of markdown files
pypromptr.register_prompt_source(FilePrompts("prompts/"))

# Or register individual prompts directly
pypromptr.register_prompt(
    "welcome",
    SimplePromptTemplate(content="Hello, {{name}}!", metadata={}),
)

# Get rendered content from anywhere in your app
rendered = pypromptr.get("welcome", name="Alice")

# Get the raw prompt object
prompt = pypromptr.get_prompt("welcome")
```

Last registered source wins. `register_prompt` always overrides any source for the same key.

## PromptRegistry

For explicit control — multiple isolated registries, combining registries, or dependency injection — use `PromptRegistry` directly:

```python
from pypromptr import PromptRegistry, InMemoryPrompts, FilePrompts

# Single source
registry = PromptRegistry(InMemoryPrompts({
    "welcome": SimplePromptTemplate(content="Hello, {{name}}!", metadata={}),
}))

# From a directory of markdown files (lazy load on access)
registry = PromptRegistry(FilePrompts("prompts/"))

# Multiple sources — first match wins
registry = PromptRegistry(FilePrompts("prompts/"), InMemoryPrompts(defaults))

# Access
prompt = registry.get_prompt("welcome")
rendered = registry.get("welcome", name="Alice")

# Combine two registries
combined = app_prompts + lib_prompts
```

## Sources

| Source | Use case |
|--------|----------|
| **InMemoryPrompts** | Dict of key → prompt; no I/O. |
| **FilePrompts** | Directory of markdown files; keys from filenames; lazy load on `get_prompt(key)`. |
| **CallablePromptSource** | Dict of callables invoked on demand — wrap any custom fetch logic. |
| **LangFusePrompts** | Optional: `pip install pypromptr[langfuse]`, then `from pypromptr.langfuse_source import LangFusePrompts`. |

### CallablePromptSource

Use `CallablePromptSource` to plug in any retrieval logic without subclassing — a database query, an HTTP call, a feature-flag lookup, anything:

```python
from pypromptr import CallablePromptSource
import pypromptr

def fetch_from_db(key):
    row = db.query("SELECT content FROM prompts WHERE key = %s", key)
    return SimplePrompt(content=row["content"], metadata={})

pypromptr.register_prompt_source(CallablePromptSource({
    "system":   lambda: fetch_from_db("system"),
    "fallback": lambda: fetch_from_db("fallback"),
}))
```

Async callables are also supported — use `aget_prompt` / `aget` to await them:

```python
async def fetch_async():
    async with aiohttp.ClientSession() as s:
        r = await s.get("https://prompts.example.com/welcome")
        return SimplePrompt(content=await r.text(), metadata={})

pypromptr.register_prompt_source(CallablePromptSource({
    "welcome": fetch_async,
}))

rendered = await pypromptr.aget("welcome", name="Alice")
```

### Custom PromptSource

For a reusable backend (e.g. your own CMS or vector store), implement the `PromptSource` protocol directly — only `get_prompt` is required:

```python
from pypromptr import PromptSource, PromptLike

class MyStore:
    def keys(self) -> list[str]:          # optional — enables enumeration
        return my_store.list_keys()

    def get_prompt(self, key: str) -> PromptLike:
        result = my_store.fetch(key)
        if result is None:
            raise KeyError(key)           # must raise KeyError for missing keys
        return SimplePrompt(content=result, metadata={})

    async def aget_prompt(self, key: str) -> PromptLike:  # optional — native async
        result = await my_store.afetch(key)
        if result is None:
            raise KeyError(key)
        return SimplePrompt(content=result, metadata={})

pypromptr.register_prompt_source(MyStore())
```

`keys()` and `aget_prompt()` are optional. Sources without `keys()` still participate in resolution; sources without `aget_prompt()` fall back to running `get_prompt` in a thread pool.

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
