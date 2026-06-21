# Adding a prompt store

Spidey’s registry works with any **PromptSource**: implement `keys()` and `get_prompt(key)` and pass it to `PromptRegistry(source, ...)`.

## Contract

- **`keys() -> list[str]`**  
  Return the set of prompt keys **without** loading prompt bodies. The registry calls this at init to build the key set. See [LAZY_LOADING.md](LAZY_LOADING.md).

- **`get_prompt(key: str)`**  
  Load and return the prompt for that key. Called only when the user (or registry) requests that key. Return a Spidey prompt type: `SimplePrompt`, `SimplePromptTemplate`, `MessagesPrompt`, or `MessagesPromptTemplate`.

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
- **Generic HTTP** — implement a small wrapper that calls your REST API in `keys()` and `get_prompt(key)` and maps responses to Spidey prompt types.

Same contract: list keys at init, fetch by key on demand, return Spidey prompt instances.
