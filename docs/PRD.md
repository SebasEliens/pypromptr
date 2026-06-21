# Spidey — Product Requirements Document

## 1. Problem statement and goals

### Why Spidey exists

Teams need a single, stable way to use prompts in code while being able to change where those prompts live. Today, prompts might start as string literals, move to markdown files in a repo, then to an external prompt store (e.g. LangFuse, LangSmith). Each move usually forces API changes, different loading logic, and duplicated typing. Spidey solves this by treating prompts as a **key–value registry** whose **source** is pluggable: the same usage in code works whether the backend is in-memory dicts, a directory of markdown files, or a remote prompt store.

### Goals

- **Swappable backends:** Users can switch from strings in code → directory of files → external prompt store without changing how they call `get_prompt("key")` or `get("key", **kwargs)`.
- **Single entry point:** One constructor, `PromptRegistry(source, fallback=...)`, where `source` and optional `fallback` are `PromptSource` implementations. No separate “load from mapping” vs “load from source” APIs for the common case.
- **Strong typing:** Prompts have Pydantic-validated metadata; the type of that metadata is known to mypy after `get_prompt("key")` (per-key metadata types via overloads).
- **Lazy and up-to-date:** At runtime, fetching a prompt is lazy so that changes in the store (e.g. LangFuse) are visible without restarting the app; file-based sources do not hold all prompt bodies in memory at once.

### Target users

- **Application developers** who want to read prompts by key and render them with template variables.
- **Prompt engineers** who want to move prompts from code to files or to a prompt management platform without breaking existing code.

---

## 2. User stories and usage

### User stories

- As a developer, I want to **start with prompts as strings in code**, then **move them to a directory of markdown files**, then **to an external prompt store** (e.g. LangFuse), without changing how my application calls the registry.
- As a developer, I want to **combine multiple prompt registries** (e.g. app prompts + shared library prompts) with a single operation, e.g. `combined = app_prompts + lib_prompts`.
- As a developer, I want **strong typing** so that after `prompt = registry.get_prompt("welcome")`, mypy knows the metadata type and I get autocomplete and type checking.
- As a developer, I want **lazy loading** so that when I use an external store, the latest version of the prompt is used on each access, and when I use a file directory, not all files are loaded into memory at startup.

### Intended API (usage only; no implementation)

**Registry from a single source (optional fallback):**

```python
from pypromptr import PromptRegistry, InMemoryPrompts, FilePrompts

# In-memory
prompts = PromptRegistry(InMemoryPrompts({"welcome": welcome_prompt}))

# File directory (with optional config)
prompts = PromptRegistry(FilePrompts("prompts/"))

# With fallback: try source first, then fallback if key missing
prompts = PromptRegistry(FilePrompts("prompts/"), fallback=InMemoryPrompts(defaults))
```

**Key–value access:**

```python
# Get prompt object (lazy load from source when applicable)
prompt = prompts.get_prompt("welcome")

# Get rendered prompt (template variables passed here)
rendered = prompts.get("welcome", name="Alice")
```

**Combining registries:**

```python
combined = app_prompts + shared_prompts
prompt = combined.get_prompt("shared.intro")
```

**Typing:** The registry is typed so that `get_prompt("welcome")` returns a prompt whose metadata type is known (e.g. `Prompt[GreetingMetadata]`); the exact mechanism (overloads per key or TypedDict-driven) is a design detail documented in the data model and typing appendix.

---

## 3. Data model and types

### Prompt type hierarchy

Spidey supports four prompt kinds, distinguished by **shape** (single content vs multiple messages) and **templating** (static vs template with placeholders):

| Type | Shape | Templating | Primary fields |
|------|--------|------------|----------------|
| **SimplePrompt** | Single content block | No | `metadata`, `content` |
| **MessagesPrompt** | Multiple messages (roles + content) | No | `metadata`, `messages` |
| **SimplePromptTemplate** | Single content block | Yes | `metadata`, `content` (with placeholders); `.render(**kwargs)` |
| **MessagesPromptTemplate** | Multiple messages | Yes | `metadata`, `messages` (with placeholders); `.render(**kwargs)` |

