"""Failure taxonomy for the retrieval-only baseline.

For each (strategy, query) pair we classify the outcome as one of:

* ``success``           - at least one relevant chunk in the top-5
* ``partial_recall``    - some relevant chunks in top-5, but not all
* ``ranking_failure``   - relevant chunks retrieved (top-100) but none in top-5
* ``retrieval_failure`` - no relevant chunks even in top-100
* ``no_qrels``          - the question has no gold judgments (excluded from rates)
* ``ambiguous``         - tagged from the QA notes; the question is under-specified
                          and an ideal system would clarify rather than answer

Two more taxonomy classes from the assignment require an answer-generation layer
that the previous-semester baseline does not have, so we cannot detect them
from retrieval alone:

* ``synthesis_failure``     - evidence present, generated answer wrong
* ``grounding_failure``     - generated answer contains unsupported claims
* ``overconfidence_failure``- confident answer despite weak evidence
* ``contradiction_failure`` - retrieved chunks conflict; system handled it badly

These are reported as "needs generator" and become motivation for the Step 2/3
extensions (verifier, abstention, critic loop, etc.).
"""
from __future__ import annotations

import json
import pathlib
import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional

from . import config


# Heuristics for spotting ambiguity-by-design questions in the benchmark notes.
_AMBIGUOUS_NOTE_PATTERNS = [
    r"ambiguous",
    r"prefer(?:red)?[^\n]{0,40}(?:clarification|ask)",
    r"deflect",
    r"should(?:n['']?t| not) favor",
    r"score is .{0,40}for every",   # the "+1 / -1" judging style implies open-ended
]


def is_ambiguous(qa_item: dict) -> bool:
    notes = (qa_item.get("notes") or "").lower()
    if not notes:
        return False
    return any(re.search(p, notes) for p in _AMBIGUOUS_NOTE_PATTERNS)


def _ranked_ids(scores: Dict[str, float]) -> List[str]:
    return [cid for cid, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]


def _classify_one(
    retrieved: List[str],
    gold: Dict[str, int],
    *,
    cutoff_top: int = 5,
    cutoff_pool: int = 100,
) -> dict:
    """Classify one (query, strategy) outcome from its run + qrels."""
    if not gold:
        return {"tag": "no_qrels", "hits_top": 0, "hits_pool": 0,
                "ranks_of_gold": [], "n_gold": 0}

    top = retrieved[:cutoff_top]
    pool = retrieved[:cutoff_pool]
    gold_set = set(gold)
    hits_top = gold_set & set(top)
    hits_pool = gold_set & set(pool)

    # ranks of every gold doc within the full retrieved list (1-indexed; -1 if not there)
    rank_lookup = {cid: i + 1 for i, cid in enumerate(retrieved)}
    ranks_of_gold = sorted(
        rank_lookup.get(g, -1) for g in gold_set
    )

    if not hits_pool:
        tag = "retrieval_failure"
    elif not hits_top:
        tag = "ranking_failure"
    elif len(hits_top) < min(len(gold_set), cutoff_top):
        tag = "partial_recall"
    else:
        tag = "success"

    return {
        "tag": tag,
        "hits_top": len(hits_top),
        "hits_pool": len(hits_pool),
        "ranks_of_gold": ranks_of_gold,
        "n_gold": len(gold_set),
    }


def analyze(
    qa_data: List[dict],
    qrels: Dict[str, Dict[str, int]],
    runs: Dict[str, Dict[str, Dict[str, float]]],
    *,
    cutoff_top: int = 5,
    cutoff_pool: int = 100,
) -> dict:
    """Build the structured failure report.

    runs[strategy][qid] = {chunk_id: score}  (output of evaluate_strategy)
    Returns a dict ready for json.dump + report rendering.
    """
    qid2qa = {str(q["id"]): q for q in qa_data}
    strategies = list(runs.keys())

    per_query: Dict[str, dict] = {}
    for qid, qa in qid2qa.items():
        gold = qrels.get(qid, {})
        ambig = is_ambiguous(qa)
        outcomes = {}
        for strat in strategies:
            ranked = _ranked_ids(runs[strat].get(qid, {}))
            outcomes[strat] = _classify_one(
                ranked, gold,
                cutoff_top=cutoff_top, cutoff_pool=cutoff_pool,
            )
        # Cross-strategy: orchestration failure flag.
        # "This strategy missed it but at least one other got it."
        per_strat_misses = {}
        any_success = any(o["tag"] in ("success", "partial_recall") for o in outcomes.values())
        for strat, o in outcomes.items():
            other_success = any(
                outcomes[s]["tag"] in ("success", "partial_recall")
                for s in strategies if s != strat
            )
            per_strat_misses[strat] = bool(
                o["tag"] in ("ranking_failure", "retrieval_failure") and other_success
            )

        per_query[qid] = {
            "question": qa.get("question", ""),
            "n_gold": len(gold),
            "ambiguous": ambig,
            "outcomes": outcomes,
            "orchestration_miss": per_strat_misses,  # per strategy: did the *system* pick wrong?
            "any_strategy_succeeded": any_success,
        }

    # aggregate counts per strategy
    per_strategy_counts: Dict[str, Counter] = {s: Counter() for s in strategies}
    orch_miss_counts: Dict[str, int] = {s: 0 for s in strategies}
    for qid, info in per_query.items():
        for s in strategies:
            per_strategy_counts[s][info["outcomes"][s]["tag"]] += 1
            if info["orchestration_miss"][s]:
                orch_miss_counts[s] += 1

    ambiguity_count = sum(1 for v in per_query.values() if v["ambiguous"])

    return {
        "config": {
            "n_questions": len(qid2qa),
            "n_with_qrels": sum(1 for q in qid2qa if qrels.get(q)),
            "strategies": strategies,
            "cutoff_top": cutoff_top,
            "cutoff_pool": cutoff_pool,
        },
        "per_strategy_counts": {s: dict(c) for s, c in per_strategy_counts.items()},
        "orchestration_miss_counts": orch_miss_counts,
        "ambiguity_count": ambiguity_count,
        "per_query": per_query,
    }


