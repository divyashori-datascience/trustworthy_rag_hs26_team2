"""Step 4 evaluation harness for the agentic system.

Reads the DecisionTraces from a run plus the reliability ground-truth labels and
qrels, and computes:

* Behaviour analysis: action vs. expected-behaviour confusion, correct/false
  abstention rate, correct/false clarification rate, answer coverage.
* Groundedness: grounded-answer rate, mean grounding score, unsupported-claim rate.
* Recovery: how often recovery fired and how often it ended in a grounded answer.
* Confidence: mean confidence by action (and, with --judge, confidence↔correctness).
* Retrieval: P@5 / Recall@5 / MRR of the final retrieved chunks vs. qrels, next
  to the Step 1 baseline reference row.
* Efficiency: latency + approximate cost (from the run summary).

With ``--judge`` it additionally uses Claude to score answer correctness against
the gold answers (factual questions) and produces a confidence-calibration view.

Outputs (under the run dir): ``evaluation.md``, ``evaluation_metrics.json``,
and PNG plots.

Usage:
    python -m src.scripts.evaluate_agentic                      # results/agentic
    python -m src.scripts.evaluate_agentic --run results/agentic/no_recovery
    python -m src.scripts.evaluate_agentic --judge              # + LLM correctness
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter, defaultdict

_HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[1]))

from baseline import config  # noqa: E402

GROUNDING_MIN = 0.60


# Which extension categories correspond to answerable evidence in the corpus.
_ANSWERABLE_BY_CATEGORY = {
    "ambiguous": False,            # no single correct answer
    "insufficient_evidence": False,
    "adversarial": False,          # false premise — no supporting evidence
    "conflicting_evidence": True,
    "multilingual": True,
}


# ----------------------------------------------------------------- loading
def load_labels(source: str = "original") -> dict:
    """Load expected-behaviour labels for the original benchmark or the extension."""
    if source == "reliability":
        items = json.loads(
            (config.PATH_BENCHMARK / "benchmark_reliability.json").read_text(encoding="utf-8")
        )
        return {
            str(it["id"]): {
                "question": it["question"],
                "category": it.get("category"),
                "answerable": _ANSWERABLE_BY_CATEGORY.get(it.get("category"), False),
                "ambiguous_by_design": it.get("category") == "ambiguous",
                "expected_behavior": it["expected_behavior"],
                "acceptable_behaviors": it.get("acceptable_behaviors", [it["expected_behavior"]]),
                "gold_answer": None,
            }
            for it in items
        }
    p = config.PATH_BENCHMARK / "reliability_labels.json"
    return json.loads(p.read_text(encoding="utf-8"))


def load_qrels_map() -> dict:
    from baseline.evaluation import load_qrels

    return load_qrels()


def load_traces(run_dir: pathlib.Path) -> dict:
    traces = {}
    for fp in sorted((run_dir / "traces").glob("*.json")):
        t = json.loads(fp.read_text(encoding="utf-8"))
        traces[str(t["qid"])] = t
    return traces


def _final_retrieve_ids(trace: dict) -> list:
    ids = []
    for step in trace.get("timeline", []):
        if step.get("step") == "retrieve":
            ids = step.get("top_ids", [])
    return ids


def _last_verify(trace: dict) -> dict:
    v = {}
    for step in trace.get("timeline", []):
        if step.get("step") == "verify":
            v = step
    return v


def _recovered(trace: dict) -> bool:
    return any(s.get("step") == "recover" for s in trace.get("timeline", []))


# ----------------------------------------------------------------- metrics
def behaviour_metrics(traces: dict, labels: dict) -> dict:
    confusion = defaultdict(Counter)  # expected -> Counter(actual)
    abst_correct = abst_false = 0
    clar_correct = clar_false = 0
    answerable = answered_answerable = 0

    for qid, lab in labels.items():
        t = traces.get(qid)
        if not t:
            continue
        actual = t["final"].get("action", "?")
        expected = lab["expected_behavior"]
        confusion[expected][actual] += 1

        if actual == "abstain":
            if lab["answerable"]:
                abst_false += 1   # evidence existed, but system gave up
            else:
                abst_correct += 1
        if actual == "clarify":
            if expected == "clarify":
                clar_correct += 1
            else:
                clar_false += 1
        if lab["answerable"] and expected == "answer":
            answerable += 1
            if actual == "answer":
                answered_answerable += 1

    n_abst = abst_correct + abst_false
    n_clar = clar_correct + clar_false
    return {
        "confusion_expected_vs_actual": {k: dict(v) for k, v in confusion.items()},
        "abstention": {
            "total": n_abst,
            "correct": abst_correct,
            "false": abst_false,
            "correct_rate": round(abst_correct / n_abst, 3) if n_abst else None,
            "false_rate": round(abst_false / n_abst, 3) if n_abst else None,
        },
        "clarification": {
            "total": n_clar,
            "correct": clar_correct,
            "false": clar_false,
            "correct_rate": round(clar_correct / n_clar, 3) if n_clar else None,
        },
        "answer_coverage_on_answerable": {
            "answerable": answerable,
            "answered": answered_answerable,
            "rate": round(answered_answerable / answerable, 3) if answerable else None,
        },
    }


def groundedness_metrics(traces: dict) -> dict:
    answers = [t for t in traces.values() if t["final"].get("action") == "answer"]
    if not answers:
        return {"n_answers": 0}
    grounded = 0
    gsum = 0.0
    unsupported = 0
    for t in answers:
        g = float(t["final"].get("signals", {}).get("grounding", 0.0))
        gsum += g
        if g >= GROUNDING_MIN:
            grounded += 1
        v = _last_verify(t)
        unsupported += len(v.get("unsupported_claims", []) or [])
    n = len(answers)
    return {
        "n_answers": n,
        "grounded_answer_rate": round(grounded / n, 3),
        "mean_grounding_score": round(gsum / n, 3),
        "mean_unsupported_claims": round(unsupported / n, 3),
    }


def recovery_metrics(traces: dict) -> dict:
    recovered = [t for t in traces.values() if _recovered(t)]
    if not recovered:
        return {"n_recovered": 0}
    success = sum(
        1
        for t in recovered
        if t["final"].get("action") == "answer"
        and float(t["final"].get("signals", {}).get("grounding", 0.0)) >= GROUNDING_MIN
    )
    return {
        "n_recovered": len(recovered),
        "recovery_success": success,
        "recovery_success_rate": round(success / len(recovered), 3),
        "recovered_qids": [t["qid"] for t in recovered],
    }


def confidence_by_action(traces: dict) -> dict:
    buckets = defaultdict(list)
    for t in traces.values():
        a = t["final"].get("action", "?")
        c = t["final"].get("confidence")
        if c is not None:
            buckets[a].append(float(c))
    return {
        a: {"n": len(v), "mean_confidence": round(sum(v) / len(v), 3)}
        for a, v in buckets.items()
    }


def retrieval_metrics(traces: dict, labels: dict, qrels: dict) -> dict:
    p5 = r5 = rr = 0.0
    counted = 0
    for qid, lab in labels.items():
        gold = set(qrels.get(qid, {}))
        if not gold:
            continue
        t = traces.get(qid)
        if not t:
            continue
        ids = _final_retrieve_ids(t)[:5]
        hits = [i for i, cid in enumerate(ids) if cid in gold]
        p5 += len(hits) / 5.0
        r5 += len(hits) / len(gold)
        rr += (1.0 / (hits[0] + 1)) if hits else 0.0
        counted += 1
    if not counted:
        return {}
    return {
        "n_with_gold": counted,
        "P@5": round(p5 / counted, 4),
        "Recall@5": round(r5 / counted, 4),
        "MRR@5": round(rr / counted, 4),
        "note": "computed on the agentic system's FINAL retrieved top-5 (post-recovery)",
    }


def baseline_reference() -> dict:
    import csv

    p = config.PATH_RESULTS / "metrics_summary.csv"
    if not p.exists():
        return {}
    rows = list(csv.DictReader(p.open()))
    if not rows:
        return {}
    best = max(rows, key=lambda r: float(r.get("recip_rank", 0)))
    return {
        "strategy": best["strategy"],
        "P@5": round(float(best["P_5"]), 4),
        "Recall@5": round(float(best["recall_5"]), 4),
        "MRR": round(float(best["recip_rank"]), 4),
        "latency_avg_s": round(float(best["latency_avg_s"]), 2),
    }


# ----------------------------------------------------------------- optional LLM judge
_JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["correct", "partially_correct", "incorrect"]},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
    "additionalProperties": False,
}
_JUDGE_SYSTEM = (
    "You grade a candidate answer against a gold answer for an ETH Zurich QA "
    "benchmark. Return 'correct' if the candidate contains the gold answer, "
    "'partially_correct' if it is on the right track but incomplete or hedged, "
    "and 'incorrect' otherwise. Judge meaning, not wording."
)


def judge_correctness(traces: dict, labels: dict) -> dict:
    from agentic.llm import default_client

    llm = default_client()
    if not llm.available:
        return {"error": "no API key; --judge skipped"}
    results = {}
    for qid, lab in labels.items():
        t = traces.get(qid)
        if not t or t["final"].get("action") != "answer":
            continue
        gold = lab.get("gold_answer")
        if not gold:
            continue  # open-ended; no single gold to grade against
        data = llm.complete_json(
            system=_JUDGE_SYSTEM,
            user=f"Question: {lab['question']}\nGold answer: {gold}\nCandidate answer: {t['final'].get('answer')}",
            schema=_JUDGE_SCHEMA,
            model=config.AGENT_MODEL_UTILITY,
            max_tokens=300,
        )
        results[qid] = {
            "verdict": data["verdict"],
            "confidence": t["final"].get("confidence"),
            "reason": data["reason"],
        }
    dist = Counter(v["verdict"] for v in results.values())
    # confidence by verdict (alignment)
    by_v = defaultdict(list)
    for v in results.values():
        if v["confidence"] is not None:
            by_v[v["verdict"]].append(float(v["confidence"]))
    align = {k: round(sum(x) / len(x), 3) for k, x in by_v.items()}
    return {
        "n_judged": len(results),
        "verdict_counts": dict(dist),
        "mean_confidence_by_verdict": align,
        "per_query": results,
    }


# ----------------------------------------------------------------- plots
def make_plots(traces: dict, run_dir: pathlib.Path) -> list:
    paths = []
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return paths

    # confidence by action (box/scatter)
    by_action = defaultdict(list)
    for t in traces.values():
        by_action[t["final"].get("action", "?")].append(
            float(t["final"].get("confidence", 0.0))
        )
    if by_action:
        fig, ax = plt.subplots(figsize=(6, 4))
        actions = sorted(by_action)
        ax.boxplot([by_action[a] for a in actions], labels=actions)
        ax.set_ylabel("confidence")
        ax.set_title("Confidence by final action")
        fig.tight_layout()
        p = run_dir / "confidence_by_action.png"
        fig.savefig(p, dpi=120)
        plt.close(fig)
        paths.append(p.name)
    return paths


# ----------------------------------------------------------------- report
def render_md(run_dir: pathlib.Path, m: dict) -> str:
    L = ["# Step 4 — Agentic System Evaluation", ""]
    L.append(f"Run: `{run_dir}`  |  questions: {m['n_questions']}")
    L.append("")

    L.append("## Action distribution")
    L.append("| action | n |")
    L.append("|---|---|")
    for a, n in sorted(m["action_counts"].items()):
        L.append(f"| {a} | {n} |")
    L.append("")

    b = m["behaviour"]
    L.append("## Behaviour vs. expected (reliability ground truth)")
    L.append("Confusion — rows = expected, cols = actual:")
    L.append("")
    acts = ["answer", "abstain", "clarify"]
    L.append("| expected \\ actual | " + " | ".join(acts) + " |")
    L.append("|---|" + "|".join("---" for _ in acts) + "|")
    for exp in ["answer", "abstain", "clarify"]:
        row = b["confusion_expected_vs_actual"].get(exp, {})
        L.append(f"| {exp} | " + " | ".join(str(row.get(a, 0)) for a in acts) + " |")
    L.append("")
    L.append(f"- **Answer coverage on answerable**: {b['answer_coverage_on_answerable']['answered']}"
             f"/{b['answer_coverage_on_answerable']['answerable']} "
             f"(rate {b['answer_coverage_on_answerable']['rate']})")
    L.append(f"- **Abstention**: {b['abstention']['total']} total — "
             f"correct {b['abstention']['correct']}, false {b['abstention']['false']} "
             f"(false-abstention rate {b['abstention']['false_rate']})")
    L.append(f"- **Clarification**: {b['clarification']['total']} total — "
             f"correct {b['clarification']['correct']}, false {b['clarification']['false']}")
    L.append("")

    g = m["groundedness"]
    L.append("## Groundedness (answered questions)")
    if g.get("n_answers"):
        L.append(f"- grounded-answer rate: **{g['grounded_answer_rate']}** "
                 f"(grounding ≥ {GROUNDING_MIN})")
        L.append(f"- mean grounding score: {g['mean_grounding_score']}")
        L.append(f"- mean unsupported claims per answer: {g['mean_unsupported_claims']}")
    L.append("")

    r = m["recovery"]
    L.append("## Adaptive recovery")
    if r.get("n_recovered"):
        L.append(f"- queries that triggered recovery: {r['n_recovered']} ({', '.join('Q'+q for q in r['recovered_qids'])})")
        L.append(f"- recovery success (ended in grounded answer): {r['recovery_success']} "
                 f"(rate {r['recovery_success_rate']})")
    else:
        L.append("- no recovery triggered in this run")
    L.append("")

    L.append("## Confidence by action")
    L.append("| action | n | mean confidence |")
    L.append("|---|---|---|")
    for a, v in sorted(m["confidence_by_action"].items()):
        L.append(f"| {a} | {v['n']} | {v['mean_confidence']} |")
    L.append("")

    L.append("## Retrieval quality vs. Step 1 baseline")
    rm, base = m["retrieval"], m["baseline_reference"]
    if rm and base:
        L.append("| system | P@5 | Recall@5 | MRR |")
        L.append("|---|---|---|---|")
        L.append(f"| Step 1 baseline ({base['strategy']}) | {base['P@5']} | {base['Recall@5']} | {base['MRR']} |")
        L.append(f"| Agentic (final top-5) | {rm['P@5']} | {rm['Recall@5']} | {rm['MRR@5']} |")
        L.append("")
        L.append(f"_{rm['note']}._")
    L.append("")

    if "correctness" in m:
        c = m["correctness"]
        L.append("## Answer correctness (LLM-judged, factual questions)")
        if "error" in c:
            L.append(f"- {c['error']}")
        else:
            L.append(f"- judged: {c['n_judged']}  |  verdicts: {c['verdict_counts']}")
            L.append(f"- mean confidence by verdict (calibration): {c['mean_confidence_by_verdict']}")
        L.append("")

    e = m["efficiency"]
    L.append("## Efficiency")
    L.append(f"- latency avg/max: {e.get('latency_avg_s')}s / {e.get('latency_max_s')}s")
    L.append(f"- approx. LLM cost (run): ${e.get('est_cost_usd')}")
    L.append("")

    if m.get("plots"):
        L.append("## Plots")
        for p in m["plots"]:
            L.append(f"![{p}]({p})")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(config.PATH_AGENTIC_RESULTS), help="run dir")
    ap.add_argument("--judge", action="store_true", help="LLM-judge answer correctness")
    ap.add_argument(
        "--labels",
        choices=["auto", "original", "reliability"],
        default="auto",
        help="which expected-behaviour labels to score against",
    )
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows console is cp1252 by default
    except Exception:  # noqa: BLE001
        pass

    run_dir = pathlib.Path(args.run)
    traces = load_traces(run_dir)
    if not traces:
        print(f"No traces found under {run_dir}/traces")
        return 1
    label_source = args.labels
    if label_source == "auto":
        label_source = "reliability" if "reliability" in run_dir.parts else "original"
    labels = load_labels(label_source)
    qrels = load_qrels_map()

    metrics = {
        "n_questions": len(traces),
        "action_counts": dict(Counter(t["final"].get("action", "?") for t in traces.values())),
        "behaviour": behaviour_metrics(traces, labels),
        "groundedness": groundedness_metrics(traces),
        "recovery": recovery_metrics(traces),
        "confidence_by_action": confidence_by_action(traces),
        "retrieval": retrieval_metrics(traces, labels, qrels),
        "baseline_reference": baseline_reference(),
    }
    # efficiency from run summary if present
    summ = run_dir / "run_summary.json"
    if summ.exists():
        s = json.loads(summ.read_text())
        metrics["efficiency"] = {
            "latency_avg_s": s.get("latency_avg_s"),
            "latency_max_s": s.get("latency_max_s"),
            "est_cost_usd": s.get("llm_usage", {}).get("est_cost_usd"),
        }
    else:
        metrics["efficiency"] = {}

    if args.judge:
        metrics["correctness"] = judge_correctness(traces, labels)

    metrics["plots"] = make_plots(traces, run_dir)

    (run_dir / "evaluation_metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    md = render_md(run_dir, metrics)
    (run_dir / "evaluation.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"\nWrote {run_dir}/evaluation.md and evaluation_metrics.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
