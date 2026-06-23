# Changelog

All notable changes to this project will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [semantic versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-06-21

### Added
- `PromptRegistry` — single entry point with optional fallback and `+` combination.
- `InMemoryPrompts` — dict-backed source; no I/O.
- `FilePrompts` — directory of markdown files; keys from filenames; lazy load on `get_prompt(key)`.
- `FilePromptsConfig` — configurable extension, parsing strategy, and message delimiters.
- Prompt types: `SimplePrompt`, `SimplePromptTemplate`, `MessagesPrompt`, `MessagesPromptTemplate`, `RenderedPrompt`, `Message`.
- Optional LangFuse source via `pip install pypromptr[langfuse]`.
- `PromptSource` protocol and `PromptLike` type alias exported for custom backend authors.
- `PromptRegistry.aget_prompt(key)` and `PromptRegistry.aget(key, **kwargs)` — async versions of `get_prompt`/`get`; blocking source I/O runs in a thread pool via `asyncio.to_thread`.
- Module-level default registry: `register_prompt`, `register_prompt_source`, `get_prompt`, `get`, `aget_prompt`, `aget`, `clear`.

### Fixed
- `FilePrompts.get_prompt()` had a TOCTOU race (existence check then read); replaced with direct `read_text()` converting `FileNotFoundError` to `KeyError`.
