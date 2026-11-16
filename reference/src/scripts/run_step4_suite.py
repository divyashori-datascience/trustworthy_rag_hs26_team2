"""Step 4 run suite: extension + ablations, loading the retrievers ONCE.

Each configuration gets its own AgenticRAG (with its own LLMClient so per-run
cost is isolated) but they all share one BaselineSystem — so the expensive
GraphRAG chunk-vector cache warms a single time across the whole suite instead
of once per process.

Runs:
* extension  — full pipeline on the Step 4 reliability benchmark (15 cases)
* no_recovery / no_abstain / no_clarify — ablations on the original 25 questions

Usage:
    python -m src.scripts.run_step4_suite
"""
from __future__ import annotations

import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve()
_SRC = _HERE.parents[1]
_SCRIPTS = _HERE.parent
for _p in (str(_SRC), str(_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agentic import AgenticRAG  # noqa: E402
from agentic.llm import LLMClient  # noqa: E402
from baseline import config  # noqa: E402
from baseline.orchestration import BaselineSystem  # noqa: E402
from baseline.retrievers import load_bm25, load_dense, load_graphrag  # noqa: E402

from run_agentic import ABLATIONS, load_benchmark, run_benchmark, run_dir_for  # noqa: E402

# (benchmark, ablation) pairs to run.
SUITE = [
    ("reliability", "full"),
    ("original", "no_recovery"),
    ("original", "no_abstain"),
    ("original", "no_clarify"),
]


def main() -> int:
    if not config.have_anthropic_key():
        print("ERROR: no usable ANTHROPIC_API_KEY.")
        return 1

    print("Loading retrievers once (shared across the suite)...")
    system = BaselineSystem(bm25=load_bm25(), dense=load_dense(), graph=load_graphrag())

    for benchmark, ablation in SUITE:
        out_dir = run_dir_for(benchmark, ablation)
        print(f"\n=== {benchmark} / {ablation} -> {out_dir} ===")
        rag = AgenticRAG(system, llm=LLMClient(), **ABLATIONS[ablation])
        qa = load_benchmark(benchmark)
        summary = run_benchmark(rag, qa, out_dir, ablation)
        print(json.dumps(summary, indent=2))

    print("\nSuite complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
