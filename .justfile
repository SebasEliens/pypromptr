test:
    uv run pytest

# Run PromptRegistry.get_prompt benchmarks (pytest-benchmark)
benchmark:
    uv run pytest tests/benchmark_registry.py -m benchmark --benchmark-only -v

# Profile get_prompt: run script under cProfile and write profile_get_prompt.stats
# Inspect with: just profile-open  (or: python -m pstats profile_get_prompt.stats)
profile:
    uv run python -m cProfile -o profile_get_prompt.stats benchmarks/profile_get_prompt.py

# Open the last profile in pstats (interactive)
profile-open:
    python -m pstats profile_get_prompt.stats