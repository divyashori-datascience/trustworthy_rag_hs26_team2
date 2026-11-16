"""Baseline evaluation: load qrels, run pytrec_eval, track latency.

Mirrors the previous team's ``ComprehensiveEvaluator.evaluate_retriever`` but
trimmed down to just what Step 1 needs (quantitative metrics + latency). The
qrels reader matches their original ``load_qrels`` exactly: each chunk-level
JSON file with ``relevance_score >= 0.5`` becomes a binary qrel of 1.
"""
from __future__ import annotations

import json
import pathlib
import time
from collections import defaultdict
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import pytrec_eval
from tqdm.auto import tqdm

from . import config


def load_qrels(folder: Optional[pathlib.Path] = None) -> Dict[str, Dict[str, int]]:
    folder = pathlib.Path(folder or config.PATH_QRELS_FIXED)
    qrels: Dict[str, Dict[str, int]] = defaultdict(dict)
    for fp in folder.glob("*.json"):
        chunk_id = fp.stem  # e.g. <doc_hash>_fixed_<idx>
        for qid, payload in json.loads(fp.read_text()).items():
            if payload.get("relevance_score", 0.0) >= 0.5:
                qrels[qid][chunk_id] = 1
    return dict(qrels)


def load_qa(path: Optional[pathlib.Path] = None) -> List[dict]:
    path = pathlib.Path(path or config.PATH_QA)
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_strategy(
    strategy,
    qa_data: List[dict],
    qrels: Dict[str, Dict[str, int]],
    *,
    top_k: int = 100,
    metrics: Optional[set] = None,
) -> dict:
    """Run ``strategy.search`` on every benchmark question and score with pytrec_eval.

    Returns a dict with ``summary`` (mean across queries), ``per_query`` (raw
    pytrec_eval output), and ``timings`` (wall-clock seconds per query).
    """
    metrics = metrics or config.METRICS
    run: Dict[str, Dict[str, float]] = defaultdict(dict)
    timings: List[float] = []

    for qa in tqdm(qa_data, desc=strategy.name):
        qid = str(qa["id"])
        query = qa["question"]
        t0 = time.perf_counter()
        docs = strategy.search(query, top_k=top_k)
        timings.append(time.perf_counter() - t0)
        for rank, d in enumerate(docs):
            uid = d.metadata.get("chunk_id") or d.metadata.get("record_id")
            if uid is None:
                continue
            # pytrec_eval expects scores; rank-based is fine and matches the
            # original team's `top_k - rank` convention.
            run[qid][uid] = float(top_k - rank)

    run_dict = {qid: dict(scores) for qid, scores in run.items()}
    evaluator = pytrec_eval.RelevanceEvaluator(qrels, metrics)
    per_query = evaluator.evaluate(run_dict)
    summary = {
        m: float(np.mean([s.get(m, 0.0) for s in per_query.values()]))
        for m in metrics
    }
    summary["latency_avg_s"] = float(np.mean(timings))
    summary["latency_p95_s"] = float(np.percentile(timings, 95))
    summary["queries_evaluated"] = len(per_query)

    return {
        "name": strategy.name,
        "summary": summary,
        "per_query": per_query,
        "run": run_dict,  # qid -> {chunk_id: score}, needed for failure analysis
        "timings": timings,
    }


def to_dataframe(results: List[dict]) -> pd.DataFrame:
    rows = [{"strategy": r["name"], **r["summary"]} for r in results]
    return pd.DataFrame(rows)