- **Metadata** is always a Pydantic model (user-defined or a generic “allow extra” model). It is validated at load time.
- **All prompt types** expose a `.render(**kwargs)` (or `.render(values=..., mode=..., engine=...)`) for consistency. For non-template prompts, render is effectively identity (no placeholders). Template prompts require the appropriate variables to be passed.
- **RenderedPrompt** is the result of render: it carries the same metadata and the final messages (or single content as a single message) and is used by the registry’s `get()`.

### Inferred vs forced type

At instantiation, the registry/source can **infer** whether a prompt is template vs not and simple vs message (e.g. from presence of placeholders and number of message blocks). It is also possible to **configure** a source or registry to force “always treat as messages” and/or “always treat as templated” for a given key or globally.

### Per-key metadata typing (mypy)

The registry shall support **per-key metadata types** so that after `get_prompt("welcome")` the type of `prompt.metadata` is known to mypy (e.g. `GreetingMetadata`). The intended mechanism is **overloads** (or equivalent) so that for a registry typed with a mapping from key to metadata type, `get_prompt("welcome")` returns `Prompt[GreetingMetadata]` and similarly for other keys. The exact overload strategy (explicit overloads per key vs TypedDict-driven) is to be fixed in implementation (Phase 0).

### Open design points (to resolve in early phases)

- Representation of “key memory” and “inferred type” (e.g. key → `SimplePromptTemplate[SomeMeta]`) and how that feeds the return type of `get_prompt`.
- Whether `get()` returns a generic `RenderedPrompt[Any]` or a type that preserves the metadata type from the underlying prompt.

---

## 4. Registry and sources

### Registry API

- **Construction:** `PromptRegistry(source, fallback=None, **config)` where `source` and `fallback` are `PromptSource` instances. Config may include e.g. `validate_at_init`, `mode` (render mode), `template_engine`.
- **Access:** `get_prompt(key)` returns the prompt object (lazy-loaded when applicable). `get(key, **kwargs)` returns a `RenderedPrompt` (renders the prompt with the given template variables).
- **Combination:** `registry1 + registry2` returns a new registry that resolves keys from the first, then the second (order and override semantics to be defined; typically “first wins” or “second overrides first”).

### Source contract (extensibility)

- **PromptSource** is the protocol (or base) that all backends implement. Users extend Spidey by implementing a custom `PromptSource` (e.g. subclass and override the relevant methods).
- The contract supports:
  - **At instantiation:** Validation of the source (configurable: list keys only vs full validation) and building an in-memory index of keys and, where possible, inferred prompt types (template vs not, messages vs not).
  - **At runtime:** Lazy resolution by key (e.g. `get(key)` or `load_key(key)`) so that the registry does not need to hold all prompt bodies in memory and external stores can return the latest version on each access.
- Built-in sources (InMemory, File, LangFuse) follow the same contract so that their implementation is straightforward and similar to what an extension would do.

### Loading semantics

- **Init:** Validate the source (configurable via e.g. `validate_at_init`: if true, optionally validate that each key is fetchable/parseable; if false, only list keys and infer types where possible). Build a key set (and optionally type map) without holding full content for file-based and remote sources so that init remains GC-friendly.
- **Runtime:** `get_prompt(key)` triggers a load for that key when the source is lazy (file-based, remote). In-memory source may return from an internal dict without I/O. No requirement to cache; each `get_prompt` can re-fetch from the store so that updates in LangFuse (or similar) are visible.

---

## 5. Built-in sources (spec)

### InMemoryPrompts (PromptSource)

