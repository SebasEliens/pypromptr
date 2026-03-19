# Spidey — Phased Implementation Roadmap

This document defines the implementation phases for Spidey. Each phase ends with a usable slice and a gate so the team can re-evaluate and change course before continuing.

Reference: [PRD](PRD.md).

---

## Phase 0: Typing and core prompt types

**Objective:** Introduce the prompt type hierarchy and design registry typing so that `get_prompt("key")` is mypy-safe with per-key metadata types.

**Tasks:**

- Introduce **SimplePrompt** and **MultiPrompt** (metadata + content vs metadata + messages); no template placeholders.
- Introduce **SimplePromptTemplate** and **MultiPromptTemplate** (same shape, with placeholders; require `.render(**kwargs)` or equivalent).
- Ensure **all four types** expose `.render()`; for non-template types, render is identity (no placeholders).
- Keep **RenderedPrompt** (or equivalent) as the result of render; align with existing `Prompt`/`RenderedPrompt` in codebase where possible.
- **Metadata:** Pydantic model per prompt; validated at load time.
- **Registry typing design:** Decide how the key set and key→metadata (and key→prompt type) mapping are expressed so that `get_prompt("welcome")` returns e.g. `Prompt[GreetingMetadata]` or `SimplePromptTemplate[GreetingMetadata]`. Options: explicit overloads per key, TypedDict-driven mapping, or a small codegen/helper. Document the chosen approach in an ADR or typing design doc.

**Deliverables:**

- Type hierarchy (SimplePrompt, MultiPrompt, SimplePromptTemplate, MultiPromptTemplate) in code.
- Typing design doc or ADR describing overload/registry parametrization.
- No (or minimal) change to existing registry behavior yet; focus is types and design.

**Gate:** Confirm the overload/registry design is implementable and does not block later phases (e.g. lazy loading, multiple sources).

---

## Phase 1: Registry API and InMemoryPrompts

**Objective:** Implement the primary API: `PromptRegistry(source, fallback=...)` and an InMemoryPrompts source so that users can build a registry from one or two in-memory sources.

**Tasks:**

- **PromptRegistry(source, fallback=None, **config):** Constructor takes a primary `PromptSource` and an optional fallback. Resolve keys from source first, then fallback when key is missing (exact semantics: first-wins or fallback-only-on-miss to be decided).
- **InMemoryPrompts(PromptSource):** Accept a `dict[str, Prompt]` (or equivalent); values may be any of the four prompt types (heterogeneous). Implement the source contract (e.g. `keys()` and `get(key)` or the agreed interface from Phase 0).
- **get_prompt(key)** and **get(key, **kwargs):** Implement on the registry; delegate to source(s). For InMemoryPrompts, no I/O.
- Tests: registry from one InMemoryPrompts; registry from source + fallback; `get_prompt` and `get` with template variables where applicable.

**Deliverables:**

- Working `PromptRegistry(source, fallback=...)` with InMemoryPrompts.
- Tests covering single source, fallback, and render.

**Gate:** API feels right; fallback semantics are clear and documented.

---

## Phase 2: Registry combination and index-at-init

**Objective:** Support combining two registries with `+` and build an in-memory index of keys (and optionally types) at init, with configurable validation.

**Tasks:**

- Implement **registry1 + registry2**: return a new registry that resolves keys from the first, then the second (or second overrides first—document choice). Type of the combined registry (key set, metadata types) to be defined in line with Phase 0 typing.
- **At init:** For each source, build a key set (and optionally type map). Do not load full prompt bodies for file-based or remote sources; keep init GC-friendly.
- **Configurable `validate_at_init`:** When true, optionally validate that each key is fetchable/parseable (e.g. call get for each key); when false, only list keys (and infer types if the source supports it). Document behavior per source type (in-memory, file, remote).
- Document what “validate” means for each source (e.g. for remote: list-only vs full fetch per key).

**Deliverables:**

- `+` operator for registries; tests.
- Documented init validation behavior and config.

**Gate:** Agreement on validation semantics per source type; no performance regression for large key sets when using list-only.

---

## Phase 3: Lazy loading

**Objective:** Refactor the PromptSource contract and registry so that prompt bodies are loaded on demand; file-based and remote sources do not hold all prompts in memory.

**Tasks:**