# ----------------------------------------------------------- report rendering
_TAG_ORDER = ["success", "partial_recall", "ranking_failure",
              "retrieval_failure", "no_qrels"]


def render_markdown(report: dict) -> str:
    cfg = report["config"]
    strats = cfg["strategies"]
    lines: List[str] = []

    lines.append("# Baseline Failure Analysis (Step 1)")
    lines.append("")
    lines.append(
        f"Benchmark: **{cfg['n_questions']} questions**, "
        f"{cfg['n_with_qrels']} with relevance judgments. "
        f"Top-k cutoff = {cfg['cutoff_top']}, retrieval pool = {cfg['cutoff_pool']}."
    )
    lines.append("")
    lines.append(
        "Out-of-scope for retrieval-only baseline (need answer generator): "
        "*synthesis_failure*, *grounding_failure*, *overconfidence_failure*, "
        "*contradiction_failure*. These motivate the Step 2/3 extensions."
    )
    lines.append("")

    # ---- per-strategy summary table
    lines.append("## Outcome distribution per strategy")
    lines.append("")
    header = "| Strategy | " + " | ".join(_TAG_ORDER) + " | orch. miss | "
    sep = "|---|" + "|".join("---" for _ in _TAG_ORDER) + "|---|"
    lines.append(header)
    lines.append(sep)
    for s in strats:
        row = [s]
        for tag in _TAG_ORDER:
            row.append(str(report["per_strategy_counts"][s].get(tag, 0)))
        row.append(str(report["orchestration_miss_counts"][s]))
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append(
        f"*ambiguous-by-design questions in benchmark*: "
        f"**{report['ambiguity_count']}**"
    )
    lines.append("")

    # ---- per-query detail
    lines.append("## Per-query outcomes")
    lines.append("")
    for qid, info in sorted(report["per_query"].items(), key=lambda kv: int(kv[0])):
        flag = " (ambiguous-by-design)" if info["ambiguous"] else ""
        lines.append(f"### Q{qid}{flag} — \"{info['question']}\"")
        lines.append(f"- gold chunks: **{info['n_gold']}**, "
                     f"any strategy succeeded: {info['any_strategy_succeeded']}")
        for s in strats:
            o = info["outcomes"][s]
            ranks = o["ranks_of_gold"]
            ranks_str = ", ".join(str(r) if r > 0 else "—" for r in ranks) or "—"
            orch = "  ← orch. miss" if info["orchestration_miss"][s] else ""
            lines.append(
                f"  - **{s}**: `{o['tag']}` | "
                f"top-5 hits: {o['hits_top']}/{o['n_gold']} | "
                f"top-100 hits: {o['hits_pool']}/{o['n_gold']} | "
                f"gold ranks: [{ranks_str}]{orch}"
            )
        lines.append("")

    # ---- recommendations
    lines.append("## Implications for Step 2 / Step 3")
    lines.append("")
    lines.append(
        "Map each observed failure mode to the assignment's reliability "
        "mechanisms. Use the counts above to prioritise:"
    )
    lines.append("")
    lines.append(
        "- **retrieval_failure** → (G) recovery: rewrite query, switch retrieval "
        "strategy, retrieve again. Indicates corpus coverage / lexical mismatch."
    )
    lines.append(
        "- **ranking_failure** → (B) groundedness verification + (F) self-reflection / "
        "critic loop: relevant evidence is there but the system can't surface it."
    )
    lines.append(
        "- **partial_recall** → (A) evidence-sufficiency estimation + (B) verifier: "
        "we got *some* gold but not enough to ground a confident answer."
    )
    lines.append(
        "- **orchestration_miss** → (G + H) adaptive routing with confidence/trust "
        "scoring: a different strategy already had the answer; the router picked "
        "wrong. Strong case for a learned policy."
    )
    lines.append(
        "- **ambiguous-by-design** → (D) clarification strategy + (E) abstention. "
        "Benchmark notes explicitly flag these as 'should ask for clarification'."
    )
    lines.append(
        "- **out-of-scope (synthesis / grounding / overconfidence)** → demands an "
        "answer generator + (B) verifier + (E) abstention + (H) confidence score. "
        "These are unobservable in retrieval-only mode but are central to the "
        "reliability story we'll build in Steps 2-3."
    )
    return "\n".join(lines)


def load_runs(results_dir: Optional[pathlib.Path] = None) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Load run_<Strategy>.json files saved by run_baseline.py."""
    results_dir = pathlib.Path(results_dir or config.PATH_RESULTS)
    runs: Dict[str, Dict[str, Dict[str, float]]] = {}
    for fp in sorted(results_dir.glob("run_*.json")):
        name = fp.stem[len("run_"):]
        runs[name] = json.loads(fp.read_text())
    return runs
