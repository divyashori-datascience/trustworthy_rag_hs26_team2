"""Derive reliability ground-truth labels for the original 25-question benchmark.

For Step 4 we need, per question, the *expected* high-level behaviour so we can
score correct vs. false abstention / clarification. We derive it from data we
already trust rather than hand-labelling:

* ``clarify``  — the question is ambiguous-by-design (Step 1 ``is_ambiguous``
  heuristic over the benchmark notes).
* ``abstain``  — the answer is not in the corpus (no gold chunks / qrels), so an
  ideal system should decline rather than fabricate.
* ``answer``   — gold evidence exists in the corpus, so the question is
  answerable (even if Step 1 retrieval ranked it poorly).

``answerable`` (gold > 0) is recorded separately so the evaluator can flag a
*false abstention* = abstaining on a question whose evidence is actually present.

Output: ``Baseline/benchmark/reliability_labels.json``.
"""
from __future__ import annotations

import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[1]))

from baseline import config  # noqa: E402
from baseline.evaluation import load_qa, load_qrels  # noqa: E402
from baseline.failure_analysis import is_ambiguous  # noqa: E402


def main() -> int:
    qa = load_qa()
    qrels = load_qrels()
    labels = {}
    for it in qa:
        qid = str(it["id"])
        gold = len(qrels.get(qid, {}))
        ambiguous = is_ambiguous(it)
        if ambiguous:
            expected = "clarify"
        elif gold == 0:
            expected = "abstain"
        else:
            expected = "answer"
        labels[qid] = {
            "question": it["question"],
            "gold_chunks": gold,
            "answerable": gold > 0,           # evidence exists in corpus
            "ambiguous_by_design": ambiguous,
            "expected_behavior": expected,
            "gold_answer": it.get("answer"),  # present for factual questions
        }
    out = config.PATH_BENCHMARK / "reliability_labels.json"
    out.write_text(json.dumps(labels, indent=2, ensure_ascii=False), encoding="utf-8")
    from collections import Counter

    dist = Counter(v["expected_behavior"] for v in labels.values())
    print(f"Wrote {out}  ({len(labels)} questions; expected {dict(dist)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
