"""Benchmarks for PromptRegistry.get_prompt overhead. Run with: pytest tests/benchmark_registry.py --benchmark-only"""

import pytest
from pydantic import BaseModel

from spidey import (
    FilePrompts,
    InMemoryPrompts,
    PromptRegistry,
    SimplePrompt,
)


class MinimalMetadata(BaseModel):
    pass


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
    registry = PromptRegistry(source, fallback=fallback)
    benchmark(registry.get_prompt, "key")


@pytest.mark.benchmark
def test_get_prompt_with_fallback_miss(benchmark):
    """Overhead of try → KeyError → fallback.get_prompt when key is only in fallback."""
    prompt = SimplePrompt(metadata=MinimalMetadata(), content="From fallback")
    source = InMemoryPrompts({"other": SimplePrompt(metadata=MinimalMetadata(), content="")})
    fallback = InMemoryPrompts({"key": prompt})
    registry = PromptRegistry(source, fallback=fallback)
    benchmark(registry.get_prompt, "key")


@pytest.mark.benchmark
def test_get_prompt_combined_registry(benchmark):
    """Overhead of chained registry (source is another registry; key in first)."""
    prompt = SimplePrompt(metadata=MinimalMetadata(), content="From first")
    first = PromptRegistry(InMemoryPrompts({"key": prompt}))
    second = PromptRegistry(InMemoryPrompts({"other": SimplePrompt(metadata=MinimalMetadata(), content="")}))
    combined = first + second
    benchmark(combined.get_prompt, "key")


@pytest.mark.benchmark
def test_get_prompt_file_prompts(benchmark, tmp_path):
    """FilePrompts: lazy load on get_prompt (includes disk I/O and parsing)."""
    (tmp_path / "key.md").write_text("Hello from file")
    registry = PromptRegistry(FilePrompts(tmp_path))
    benchmark(registry.get_prompt, "key")
