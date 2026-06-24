# Design: HttpPrompts

## Motivation

A generic HTTP source covers teams with an internal prompt server, a custom API, or any service that exposes prompts over HTTP but doesn't have a dedicated pypromptr integration. One implementation, zero vendor lock-in.

Also useful as the reference implementation for how to write a keyless source (no `keys()`), since many HTTP APIs don't support listing.

## Optional dependency

```bash
pip install pypromptr[http]
# adds: httpx
```

## Interface

```python
from pypromptr.http_source import HttpPrompts

source = HttpPrompts(
    base_url="https://prompts.internal/api/v1",
    # GET {base_url}/prompts/{key} -> {"content": "...", "metadata": {...}}
    path_template="/prompts/{key}",   # default: "/prompts/{key}"
    headers={"Authorization": "Bearer {token}"},
    timeout=5.0,
    # Optional: provide a list endpoint to enable keys()
    list_url=None,                    # e.g. "/prompts" -> [{"key": "..."}, ...]
    list_key_field="key",             # field in each list item that holds the key name
)
```

## Behaviour

### `get_prompt(key: str) -> PromptLike`
`GET {base_url}{path_template.format(key=key)}`. Expects a JSON response. Raises `KeyError(key)` on 404; raises the underlying `httpx` error for other failures.

Response shape (flexible — configurable via subclassing or a `parse` callable):
```json
{"content": "Hello, {{name}}!", "metadata": {}}
```

### `keys() -> list[str]` (optional)
Only present if `list_url` is provided. `GET {base_url}{list_url}`, returns a JSON array, extracts `list_key_field` from each item. If `list_url` is `None`, the source has no `keys()` and participates in resolution only.

## Notes

- **Keyless by default** — this is the canonical example of a source that implements only `get_prompt`. Most HTTP APIs don't have a cheap list endpoint.
- No caching built in — every `get_prompt` is a live HTTP call. Users can wrap with a caching layer or use `validate_at_init=False` and cache at the application level.
- Sync only; async callers use `aget_prompt` on the registry, which wraps the blocking call in `asyncio.to_thread`.
- Response parsing is intentionally minimal and overridable.

## Example

```python
from pypromptr import PromptRegistry
from pypromptr.http_source import HttpPrompts

registry = PromptRegistry(
    HttpPrompts(
        base_url="https://prompts.internal",
        headers={"Authorization": f"Bearer {token}"},
    ),
    fallback_registry,  # local InMemoryPrompts for defaults
)

rendered = registry.get("onboarding-email", user="Alice")
```
