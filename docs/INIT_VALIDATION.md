# Init validation behavior

When constructing a `PromptRegistry`, the key set is always built at init from the source (and optional fallback) by calling `keys()` only—no prompt bodies are loaded. This keeps init fast and GC-friendly for file-based and remote sources.

## `validate_at_init`

- **`validate_at_init=False` (default):** Only the key set is built. No call to `get_prompt(key)` is made at construction. Resolution is fully lazy on first access.
- **`validate_at_init=True`:** After building the key set, the registry calls `get_prompt(key)` for each key. If any key is not fetchable (e.g. the source raises), construction fails. Use this to fail fast when a source is misconfigured or a key is missing.

## Per-source semantics

| Source type      | `keys()` at init        | `validate_at_init=True` (per key)   |
|------------------|-------------------------|--------------------------------------|
| **InMemoryPrompts** | Returns dict keys; no I/O. | `get_prompt(key)` from dict; no I/O. |
| **File-based** (future) | List keys from filenames/index only; do not read file bodies. | Read and parse file for each key; construction may be slow or fail if a file is missing/invalid. |
| **Remote** (e.g. LangFuse) | List keys via list endpoint only; no per-key fetch. | Optionally call get/fetch per key; may be slow and depend on network. Prefer list-only at init. |

For file and remote sources, “validate” means: ensure each key in the key set is actually fetchable (e.g. file exists and parses, or API returns the prompt). When false, only the key set is built so that init remains cheap and does not load all prompt bodies.
