"""Benchmarks for PromptRegistry.get_prompt across all source backends.

Run with:
  pytest tests/benchmark_registry.py --benchmark-only

Optional-dependency sources (git, s3, http, sql, langfuse) are skipped
automatically when their extras are not installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from pypromptr import (
    CallablePromptSource,
    FilePrompts,
    InMemoryPrompts,
    PromptRegistry,
    SimplePrompt,
)

_PROMPTS_DIR = Path(__file__).parent.parent / "benchmarks" / "prompts"


class MinimalMetadata(BaseModel):
    pass


# ---------------------------------------------------------------------------
# InMemoryPrompts
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_get_prompt_in_memory(benchmark):
    """Baseline: dict lookup + registry try/return (InMemoryPrompts, single key)."""
    prompt = SimplePrompt(metadata=MinimalMetadata(), content="Hello")
    registry = PromptRegistry(InMemoryPrompts({"key": prompt}))
    benchmark(registry.get_prompt, "key")


@pytest.mark.benchmark
def test_get_prompt_with_fallback_hit(benchmark):
    """Overhead of try/source.get_prompt when key is in source (no KeyError)."""
    prompt = SimplePrompt(metadata=MinimalMetadata(), content="From source")
    source = InMemoryPrompts({"key": prompt})
    fallback = InMemoryPrompts({"other": SimplePrompt(metadata=MinimalMetadata(), content="")})
    registry = PromptRegistry(source, fallback)
    benchmark(registry.get_prompt, "key")


@pytest.mark.benchmark
def test_get_prompt_with_fallback_miss(benchmark):
    """Overhead of try → KeyError → next source's get_prompt when key is only in second source."""
    prompt = SimplePrompt(metadata=MinimalMetadata(), content="From fallback")
    source = InMemoryPrompts({"other": SimplePrompt(metadata=MinimalMetadata(), content="")})
    fallback = InMemoryPrompts({"key": prompt})
    registry = PromptRegistry(source, fallback)
    benchmark(registry.get_prompt, "key")


@pytest.mark.benchmark
def test_get_prompt_combined_registry(benchmark):
    """Overhead of chained registry (source is another registry; key in first)."""
    prompt = SimplePrompt(metadata=MinimalMetadata(), content="From first")
    first = PromptRegistry(InMemoryPrompts({"key": prompt}))
    second = PromptRegistry(InMemoryPrompts({"other": SimplePrompt(metadata=MinimalMetadata(), content="")}))
    combined = first + second
    benchmark(combined.get_prompt, "key")


# ---------------------------------------------------------------------------
# FilePrompts — reads from benchmarks/prompts/
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_get_prompt_file_prompts(benchmark):
    """FilePrompts: lazy load on get_prompt (disk I/O + frontmatter parsing)."""
    registry = PromptRegistry(FilePrompts(_PROMPTS_DIR))
    benchmark(registry.get_prompt, "welcome")


# ---------------------------------------------------------------------------
# CallablePromptSource — callable reads from disk via FilePrompts
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_get_prompt_callable_source(benchmark):
    """CallablePromptSource: callable reads from benchmarks/prompts/ on each call."""
    file_source = FilePrompts(_PROMPTS_DIR)
    registry = PromptRegistry(
        CallablePromptSource({
            "welcome": lambda: file_source.get_prompt("welcome"),
            "system": lambda: file_source.get_prompt("system"),
        })
    )
    benchmark(registry.get_prompt, "welcome")


# ---------------------------------------------------------------------------
# GitRepoPrompts — fake adapter (no I/O) and real local repo
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_get_prompt_git_fake_adapter(benchmark):
    """GitRepoPrompts with FakeGitAdapter: in-memory round-trip + parsing."""
    from pypromptr.sources.git import FakeGitAdapter, GitRepoPrompts

    adapter = FakeGitAdapter({
        "welcome": "Hello, {{name}}! Welcome to the service.\n",
        "system": "You are a helpful assistant.\n",
    })
    registry = PromptRegistry(GitRepoPrompts(adapter=adapter))
    benchmark(registry.get_prompt, "welcome")


