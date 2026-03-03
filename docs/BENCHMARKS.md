# Benchmarks and profiling for PromptRegistry.get_prompt

This document describes how to measure the overhead of `PromptRegistry.get_prompt` using pytest-benchmark (latency/throughput) and cProfile (where time is spent).

## Benchmarks (pytest-benchmark)

Benchmarks live in **tests/benchmark_registry.py**. They are not run by default when you execute `pytest` (the benchmark module is not named `test_*.py`, and benchmark tests are marked with `@pytest.mark.benchmark` and excluded via `addopts`).

### How to run

From the project root:

```bash
just benchmark
```

Or directly:

```bash
uv run pytest tests/benchmark_registry.py -m benchmark --benchmark-only -v
```

Or with a shorter run (fewer rounds):

```bash
uv run pytest tests/benchmark_registry.py -m benchmark --benchmark-only --benchmark-min-rounds=3
```

### What each benchmark measures

| Benchmark | Setup | What it measures |
|-----------|--------|------------------|
| **test_get_prompt_in_memory** | `PromptRegistry(InMemoryPrompts({...}))` with one key | Baseline: dict lookup + registry try/return. |
| **test_get_prompt_with_fallback_hit** | Registry with source + fallback; key in source | Overhead of try/source.get_prompt (no KeyError). |
| **test_get_prompt_with_fallback_miss** | Same; key only in fallback | Overhead of try → KeyError → fallback.get_prompt. |
| **test_get_prompt_combined_registry** | `first + second`; key in first | Overhead of chained registry (source is another registry). |
| **test_get_prompt_file_prompts** | `PromptRegistry(FilePrompts(tmp_path))` with one file | FilePrompts: lazy load on get_prompt (includes disk I/O and parsing). |

Use the reported mean time and OPS (operations per second) to compare overhead across these scenarios.

## Profiling (cProfile)

To see **where** time is spent inside `get_prompt` and the source, use the profile script and cProfile.

### How to run

From the project root:

```bash
just profile
```

Or directly:

```bash
uv run python -m cProfile -o profile_get_prompt.stats benchmarks/profile_get_prompt.py
```

This runs many `get_prompt` calls (default 100_000) and writes statistics to **profile_get_prompt.stats** in the current directory. Then run `just profile-open` to inspect interactively with pstats.

### How to inspect results

**With pstats (stdlib):**

```bash
python -m pstats profile_get_prompt.stats
```

Then at the `%` prompt you can use:

- `sort cumtime` — sort by cumulative time
- `stats` — print top 20
- `callers get_prompt` — show callers of `get_prompt`
- `callees get_prompt` — show what `get_prompt` calls

**With snakeviz (optional, for a flame graph):**

```bash
pip install snakeviz
snakeviz profile_get_prompt.stats
```

This opens a browser with an interactive flame graph of where time was spent.

### What the profile script does

**benchmarks/profile_get_prompt.py** builds a registry from `InMemoryPrompts` with two keys and calls `registry.get_prompt("a")` and `registry.get_prompt("b")` in a loop (100_000 iterations total). Profiling this run shows the cost of the registry path and dict lookup without external I/O.
