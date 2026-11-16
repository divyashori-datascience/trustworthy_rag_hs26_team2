"""Summarise a run's decision traces into one audit table.

Reads every ``traces/<qid>.json`` in a run folder and prints / saves a per-question
table: profile type, expected behaviour, final action, confidence, LLM-judged
verdict, retrieval modes tried, number of recoveries, generator evidence flags,
max sufficiency and latency.

Usage (from the repo root):
    python -m src.ours.traces.audit_traces                                  # reference team's run
    python -m src.ours.traces.audit_traces --run results/<run_id>/benchmark # one of our runs
    python -m src.ours.traces.audit_traces --out docs/audit/trace_audit.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
DEFAULT_RUN = REPO / "reference" / "results" / "agentic"
LABELS = REPO / "reference" / "Baseline" / "benchmark" / "reliability_labels.json"


def load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def summarise(run: pathlib.Path) -> list[dict]:
    labels = load_json(LABELS)
    answers = load_json(run / "answers.json")
    verdicts = load_json(run / "evaluation_metrics.json").get("correctness", {}).get("per_query", {})
    rows = []
    for fp in sorted((run / "traces").glob("*.json"), key=lambda p: (len(p.stem), p.stem)):
        t = json.loads(fp.read_text(encoding="utf-8"))
        qid, tl, final = t["qid"], t["timeline"], t.get("final", {})
        suff = [s["signals"]["sufficiency"] for s in tl if s["step"] == "analyze"]
        rows.append({
            "qid": qid,
            "question": t["query"],
            "query_type": (t.get("profile") or {}).get("query_type"),
            "expected": labels.get(qid, {}).get("expected_behavior"),
            "gold_chunks": labels.get(qid, {}).get("gold_chunks"),
            "action": final.get("action"),
            "confidence": final.get("confidence"),
            "verdict": verdicts.get(qid, {}).get("verdict"),
            "modes": ">".join(s["mode"] for s in tl if s["step"] == "retrieve"),
            "recoveries": sum(1 for s in tl if s["step"] == "recover"),
            "evidence_found": "".join("T" if s.get("evidence_found") else "F" for s in tl if s["step"] == "generate"),
            "max_sufficiency": max(suff) if suff else None,
            "latency_s": (answers.get(qid) or {}).get("latency_s", t.get("latency_s")),
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(DEFAULT_RUN), help="run folder containing traces/")
    ap.add_argument("--out", default=None, help="optional CSV path")
    args = ap.parse_args()
    rows = summarise(pathlib.Path(args.run))
    if not rows:
        raise SystemExit(f"no traces found in {args.run}/traces")
    cols = list(rows[0])
    print(" | ".join(cols))
    for r in rows:
        print(" | ".join("" if r[c] is None else str(r[c]) for c in cols))
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        print(f"\nsaved {args.out}")


if __name__ == "__main__":
    main()
