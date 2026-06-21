"""Profile PromptRegistry.get_prompt by calling it many times under cProfile.

Run from project root:
  uv run python -m cProfile -o profile_get_prompt.stats benchmarks/profile_get_prompt.py

Then inspect with:
  python -m pstats profile_get_prompt.stats
  # or: snakeviz profile_get_prompt.stats
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src is on path when run as script
_root = Path(__file__).resolve().parent.parent
if str(_root / "src") not in sys.path:
    sys.path.insert(0, str(_root / "src"))

from pypromptr import InMemoryPrompts, PromptRegistry, SimplePrompt
from pydantic import BaseModel


class MinimalMetadata(BaseModel):
    pass


def run_many_get_prompt(n: int = 100_000) -> None:
    registry = PromptRegistry(
        InMemoryPrompts({
            "a": SimplePrompt(metadata=MinimalMetadata(), content="A"),
            "b": SimplePrompt(metadata=MinimalMetadata(), content="B"),
        })
    )
    for _ in range(n):
        registry.get_prompt("a")
        registry.get_prompt("b")


if __name__ == "__main__":
    run_many_get_prompt()