- **PromptSource contract:** Add or standardize methods for lazy resolution: e.g. `keys()` (or `key_set()`) and `get_prompt(key)` (or `get(key)`). Optionally keep `load()` for backward compatibility or deprecate.
- **Registry:** `get_prompt(key)` calls the source’s getter; no pre-loading of all prompts at init for file/remote sources. For InMemoryPrompts, getter returns from the internal dict.
- **File-based sources:** Do not read all files at init; only build key set (e.g. from filenames or a lightweight scan). On `get_prompt(key)`, read and parse the corresponding file. Ensure no long-lived references to full content at init so GC can reclaim.
- **Remote sources:** Same pattern: init = list keys (and optionally validate); get = fetch by key on demand.

**Deliverables:**

- Lazy load on `get_prompt(key)` for file and remote sources; InMemoryPrompts unchanged (no regression).
- Updated contract and any migration notes for existing sources.

**Gate:** File-based source only loads on demand; init remains fast and GC-friendly.

---

## Phase 4: FilePrompts

**Objective:** Implement FilePrompts as a PromptSource with configurable extension, parsing strategy, and message delimiters; dict-based config validation.

**Tasks:**

- **FilePrompts(path, config=None):** `path` is Path or str to a directory. Default config: `FilePromptsConfig(extension=".md", parsing_strategy="markdown", message_delimiters=MessageDelimiters(user="<user>", system="<system>", assistant="<assistant>"))`.
- **FilePromptsConfig and MessageDelimiters:** Pydantic models (or equivalent); accept dict input and validate. Document fields (extension, parsing_strategy, message_delimiters; user, system, assistant).
- **Parsing strategy "markdown":** Implement frontmatter + body; message sections via `## role` and/or delimiters (e.g. `<user>...</user>`). Align with existing MarkdownPromptSource behavior where useful.
- **Other strategies:** Defer or stub (e.g. "yaml", "json") unless required for MVP.
- Tests: FilePrompts in a registry; config from dict; default and custom delimiters.

**Deliverables:**

- FilePrompts source with default and dict-validated config; tests.

**Gate:** Config and delimiters match PRD; decision on deprecating or aligning existing MarkdownPromptSource (Phase 6).

---

## Phase 5: LangFuse (and store pattern)

**Objective:** Add LangFuse as an optional prompt source; document the pattern for other stores (LangSmith, Helicone, generic HTTP).

**Tasks:**

- **LangFusePromptSource(PromptSource):** Implement lazy get by key; at init, list prompt keys (and optionally validate if `validate_at_init` is true). Use LangFuse API for prompts (exact endpoint set to be chosen).
- **Auth / env:** Support configuration via environment variables or explicit config (API key, host); document in README or docs.
- **Optional dependency:** LangFuse SDK as extra (e.g. `pip install spideyprompt[langfuse]`); no mandatory dependency on LangFuse.
- **Documentation:** Short “Adding a prompt store” guide: implement PromptSource with `keys()` and `get_prompt(key)`; list LangSmith, Helicone, generic HTTP as future candidates.

**Deliverables:**

- LangFuse source as optional extra; docs and one end-to-end test (or integration test with env or mock).
- Pattern doc for other stores.

**Gate:** One external store works end-to-end; pattern is clear for others.

---

## Phase 6: Polish and docs

**Objective:** Finalize public API; update README; document that FilePrompts is the markdown source and add migration notes.

**Tasks:**

- **MarkdownPromptSource:** FilePrompts is the markdown source; there is no separate MarkdownPromptSource to deprecate. Document this in README and IMPLEMENTATION.
- **Public API:** Finalize exports and document in README (PromptRegistry, InMemoryPrompts, FilePrompts, prompt types; optional LangFusePrompts from `spideyprompt.langfuse_source`). No deprecated `from_mapping` or `load_source` in codebase.
- **README:** Quick start with `PromptRegistry(source, fallback=...)`, InMemoryPrompts/FilePrompts; lazy loading and typing; optional LangFuse and `spideyprompt[langfuse]`.
- **Migration notes:** For users coming from a hypothetical old API: use `PromptRegistry(InMemoryPrompts(mapping))` or `PromptRegistry(FilePrompts(path))`; no separate loaders.

**Deliverables:**

- Consistent public API; updated README; FilePrompts documented as the markdown source; short migration note in README.

**Gate:** Ready for release; no breaking surprises for documented use cases.

---

## How this surfaces unknowns

- **Phase 0:** Forces typing and prompt-type decisions (overload strategy, key→type representation).
- **Phase 2:** Forces validation semantics per source (list-only vs full fetch; behavior for remote).
- **Phase 3:** Forces the Source contract (lazy vs eager; method names and signatures).
- **Phase 4 & 5:** Force config (FilePrompts, MessageDelimiters) and store API choices (LangFuse endpoints, auth).

After each phase, the team can re-scope (e.g. simplify typing, drop a source, or move lazy loading to a later phase) before continuing.
