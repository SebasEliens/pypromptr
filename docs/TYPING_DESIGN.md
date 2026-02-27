# Typing design: registry per-key metadata

This document describes how the registry will support per-key metadata types so that `get_prompt("welcome")` returns a prompt whose `metadata` type is known to mypy (e.g. `Prompt[GreetingMetadata]`).

## Goal

- After `prompt = registry.get_prompt("welcome")`, mypy should infer `prompt.metadata` as `GreetingMetadata` (or whatever type is associated with `"welcome"`).
- Autocomplete and type checking should work for metadata fields without casts.

## Options

### 1. Explicit overloads per key

Define one `@overload` for each known key and a fallback for `str`:

```python
@overload
def get_prompt(self, key: Literal["welcome"]) -> Prompt[GreetingMetadata]: ...
@overload
def get_prompt(self, key: Literal["system"]) -> Prompt[SystemMetadata]: ...
def get_prompt(self, key: str) -> Prompt[Any]: ...
```

- **Pros:** Simple, no extra types; exact return type per key.
- **Cons:** Requires maintaining overloads when keys change; key set must be fixed at type-check time.

### 2. TypedDict-driven mapping

Parametrize the registry by a TypedDict (or similar) mapping key names to metadata types:

```python
class MyKeys(TypedDict):
    welcome: GreetingMetadata
    system: SystemMetadata

registry: PromptRegistry[MyKeys]
prompt = registry.get_prompt("welcome")  # inferred as Prompt[GreetingMetadata]
```

- **Pros:** Single source of truth for key→metadata; scales to many keys.
- **Cons:** TypedDict keys are nominal; need a way to express “key string” → “metadata type” that mypy understands for `get_prompt(key)`.

### 3. Codegen or helper

Generate overloads or stub code from a schema (e.g. YAML or Pydantic models) so the registry’s `get_prompt` is typed per key.

- **Pros:** Keeps key set and types in sync with external config.
- **Cons:** Build step and tooling; may be unnecessary for small key sets.

## Recommendation

- **Phase 1 (Registry + InMemory):** Use **explicit overloads** for the initial API. The registry can be typed with a small set of keys (e.g. from a Literal union). This is straightforward and does not block lazy loading or multiple sources.
- **Later:** If the key set becomes large or dynamic, consider a **TypedDict-driven** or **codegen** approach; the runtime behaviour of `get_prompt(key)` stays the same, only the typing surface changes.

## Open points

- Whether `get(key, **kwargs)` returns `RenderedPrompt[Any]` or preserves the underlying prompt’s metadata type (e.g. `RenderedPrompt[GreetingMetadata]`) is left for implementation; preserving it improves DX but may require generic plumbing.
- “Key memory” and inferred prompt shape (simple vs messages, template vs not) can be reflected in overloads (e.g. `get_prompt("welcome")` → `SimplePromptTemplate[GreetingMetadata]`) once the key set and shapes are fixed at type-check time.
