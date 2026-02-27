# Lazy loading contract (PromptSource)

Implementations of `PromptSource` must follow this contract so that file-based and remote sources stay GC-friendly and init stays fast.

- **`keys()`:** Return the set of available keys **without** loading any prompt body. The registry calls this at init to build the key set. For file-based sources: list keys from filenames or a lightweight index only. For remote: use a list-keys endpoint only.
- **`get_prompt(key)`:** Load and return the prompt for that key. Called only when the user (or registry) requests that key via `get_prompt(key)` or `get(key, ...)`. No pre-loading of all prompts; each key is loaded on demand.

**InMemoryPrompts** already satisfies this: `keys()` returns dict keys; `get_prompt(key)` returns from the dict with no I/O. File and remote sources must not load full content in `keys()` or at registry init; only on `get_prompt(key)`.
