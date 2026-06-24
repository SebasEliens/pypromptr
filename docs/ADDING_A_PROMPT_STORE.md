# Adding a prompt store

pypromptr's registry works with any **PromptSource**: implement `get_prompt(key)` and pass it to `PromptRegistry(source, ...)`.

## Contract

### Required: `get_prompt(key: str) -> PromptLike`

Load and return the prompt for `key`. Return one of the pypromptr prompt types: `SimplePrompt`, `SimplePromptTemplate`, `MessagesPrompt`, or `MessagesPromptTemplate`.

**KeyError contract:** raise `KeyError(key)` when the key does not exist in your source. The registry catches `KeyError` to fall through to the next source in the chain. If your backend raises a different exception for missing keys (e.g. `FileNotFoundError`, `ValueError`), convert it to `KeyError` — otherwise the chain breaks and the error propagates to the caller.

```python
def get_prompt(self, key: str) -> PromptLike:
    try:
        data = self._backend.fetch(key)
    except BackendNotFoundError:
        raise KeyError(key)  # must be KeyError
    return SimplePrompt(content=data["content"], metadata={})
```

Other errors (network failures, parse errors, auth failures) may propagate freely.

### Optional: `keys() -> list[str]`

Return the set of prompt keys **without** loading prompt bodies. When present, the registry calls this at init to build the known key set (used by `registry.keys()` and `validate_at_init`). Sources without `keys()` are skipped for enumeration but still participate fully in resolution.

Omit `keys()` if listing all prompts is expensive or unsupported by your backend (e.g. a remote store with no list API).

## Built-in sources

- **InMemoryPrompts** — dict of key → prompt; no I/O.
- **FilePrompts** — directory of markdown files; lazy load on `get_prompt(key)`.
- **LangFusePrompts** — optional extra; `pip install pypromptr[langfuse]`. See below.

## LangFuse (optional)

Install: `pip install pypromptr[langfuse]`

Configure via environment or explicit arguments:

- **Env:** `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_HOST` (optional; default LangFuse cloud).
- **Explicit:** `LangFusePrompts(secret_key=..., public_key=..., host=...)` or pass an existing `client` (e.g. for tests).

Usage:

```python
from pypromptr import PromptRegistry
from pypromptr.langfuse_source import LangFusePrompts

registry = PromptRegistry(LangFusePrompts())
prompt = registry.get_prompt("my-prompt-name")
rendered = registry.get("my-prompt-name", **variables)
```

## Other stores (candidates)

- **LangSmith** — prompt management and versioning; different API and auth.
- **Helicone** — observability and prompt management.
- **Generic HTTP** — implement a small wrapper that calls your REST API in `get_prompt(key)` and maps responses to pypromptr prompt types.
