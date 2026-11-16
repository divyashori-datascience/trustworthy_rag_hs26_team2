"""RetrievalCoordinator — wraps the Step 1 BaselineSystem for the agent loop.

No new retrievers are built. This is a thin adapter that:

* exposes the three baseline orchestration strategies (waterfall / voting /
  confidence) *and* the three single retrievers (bm25 / dense / graphrag) as
  named "modes" the PolicyController can pick between per query, and
* accepts a (possibly rewritten) query string plus a list of already-tried
  modes, so a recovery step can switch to a mode not yet used.

Returning a uniform ``List[Chunk]`` decouples the rest of the pipeline from the
LangChain ``Document`` objects the baseline produces.
"""
from __future__ import annotations

from typing import List, Optional

from langchain_core.documents import Document

from baseline.orchestration import BaselineSystem

from .state import Chunk

# Modes the PolicyController may request.
ORCH_MODES = ("waterfall", "voting", "confidence")
SINGLE_MODES = ("bm25", "dense", "graphrag")
ALL_MODES = ORCH_MODES + SINGLE_MODES


def _uid(d: Document) -> Optional[str]:
    return d.metadata.get("chunk_id") or d.metadata.get("record_id")


def _score(d: Document) -> float:
    for key in ("fused_score", "dense_score", "bm25_score", "grag_score"):
        if key in d.metadata:
            return float(d.metadata[key])
    return 0.0


def _to_chunks(docs: List[Document]) -> List[Chunk]:
    out: List[Chunk] = []
    for d in docs:
        uid = _uid(d)
        if uid is None:
            continue
        text = d.metadata.get("original_text") or d.page_content or ""
        out.append(
            Chunk(
                chunk_id=uid,
                text=text,
                score=_score(d),
                source=d.metadata.get("language", ""),
            )
        )
    return out


class RetrievalCoordinator:
    def __init__(self, system: BaselineSystem) -> None:
        self.system = system

    def retrieve(self, query: str, mode: str, top_k: int = 8) -> List[Chunk]:
        """Run one mode and return the top-k chunks as Chunk objects."""
        mode = mode.lower()
        if mode in ORCH_MODES:
            docs, _trace = getattr(self.system, mode)(query, top_k=top_k)
        elif mode == "bm25":
            docs = self.system.bm25.search(query, top_k=top_k)
        elif mode == "dense":
            docs = self.system.dense.search(query, top_k=top_k)
        elif mode == "graphrag":
            docs = self.system.graph.retrieve(query, top_k=top_k)
        else:
            raise ValueError(f"unknown retrieval mode: {mode!r}")
        return _to_chunks(docs)[:top_k]

    @staticmethod
    def next_mode(query_type: str, tried: List[str]) -> str:
        """Pick a recovery mode not yet tried, preferring complementary signals.

        Order reflects the Step 1 finding that no single strategy dominates:
        if the type-default failed, try a fusion strategy, then graph, then the
        remaining single retrievers.
        """
        order = ["voting", "graphrag", "confidence", "dense", "bm25", "waterfall"]
        for m in order:
            if m not in tried:
                return m
        return "voting"