@pytest.mark.benchmark
def test_get_prompt_git_local_repo(benchmark):
    """GitRepoPrompts reading benchmarks/prompts/ from the local git repo (real git I/O)."""
    pytest.importorskip("git")
    from pypromptr.sources.git import GitRepoPrompts

    repo_root = Path(__file__).parent.parent
    registry = PromptRegistry(GitRepoPrompts(local_path=repo_root, path="benchmarks/prompts"))
    benchmark(registry.get_prompt, "welcome")


# ---------------------------------------------------------------------------
# S3Prompts — fake bucket adapter (no network)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_get_prompt_s3_fake_adapter(benchmark):
    """S3Prompts with FakeBucketAdapter: in-memory round-trip + parsing."""
    from pypromptr.sources.s3 import FakeBucketAdapter, S3Prompts

    adapter = FakeBucketAdapter({
        "welcome": "Hello, {{name}}! Welcome to the service.\n",
        "system": "You are a helpful assistant.\n",
    })
    registry = PromptRegistry(S3Prompts(adapter=adapter))
    benchmark(registry.get_prompt, "welcome")


# ---------------------------------------------------------------------------
# HttpPrompts — fake HTTP adapter (no network)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_get_prompt_http_fake_adapter(benchmark):
    """HttpPrompts with FakeHttpAdapter: in-memory round-trip + parsing."""
    from pypromptr.sources.http import FakeHttpAdapter, HttpPrompt, HttpPrompts

    base = "https://prompts.example.com"
    adapter = FakeHttpAdapter({
        f"{base}/welcome": "Hello, {{name}}! Welcome to the service.\n",
        f"{base}/system": "You are a helpful assistant.\n",
    })
    registry = PromptRegistry(
        HttpPrompts(
            {
                "welcome": HttpPrompt(url=f"{base}/welcome"),
                "system": HttpPrompt(url=f"{base}/system"),
            },
            adapter=adapter,
        )
    )
    benchmark(registry.get_prompt, "welcome")


# ---------------------------------------------------------------------------
# SqlPrompts — SQLite in-memory (requires pypromptr[sql])
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_get_prompt_sql_sqlite(benchmark):
    """SqlPrompts with SQLite in-memory: full SQL round-trip + parsing."""
    pytest.importorskip("sqlalchemy")
    from sqlalchemy import create_engine, text

    from pypromptr.sources.sql import SqlPrompts

    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE TABLE prompts (key TEXT, content TEXT, metadata TEXT)"
        ))
        conn.execute(text(
            "INSERT INTO prompts VALUES ('welcome', 'Hello, {{name}}!', NULL)"
        ))
        conn.execute(text(
            "INSERT INTO prompts VALUES ('system', 'You are a helpful assistant.', NULL)"
        ))
        conn.commit()

    registry = PromptRegistry(SqlPrompts(engine=engine))
    benchmark(registry.get_prompt, "welcome")


# ---------------------------------------------------------------------------
# LangFusePrompts — fake client (no network, requires pypromptr[langfuse])
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_get_prompt_langfuse_fake_client(benchmark):
    """LangFusePrompts with a fake in-process client: parsing overhead only."""
    pytest.importorskip("langfuse")
    from pypromptr.sources.langfuse import LangFusePrompts

    class _FakePrompt:
        prompt = "Hello, {{name}}! Welcome to the service."
        config = {}

    class _FakeClient:
        class _Prompts:
            def list(self):
                return [type("P", (), {"name": "welcome"})()]

        prompts = _Prompts()

        def get_prompt(self, key: str):
            if key == "welcome":
                return _FakePrompt()
            raise Exception(f"not found: {key}")

    registry = PromptRegistry(LangFusePrompts(client=_FakeClient()))
    benchmark(registry.get_prompt, "welcome")
