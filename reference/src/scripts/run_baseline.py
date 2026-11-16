"""Step 1 baseline reproduction entry point.

Loads the prebuilt BM25 / Dense / GraphRAG retrievers, runs the three
orchestration strategies (waterfall, voting, confidence) on the bilingual
benchmark, and writes ``metrics_summary.csv`` + ``per_query_<strategy>.json``
under ``results/baseline/``.

Usage (from repo root, with the venv activated):
    python -m src.scripts.run_baseline
or:
    python src/scripts/run_baseline.py
"""
from __future__ import annotations

import json
import pathlib
import sys

# Allow ``python src/scripts/run_baseline.py`` (without -m) to find the package.
_HERE = pathlib.Path(__file__).resolve()
_SRC = _HERE.parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from baseline import config  # noqa: E402
from baseline.evaluation import evaluate_strategy, load_qa, load_qrels, to_dataframe  # noqa: E402
from baseline.orchestration import BaselineSystem, make_strategies  # noqa: E402
from baseline.retrievers import load_bm25, load_dense, load_graphrag  # noqa: E402


def main() -> None:
    print(f"BASELINE_ROOT = {config.BASELINE_ROOT}")
    print(f"DEVICE        = {config.DEVICE}")
    out_dir = config.PATH_RESULTS
    out_dir.mkdir(parents=True, exist_ok=True)

    # -------- Load retrievers
    print("\nLoading BM25 (also initialises m2m100 translator)...")
    bm25 = load_bm25()
    print(f"  ok ({len(bm25.retrievers)} language buckets)")

    print("Loading Dense (initialising e5-large)...")
    dense = load_dense()
    print("  ok")

    print("Loading GraphRAG...")
    graph = load_graphrag()
    print("  ok")

    system = BaselineSystem(bm25=bm25, dense=dense, graph=graph)
    strategies = make_strategies(system)

    # -------- Benchmark + qrels
    qa = load_qa()
    qrels = load_qrels()
    print(f"\nBenchmark: {len(qa)} questions, {len(qrels)} have qrels")

    # -------- Evaluate
    results = []
    for name, strat in strategies.items():
        print(f"\n--- {name} ---")
        r = evaluate_strategy(strat, qa, qrels, top_k=100)
        results.append(r)
        (out_dir / f"per_query_{name}.json").write_text(
            json.dumps(r["per_query"], indent=2)
        )
        (out_dir / f"run_{name}.json").write_text(json.dumps(r["run"], indent=2))

    df = to_dataframe(results)
    summary_path = out_dir / "metrics_summary.csv"
    df.to_csv(summary_path, index=False)

    print(f"\nWrote {summary_path}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
