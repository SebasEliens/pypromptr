# Framework integration (future)

## Note: output format flexibility

In the future we will want to be **flexible in the output format of messages** and support **LangChain** (and possibly other agent/LLM frameworks). The current `RenderedPrompt` exposes `content` and `messages` (list of `Message` TypedDict with `role` and `content`). To support multiple frameworks without coupling Spidey to any one of them, we may introduce:

- **Adapters** or **formatters** that convert `RenderedPrompt` (or its `messages`) into framework-specific types (e.g. LangChain `BaseMessage` list, pydantic_ai parts).
- A **registry or render config** option to choose output format (e.g. “raw” messages vs “langchain” vs “pydantic_ai”), or separate methods like `.to_langchain()` / `.to_pydantic_ai()` on `RenderedPrompt`.

This doc tracks that intent and outlines what supporting various frameworks would require.

---

## Framework rundown

### LangChain / LangChain Core

- **Message format:** `BaseMessage` with subclasses: `HumanMessage`, `AIMessage`, `SystemMessage`, `ChatMessage`, `ToolMessage`, `FunctionMessage`. Each has `content` (str or list of content blocks), `type`, and optional `additional_kwargs`, `name`, `id`.
- **What we’d need:** An adapter that maps our `Message(role=..., content=...)` to the right LangChain class (`role` → `HumanMessage` / `SystemMessage` / `AIMessage` / `ChatMessage(role=...)`). Optional: support for `additional_kwargs` if we ever extend `Message` (e.g. tool_calls). No change to our core types if we keep adapters outside the core; optional dependency on `langchain-core` only in the adapter.

### Pydantic AI

- **Message format:** Request/response model with **parts**: `SystemPromptPart`, `UserPromptPart`, `ToolReturnPart`, `RetryPromptPart` (request); `TextPart`, `ToolCallPart` (response). Parts have `part_kind`, content, and metadata. Chat history is a list of these parts, not a flat list of role/content.
- **What we’d need:** An adapter that maps our `messages` (and optionally `content`) into the appropriate pydantic_ai part types. Our `role` + `content` map to `UserPromptPart` / `SystemPromptPart` (and possibly assistant content as `TextPart`). Tool messages would require extending our `Message` (e.g. optional `tool_call_id` or part-kind) or a separate convention. Optional dependency on `pydantic-ai` only in the adapter.

### Other agent frameworks (candidates)

- **LlamaIndex:** Chat messages are often a list of `ChatMessage`-like objects (role + content). Similar to our `Message`; an adapter would be straightforward.
- **Semantic Kernel (Python):** Uses `ChatMessage` / `ChatRole`; again role + content. Adapter from our `Message` list is enough.
- **CrewAI / AutoGen / other multi-agent:** Typically use their own message or “event” types. Support would mean either (1) mapping our `messages` to their format in an adapter, or (2) a generic “dict/list” export they can consume.

### What would be required in addition

1. **Keep `Message` minimal and stable:** Only add optional fields (e.g. `name`, `tool_call_id`) if we need them for a first-class adapter; otherwise keep `role` + `content` and let adapters add framework-specific fields.
2. **Adapters as optional extras:** e.g. `spidey[langchain]`, `spidey[pydantic-ai]`, so core Spidey stays dependency-light.
3. **Single canonical shape in core:** Our `RenderedPrompt.messages` stays a list of `Message`. Framework-specific types are produced by adapter functions or methods, not by changing the core model.
4. **Optional: render mode / format in registry:** If we add a “format” or “target” (e.g. `get(..., format="langchain")`), it would call the appropriate adapter before returning; that’s a design choice once we implement the first adapter.

No change to the current Phase 0 types is strictly required; the `Message` TypedDict with explicit `role` and `content` is a good base for all of the above.
