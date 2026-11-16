"""Lightweight smoke test: imports, paths, qrels/qa load — no models, no GPU.

Catches obvious wiring problems before ``run_baseline.py`` triggers the
multi-GB HuggingFace downloads.

Usage (from repo root, with the venv activated):
    python src/scripts/smoke_test.py
"""
from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[1]))


def main() -> int:
    print("[1/4] importing baseline package...")
    from baseline import config
    from baseline import evaluation, orchestration, retrievers  # noqa: F401
    print("       ok")

    print(f"\n[2/4] BASELINE_ROOT = {config.BASELINE_ROOT}")
    if not config.BASELINE_ROOT.is_dir():
        print(f"       MISSING: {config.BASELINE_ROOT}")
        return 1

    expected = {
        "BM25 pickle":       config.PATH_BM25_PICKLE,
        "Chroma dir":        config.PATH_CHROMA_DIR,
        "GraphRAG root":     config.PATH_GRAG_ROOT,
        "Lang_norm chunks":  config.PATH_LANG_NORM_PKL,
        "QA benchmark":      config.PATH_QA,
        "qrels (fixed)":     config.PATH_QRELS_FIXED,
    }
    missing = []
    for label, p in expected.items():
        ok = p.exists()
        size = ""
        if ok and p.is_file():
            size = f" ({p.stat().st_size / 1e6:.1f} MB)"
        print(f"       {'OK ' if ok else '!! '} {label:<18} {p}{size}")
        if not ok:
            missing.append(label)
    if missing:
        print(f"\n[2/4] missing artifacts: {missing}")
        return 2

    print("\n[3/4] loading QA benchmark + qrels (no models)...")
    qa = evaluation.load_qa()
    qrels = evaluation.load_qrels()
    print(f"       qa:    {len(qa)} questions")
    print(f"       qrels: {len(qrels)} questions with judgments")
    print(f"       sample question: {qa[0]['question']!r}")
    if qrels:
        sample_qid = next(iter(qrels))
        print(f"       sample qrels[{sample_qid}]: "
              f"{len(qrels[sample_qid])} relevant chunks")

    print("\n[4/4] all smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
