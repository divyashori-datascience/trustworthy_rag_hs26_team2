"""Compare our run's final actions with the reference run and the reference labels.

Usage:
    python src/ours/eval/compare_runs.py results/<run>/actions.csv
    python src/ours/eval/compare_runs.py results/<run>/answers.json
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REF_ANSWERS = ROOT / "reference/results/agentic/answers.json"
LABELS = ROOT / "reference/Baseline/benchmark/reliability_labels.json"


def load_actions(path: Path) -> dict:
    if path.suffix == ".json":
        return {k: v["action"] for k, v in json.loads(path.read_text()).items()}
    with path.open() as f:
        return {r["qid"]: r["action"] for r in csv.DictReader(f)}


def main(path: str) -> None:
    ours = load_actions(Path(path))
    ref = {k: v["action"] for k, v in json.loads(REF_ANSWERS.read_text()).items()}
    labels = json.loads(LABELS.read_text())
    qids = sorted(ref, key=int)

    same = [q for q in qids if ours.get(q) == ref[q]]
    print(f"Same action as reference run: {len(same)}/{len(qids)}")
    for name, run in [("reference", ref), ("ours", ours)]:
        ok = sum(run.get(q) == labels[q]["expected_behavior"] for q in qids)
        print(f"Matches expected_behavior ({name}): {ok}/{len(qids)}")
    print("\nChanged actions:")
    for q in qids:
        if ours.get(q) != ref[q]:
            print(f"  Q{q}: {ref[q]} -> {ours.get(q)} (expected {labels[q]['expected_behavior']}) | {labels[q]['question']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/20261117_colab_full_run/actions.csv")
