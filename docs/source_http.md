# Design: HttpPrompts

## Motivation

Some prompts live behind HTTP endpoints — an internal API, a CDN-hosted file, a versioned URL. `HttpPrompts` maps keys to pre-configured HTTP requests, so each prompt is fetched from its own endpoint on demand.

This mirrors `InMemoryPrompts` in structure: a dict of `key -> request config`, resolved lazily on `get_prompt(key)`.

## Optional dependency

```bash
pip install pypromptr[http]
# adds: httpx
```

## Interface

```python
from pypromptr.http_source import HttpPrompt, HttpPrompts

source = HttpPrompts({
    "system-prompt": HttpPrompt("https://prompts.internal/system"),
    "welcome":        HttpPrompt("https://prompts.internal/welcome",
                                 headers={"X-Version": "2"}),
    "legal-notice":   HttpPrompt("https://cdn.example.com/prompts/legal.md"),
})
```

### `HttpPrompt`

```python
@dataclass
class HttpPrompt:
    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 5.0
```

No `base_url`, no path templates — each prompt is a fully-specified request.

## Behaviour

### `keys() -> list[str]`
Returns the dict keys. No I/O.

### `get_prompt(key: str) -> PromptLike`
Raises `KeyError(key)` immediately if `key` is not in the mapping (no HTTP call made). Otherwise executes the configured request and parses the response body as a prompt (same frontmatter + body parsing as `FilePrompts`). Non-2xx responses raise an `httpx` error and propagate.

## Notes

- **Explicit over dynamic** — each prompt endpoint is declared upfront. There is no URL template or base URL. This makes the source self-documenting and avoids surprising requests to unexpected URLs.
- `keys()` is supported and free — just the mapping keys, no network call.
- No caching — each `get_prompt` is a live HTTP call. Add a caching layer at the application level if needed.
- Sync only; `aget_prompt` on the registry wraps the call in `asyncio.to_thread`.

## Example

```python
from pypromptr import PromptRegistry
from pypromptr.http_source import HttpPrompt, HttpPrompts

registry = PromptRegistry(
    HttpPrompts({
        "system":  HttpPrompt("https://prompts.internal/v2/system",
                              headers={"Authorization": f"Bearer {token}"}),
        "welcome": HttpPrompt("https://prompts.internal/v2/welcome",
                              headers={"Authorization": f"Bearer {token}"}),
    }),
    InMemoryPrompts(defaults),   # fallback for keys not in the HTTP source
)

rendered = registry.get("welcome", user="Alice")
```
