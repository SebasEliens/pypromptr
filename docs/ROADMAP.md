# Roadmap — wider usefulness after first PyPI release

This document is a **plan for future functionality** aimed at first-time PyPI maintainers learning the release cycle, and at growing **pypromptr** into a library more teams can adopt without giving up their existing stack. It complements [PRD.md](PRD.md) (product intent), [IMPLEMENTATION.md](IMPLEMENTATION.md) (phases delivered), and [FRAMEWORK_INTEGRATION.md](FRAMEWORK_INTEGRATION.md) (adapter direction).

Goals for this roadmap:

- Keep the **core small and dependency-light** (registry + `PromptSource` + prompt types).
- Add **optional extras** for templating, remote stores, and framework bridges.
- Improve **discoverability and trust** for PyPI users (docs, examples, stability).

---

## Tier A — High impact, still small surface area

These changes help strangers on PyPI adopt the library without committing to a large framework.

### A1. PyPI and onboarding polish

- **README quickstart** that shows three paths in one screen: `InMemoryPrompts`, `FilePrompts`, optional `LangFusePrompts`.
- **Changelog** (`CHANGELOG.md` or GitHub Releases) from day one; semantic versioning discipline (breaking changes in major bumps).
- **Supported Python versions** clearly stated; classifiers in `pyproject.toml` aligned with CI matrix.
- **Security / maintenance signals:** dependabot or equivalent, issue templates for bugs vs feature requests.

### A2. Optional Jinja2 (or pluggable) templating

- Today `{{key}}` substitution is intentional but limited. Offer **`pypromptr[jinja]`** (or a `TemplateEngine` protocol) so power users get conditionals and includes without forcing Jinja on minimal installs.
- Keep **default behavior** unchanged: simple replacement remains the zero-dep path.

### A3. File source ergonomics

- **Glob or recursive discovery** (optional config) for nested `prompts/**/*.md` if keys-from-flat-dir is too limiting.
- **Optional watch/reload** (extra dependency, e.g. `watchfiles`) for local dev: invalidate cache when files change—document as dev-only if production prefers explicit restart.
- **Document delimiter strategy:** `FilePromptsConfig` mentions delimiters; ensure multi-message formats (`## role` vs tags) are fully specified in README with copy-paste examples.

### A4. Remote sources: caching and failure modes

- **TTL or explicit cache** for `LangFusePrompts` (and future HTTP sources) so users can balance “fresh prompts” vs “rate limits / latency.”
- **Clear errors:** distinguish missing key, network failure, and auth failure; optional hook `on_fetch_error` for metrics/logging.
- **Timeout and retry** as optional constructor args on remote sources, with conservative defaults.

### A5. Typing story (finish the PRD promise)

- [TYPING_DESIGN.md](TYPING_DESIGN.md) outlines registry generics; **shipping** overloads or a typed registry builder improves IDE experience for library consumers.
- Public **type aliases** exported for `PromptLike` and `Message` so downstream packages don’t re-declare.

---

## Tier B — Broader integration without owning “the agent stack”

### B1. Framework adapters (extras)

- Implement the direction in [FRAMEWORK_INTEGRATION.md](FRAMEWORK_INTEGRATION.md): **`RenderedPrompt.to_langchain_messages()`** (or module `pypromptr.adapters.langchain`) behind `pypromptr[langchain-core]`.
- Second candidate: **pydantic-ai** parts adapter, same pattern—optional extra only.

### B2. Generic HTTP / Git-backed `PromptSource`

- **HTTP source:** fetch by URL pattern or small JSON API contract (document the schema). Useful for internal prompt services that are not Langfuse.
- **Git or raw URL** is higher complexity; treat as later or community-driven unless there is clear demand.

### B3. Composition helpers

- **`ChainSource`** (name TBD): ordered list of sources, first hit wins—generalizes `fallback` beyond two layers without nested `PromptRegistry` only.
- **Prefix / namespace:** map `PromptSource` keys under a prefix for large monorepos (`lib.*` vs `app.*`).

---

## Tier C — Power features and ecosystem

### C1. Version labels and environments

- Langfuse and other stores support **labels** (e.g. production vs staging). Expose optional `label=` or `environment=` on `get_prompt` / source config so the same key resolves different content per deploy.

### C2. Validation hooks

- Optional **post-load validation**: callable `validate(metadata, body_or_messages)` registered on `PromptRegistry` or per source, for schema checks or “must contain these placeholders.”

### C3. CLI (optional extra)

- **`python -m pypromptr`** or console script: list keys, render one prompt with JSON vars, dry-run from a directory—helps ops and prompt review without writing Python.

### C4. Observability

- Optional **structured logging** or **OpenTelemetry spans** around `get_prompt` / remote fetch (behind extra or env flag) for teams that already trace LLM apps.

---

## Suggested sequencing (learning-friendly for a first PyPI project)

| Phase | Focus | Why this order |
|-------|--------|----------------|
| **R0** | Release hygiene (README, changelog, version policy, CI badges) | Builds muscle for every later release. |
| **R1** | A2 templating extra + A4 caching/timeouts on Langfuse | Addresses the two most common “we outgrew the library” complaints while keeping core tiny. |
| **R2** | A5 typing + A3 file docs / optional glob | Improves day-to-day DX for real codebases. |
| **R3** | B1 one framework adapter (LangChain **or** pydantic-ai) | Proves the adapter pattern; read [FRAMEWORK_INTEGRATION.md](FRAMEWORK_INTEGRATION.md). |
| **R4** | B2 HTTP source or C1 labels | Unlocks teams not on Langfuse or needing prod/staging prompts. |
| **R5** | C3 CLI or C2 validation hooks | Nice for adoption; not blocking for core value. |

Adjust order if user feedback points elsewhere; the table is a default learning path, not a contract.

---

## Non-goals (to stay maintainable)

- **Replacing** Langfuse, LangSmith, or full prompt IDE products.
- **Owning** agent orchestration, tool calling, or RAG pipelines—stay at the boundary: **resolve + render + adapt messages**.
- **Mandatory** dependencies beyond Pydantic (and current core stack) for the default install.

---

## How to use this doc

- Turn items into **GitHub issues** with the tier label (`A2`, `B1`, …) when ready to implement.
- After each PyPI release, **revisit Tier A** for doc and changelog gaps before adding Tier C features.