- **Constructor:** `InMemoryPrompts(mapping)` where `mapping` is a dict from string keys to Prompt values. Values may be any of the four prompt types (SimplePrompt, MessagesPrompt, SimplePromptTemplate, MessagesPromptTemplate); the source is heterogeneous.
- **Behavior:** At init, the source “validates” by iterating the keys (and optionally the prompt types). At runtime, `get_prompt(key)` returns the value from the dict (no I/O; “lazy” only in the sense that the registry does not copy all prompts into itself at init if we adopt a lazy registry that delegates to the source).
- **Use case:** Start with prompts in code; easy to swap to FilePrompts or a store later by changing the single `PromptRegistry(source, ...)` call.

### FilePrompts (PromptSource)

- **Constructor:** `FilePrompts(path, config=None)` where `path` is a `Path` or `str` pointing to a directory of prompt files. `config` is optional and defaults to `FilePromptsConfig(extension=".md", parsing_strategy="markdown", message_delimiters=MessageDelimiters(user="<user>", system="<system>", assistant="<assistant>"))`.
- **Config:** `FilePromptsConfig` has at least `extension`, `parsing_strategy`, and `message_delimiters`. `MessageDelimiters` has at least `user`, `system`, `assistant` (and optionally `tool`). Both `FilePromptsConfig` and `MessageDelimiters` can be passed as dicts and are validated internally (e.g. via Pydantic).
- **Behavior:** At init, the source discovers keys (e.g. from filenames or frontmatter) and infers types; it does not load full bodies into memory. At runtime, `get_prompt(key)` reads and parses the corresponding file. Parsing strategy `"markdown"` means frontmatter + body with message sections (e.g. `## system`, `## user` or delimiters like `<system>...</system>`). Other strategies (e.g. `"yaml"`, `"json"`) may be stubbed or deferred.
- **Extension point:** Same PromptSource contract; custom parsers or strategies can be added by subclassing or composing.

---

## 6. External stores

### LangFuse (first-class)

- **Scope:** Spidey will support LangFuse as the first external prompt store. The implementation will use the LangFuse API for prompts (exact endpoint set to be chosen: prompts vs datasets).
- **Auth / env:** Credentials and endpoint configuration via environment variables or explicit config (e.g. API key, host); exact env names to be specified in implementation.
- **Behavior:** Lazy fetch by key; at init, list prompt keys (and optionally validate). No requirement to cache; each `get_prompt(key)` can call the API so that edits in LangFuse are reflected on the next access.

### Other stores (candidates for future phases)

- **LangSmith:** Same use case as LangFuse (prompt management and versioning). Different API and auth; candidate for a future phase once LangFuse integration is stable.
- **Helicone:** Observability and prompt management; add if there is user demand.
- **Generic HTTP/API:** A small abstraction (e.g. “HTTP prompt source” with URL template and headers) would allow custom or internal REST prompt APIs without implementing a new store per vendor. Keeps the door open for any REST-based store.

These are listed in the PRD as options; no commitment to implement in the initial roadmap beyond LangFuse.

---

## 7. Non-goals and constraints

- **Python:** 3.13+.
- **Dependencies:** Pydantic 2 for metadata and config validation. No mandatory dependency on LangFuse/LangSmith; they are optional extras.
- **UI:** No UI for editing or browsing prompts; Spidey is a library only.

---

## Appendix A: Open questions

- Exact overload strategy for per-key metadata (explicit overloads vs TypedDict/key–type map).
- Semantics of `parsing_strategy` beyond `"markdown"` and interaction of `message_delimiters` with `## role` vs `<role>...</role>` in file format.
- LangFuse: which API (prompts vs datasets), and exact env/config for auth.

---

## Appendix B: Typing strategy (placeholder)

The implementation will document how the registry is parametrized (e.g. by key set and key → metadata type) and how `get_prompt` overloads are generated or declared so that mypy infers the correct metadata type per key. To be detailed in Phase 0 (typing and core prompt types).
