"""Step 1 (part 3): failure analysis on the saved baseline runs.

Reads ``results/baseline/run_<Strategy>.json`` (saved by ``run_baseline.py``)
plus the QA + qrels, classifies each (strategy, question) outcome, and writes:

* ``results/baseline/failure_report.json``  — machine-readable
* ``results/baseline/failure_report.md``    — human-readable report

Usage (from repo root, with the venv activated):
    python src/scripts/analyze_failures.py
"""
from __future__ import annotations

import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[1]))

from baseline import config  # noqa: E402
from baseline.evaluation import load_qa, load_qrels  # noqa: E402
from baseline.failure_analysis import analyze, load_runs, render_markdown  # noqa: E402


def main() -> int:
    out_dir = config.PATH_RESULTS
    runs = load_runs(out_dir)
    if not runs:
        print(f"No run_*.json files found under {out_dir}.")
        print("Run `python src/scripts/run_baseline.py` first.")
        return 1

    qa = load_qa()
    qrels = load_qrels()
    print(f"Loaded {len(runs)} strategies: {list(runs.keys())}")
    print(f"        {len(qa)} QA, {len(qrels)} with qrels")

    report = analyze(qa, qrels, runs)
    (out_dir / "failure_report.json").write_text(json.dumps(report, indent=2))
    md = render_markdown(report)
    (out_dir / "failure_report.md").write_text(md, encoding="utf-8")

    # Print a concise console summary
    print("\nOutcome counts:")
    for strat, cnt in report["per_strategy_counts"].items():
        print(f"  {strat:<12} {dict(cnt)}")
    print(f"\nOrchestration misses (this strategy missed but another succeeded):")
    for s, c in report["orchestration_miss_counts"].items():
        print(f"  {s:<12} {c}")
    print(f"\nAmbiguous-by-design questions: {report['ambiguity_count']}")
    print(f"\nWrote {out_dir / 'failure_report.md'}")
    print(f"Wrote {out_dir / 'failure_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
