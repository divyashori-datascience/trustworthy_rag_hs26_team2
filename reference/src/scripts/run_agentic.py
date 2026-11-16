"""Run the Step 3 agentic system over a benchmark, saving traces + answers.

Outputs (under the run dir):
* ``traces/<qid>.json`` — one DecisionTrace per query (interpretability artifact).
* ``answers.json``      — compact per-query summary.
* ``run_summary.json``  — action counts, latency, approximate LLM cost.

Usage (from repo root, venv active, ANTHROPIC_API_KEY set in .env):
    python -m src.scripts.run_agentic                          # full original benchmark
    python -m src.scripts.run_agentic --limit 3                # first 3 questions (smoke)
    python -m src.scripts.run_agentic --ablation no_recovery   # an ablation
    python -m src.scripts.run_agentic --benchmark reliability  # the Step 4 extension cases
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from collections import Counter

_HERE = pathlib.Path(__file__).resolve()
_SRC = _HERE.parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from agentic import AgenticRAG  # noqa: E402
from baseline import config  # noqa: E402
from baseline.evaluation import load_qa  # noqa: E402

ABLATIONS = {
    "full": {},
    "no_recovery": {"enable_recovery": False},
    "no_abstain": {"enable_abstain": False},
    "no_clarify": {"enable_clarify": False},
}


def load_benchmark(name: str) -> list:
    """Load either the original bilingual benchmark or the Step 4 extension."""
    if name == "reliability":
        path = config.PATH_BENCHMARK / "benchmark_reliability.json"
        return json.loads(path.read_text(encoding="utf-8"))
    return load_qa()


def run_dir_for(benchmark: str, ablation: str) -> pathlib.Path:
    base = config.PATH_AGENTIC_RESULTS
    if benchmark == "reliability":
        base = base / "reliability"
    return base if ablation == "full" else base / ablation


def run_benchmark(rag: AgenticRAG, qa: list, out_dir: pathlib.Path, ablation: str) -> dict:
    """Run one configured pipeline over the questions and write the artifacts."""
    (out_dir / "traces").mkdir(parents=True, exist_ok=True)
    usage0 = rag.llm.usage.as_dict()  # snapshot for per-run cost delta

    answers = {}
    actions = Counter()
    latencies = []
    for item in qa:
        qid = str(item["id"])
        query = item["question"]
        t0 = time.perf_counter()
        trace = rag.answer(qid, query, item)
        dt = time.perf_counter() - t0
        latencies.append(dt)
        actions[trace.final.get("action", "?")] += 1
        (out_dir / "traces" / f"{qid}.json").write_text(
            json.dumps(trace.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        answers[qid] = {
            "question": query,
            "action": trace.final.get("action"),
            "answer": trace.final.get("answer"),
            "clarifying_question": trace.final.get("clarifying_question"),
            "confidence": trace.final.get("confidence"),
            "mode_used": trace.final.get("mode_used"),
            "latency_s": round(dt, 2),
        }
        print(f"  {qid:<4} [{trace.final.get('action'):>8}] "
              f"conf={trace.final.get('confidence')} ({dt:.1f}s) {query[:50]}")

    (out_dir / "answers.json").write_text(
        json.dumps(answers, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    # per-run usage delta
    u1 = rag.llm.usage.as_dict()
    usage_delta = {
        "calls": u1["calls"] - usage0["calls"],
        "input_tokens": u1["input_tokens"] - usage0["input_tokens"],
        "output_tokens": u1["output_tokens"] - usage0["output_tokens"],
        "est_cost_usd": round(u1["est_cost_usd"] - usage0["est_cost_usd"], 4),
    }
    summary = {
        "ablation": ablation,
        "n_questions": len(qa),
        "action_counts": dict(actions),
        "latency_avg_s": round(sum(latencies) / max(len(latencies), 1), 2),
        "latency_max_s": round(max(latencies), 2) if latencies else 0.0,
        "models": {
            "generation": config.AGENT_MODEL_GENERATION,
            "verifier": config.AGENT_MODEL_VERIFIER,
            "utility": config.AGENT_MODEL_UTILITY,
        },
        "llm_usage": usage_delta,
    }
    (out_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only the first N questions")
    ap.add_argument("--ablation", choices=list(ABLATIONS), default="full")
    ap.add_argument("--benchmark", choices=["original", "reliability"], default="original")
    ap.add_argument("--out", default=None, help="override output dir")
    args = ap.parse_args()

    if not config.have_anthropic_key():
        print("ERROR: no usable ANTHROPIC_API_KEY. Copy .env.example to .env and set it.")
        return 1

    out_dir = pathlib.Path(args.out) if args.out else run_dir_for(args.benchmark, args.ablation)
    print("Loading retrievers (loads/downloads models on first run)...")
    rag = AgenticRAG.from_pretrained(**ABLATIONS[args.ablation])
    print(f"Benchmark={args.benchmark}  Ablation={args.ablation}")

    qa = load_benchmark(args.benchmark)
    if args.limit:
        qa = qa[: args.limit]

    summary = run_benchmark(rag, qa, out_dir, args.ablation)
    print(f"\nWrote {out_dir}")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
