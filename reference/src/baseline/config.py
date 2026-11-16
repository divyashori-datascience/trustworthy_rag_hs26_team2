"""Paths and constants for the local baseline.

Resolves all data paths relative to ``BASELINE_ROOT`` (env var, optionally set
via ``.env`` at the repo root). Defaults to ``<repo>/Baseline``.
"""
from __future__ import annotations

import os
import pathlib

import torch
from dotenv import load_dotenv

# Load .env from repo root if present
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
load_dotenv(_REPO_ROOT / ".env")

REPO_ROOT: pathlib.Path = _REPO_ROOT
BASELINE_ROOT: pathlib.Path = pathlib.Path(
    os.getenv("BASELINE_ROOT", str(REPO_ROOT / "Baseline"))
).resolve()

# storage layout
STORAGE = BASELINE_ROOT / "storage"
FULL_CORPUS = STORAGE / "full_corpus"
SUBSAMPLE = STORAGE / "subsample"
CORPUS_ROOT = FULL_CORPUS  # which slice we evaluate on

# Prebuilt retriever artifacts (full corpus, fixed-size chunks)
PATH_BM25_PICKLE = CORPUS_ROOT / "retrieval" / "fixed_size_chunk" / "bm25_retriever_full.pkl"
PATH_CHROMA_DIR = CORPUS_ROOT / "vectordb_dense" / "fixed_e5"
PATH_GRAG_ROOT = CORPUS_ROOT / "retrieval_graph"
PATH_LANG_NORM_PKL = CORPUS_ROOT / "Lang_norm" / "fixed_size_chunk" / "docs_fixed_norm.pkl"

# Benchmark
PATH_BENCHMARK = BASELINE_ROOT / "benchmark"
PATH_QA = PATH_BENCHMARK / "benchmark_qa_bilingual.json"
PATH_QRELS_FIXED = PATH_BENCHMARK / "score" / "fixed_size"

# Outputs
PATH_RESULTS = REPO_ROOT / "results" / "baseline"
PATH_AGENTIC_RESULTS = REPO_ROOT / "results" / "agentic"
PATH_AGENTIC_TRACES = PATH_AGENTIC_RESULTS / "traces"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ---------------------------------------------------------------- LLM (Claude)
# The Step 3 agentic system (answer generation, verification, query rewriting,
# query profiling) calls Claude via the Anthropic SDK. Models are configurable
# so the cheap bulk benchmark runs and the high-quality demo runs can differ.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# Generation / verification default to a strong model; profiling + rewriting are
# light tasks that a faster model handles well. Override via .env.
AGENT_MODEL_GENERATION = os.getenv("AGENT_MODEL_GENERATION", "claude-opus-4-7")
AGENT_MODEL_VERIFIER = os.getenv("AGENT_MODEL_VERIFIER", "claude-opus-4-7")
AGENT_MODEL_UTILITY = os.getenv("AGENT_MODEL_UTILITY", "claude-haiku-4-5")


def have_anthropic_key() -> bool:
    """True when a usable Anthropic key is configured (not the placeholder)."""
    return bool(ANTHROPIC_API_KEY) and "replace" not in ANTHROPIC_API_KEY

# pytrec_eval metric set used by the previous team
METRICS = {
    "P_1", "P_3", "P_5", "P_10",
    "recall_5", "recall_10", "recall_100",
    "recip_rank",
    "ndcg_cut_5", "ndcg_cut_10",
}
