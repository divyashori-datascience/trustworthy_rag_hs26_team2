"""Load the benchmarks used in Step 3 into one common format.

Each item is a dict with:
    id, question, category, expected (primary final outcome),
    acceptable (set of acceptable final outcomes, lower case),
    reference (gold / reference answer or None)

Two sources:
* the instructor's development benchmark (80 questions, JSONL), and
* the original 25 questions with their ORIGINAL labels (reliability_labels.json),
  which must be used unchanged (instructor decision, 19 Nov).
"""
from __future__ import annotations

import json
import os
import pathlib

# Repo root; in Colab the notebook sets G02_ROOT to where it wrote the data files.
ROOT = pathlib.Path(os.environ.get("G02_ROOT", pathlib.Path(__file__).resolve().parents[3]))
DEV_JSONL = ROOT / "benchmark" / "dev" / "Development_Benchmark_v1.0.jsonl"
ORIGINAL_LABELS = ROOT / "reference" / "Baseline" / "benchmark" / "reliability_labels.json"


def _clean_ref(text):
    if not text:
        return None
    t = str(text).strip()
    # "(No answer: ...)" marks abstention cases: there is no gold answer to grade against.
    return None if t.startswith("(No answer") else t


def load_dev(path=None) -> list[dict]:
    path = path or DEV_JSONL
    items = []
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        acc = {a.strip().lower() for a in str(r["acceptable_final_outcomes"]).split("|") if a.strip()}
        items.append({
            "id": r["case_id"],
            "question": r["question"],
            "category": r["category"],
            "group": r["group_id"],
            "expected": r["expected_final_outcome"].lower(),
            "acceptable": acc,
            "reference": _clean_ref(r.get("reference_answer")),
        })
    return items


def load_original(path=None) -> list[dict]:
    path = path or ORIGINAL_LABELS
    labels = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    items = []
    for qid in sorted(labels, key=int):
        L = labels[qid]
        exp = L["expected_behavior"].lower()
        items.append({
            "id": str(qid),
            "question": L["question"],
            "category": "original",
            "group": "original",
            "expected": exp,
            "acceptable": {exp},
            "reference": L.get("gold_answer"),
        })
    return items


def to_qa(items: list[dict]) -> list[dict]:
    """Items for the reference system's run_benchmark(): id + question ONLY.

    No category, notes or labels are passed, so the system cannot see the answer key
    (the reference profiler reads ambiguity hints from qa_item['notes'] otherwise).
    """
    return [{"id": it["id"], "question": it["question"]} for it in items]
