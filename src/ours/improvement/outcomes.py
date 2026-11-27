"""Ground truth for calibration: was a given output acceptable, and how good was it?

For every (run, question) row:

* y      graded correctness of an ANSWER (1 correct, 0.5 partially correct, 0 incorrect),
         or 0 when the benchmark does not accept ANSWER for this question
         (e.g. an abstain or clarify case that the system answered anyway).
         None when ANSWER is acceptable but there is no reference answer to grade against.
* score_answer / score_abstain   the row's value if the system answers / abstains.
         These drive the abstention gate and the end-to-end reliability score.

Correctness comes from the reference team's LLM judge prompt (same wording, same
utility model), so our numbers stay comparable with theirs.
"""
from __future__ import annotations

from typing import Callable, Optional

VERDICT_SCORE = {"correct": 1.0, "partially_correct": 0.5, "incorrect": 0.0}

# Identical to reference/src/scripts/evaluate_agentic.py (_JUDGE_SYSTEM / _JUDGE_SCHEMA).
JUDGE_SYSTEM = (
    "You grade a candidate answer against a gold answer for an ETH Zurich QA "
    "benchmark. Return 'correct' if the candidate contains the gold answer, "
    "'partially_correct' if it is on the right track but incomplete or hedged, "
    "and 'incorrect' otherwise. Judge meaning, not wording."
)
JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["correct", "partially_correct", "incorrect"]},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
    "additionalProperties": False,
}


def needs_judging(item: dict, trace: dict) -> bool:
    return (trace["final"].get("action") == "answer"
            and "answer" in item["acceptable"] and bool(item.get("reference")))


def judge_run(items: list[dict], traces: dict, grade: Callable[[str, str, str], dict],
              cache: Optional[dict] = None) -> dict:
    """grade(question, gold, candidate) -> {'verdict', 'reason'}. Returns {qid: {...}}."""
    out = dict(cache or {})
    for it in items:
        t = traces.get(it["id"])
        if t is None or it["id"] in out or not needs_judging(it, t):
            continue
        out[it["id"]] = grade(it["question"], it["reference"], t["final"].get("answer") or "")
    return out


def outcome(item: dict, trace: dict, verdict: Optional[dict]) -> dict:
    action = trace["final"].get("action")
    acc = item["acceptable"]
    if "answer" not in acc:
        y = 0.0
    elif not item.get("reference"):
        y = None                        # acceptable to answer, nothing to grade against
    elif verdict is not None:
        y = VERDICT_SCORE[verdict["verdict"]]
    else:
        y = None
    score_answer = (1.0 if y is None else y) if "answer" in acc else 0.0
    score_abstain = 1.0 if "abstain" in acc else 0.0
    return {
        "action": action,
        "action_ok": action in acc,
        "y": y if action == "answer" else None,
        "score_answer": score_answer,
        "score_abstain": score_abstain,
        "score_as_is": score_answer if action == "answer" else (1.0 if action in acc else 0.0),
    }
