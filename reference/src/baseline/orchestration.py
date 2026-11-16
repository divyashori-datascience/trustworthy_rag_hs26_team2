"""Orchestration strategies: waterfall, voting, confidence.

Ports the previous team's Step 2 / Step 3 logic into a single ``BaselineSystem``
class so the three retrievers don't have to live as module-level globals. The
parameter values (``pre_k=120``, RRF ``k=60``, weights, overlap threshold 0.05)
are kept exactly as in the original notebooks for reproducibility.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import torch
from langchain_core.documents import Document
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from . import config


# ----------------------------------------------------- query classifier
class QueryClassifierAgent:
    """FLAN-T5 classifier used by the confidence orchestrator."""

    def __init__(
        self,
        model_name: str = "google/flan-t5-base",
        device: Optional[str] = None,
        max_new_tokens: int = 32,
    ) -> None:
        self.device = device or config.DEVICE
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(self.device)
        self.max_new_tokens = max_new_tokens

    @staticmethod
    def _prompt(query: str) -> str:
        return (
            "Classify as FACTOID, SEMANTIC, or HYBRID.\n\n"
            "FACTOID = names, numbers, dates, who/when/where\n"
            "SEMANTIC = why, how, explain, conceptual\n"
            "HYBRID = mix of both\n\n"
            f"Query: {query}\n\nAnswer:"
        )

    def classify(self, query: str) -> str:
        inputs = self.tokenizer(
            self._prompt(query),
            return_tensors="pt",
            truncation=True,
            max_length=512,
        ).to(self.device)
        with torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
            )
        return self.tokenizer.decode(out[0], skip_special_tokens=True)


# ----------------------------------------------------- RRF helpers
def _uid(doc: Document) -> Optional[str]:
    return doc.metadata.get("chunk_id") or doc.metadata.get("record_id")


def _safe_unique(docs: List[Document]) -> List[Document]:
    out: List[Document] = []
    seen: set = set()
    for d in docs:
        u = _uid(d)
        if u is None or u in seen:
            continue
        seen.add(u)
        out.append(d)
    return out


def _rrf_fuse(
    runs: Dict[str, List[Document]],
    k_rrf: int = 60,
    weights: Optional[Dict[str, float]] = None,
) -> List[Document]:
    weights = weights or {"bm25": 1.0, "dense": 1.0, "graph": 0.7}
    scores: Dict[str, float] = defaultdict(float)
    store: Dict[str, Document] = {}
    for name, docs in runs.items():
        w = float(weights.get(name, 1.0))
        for rank, d in enumerate(docs, start=1):
            u = _uid(d)
            if u is None:
                continue
            store.setdefault(u, d)
            scores[u] += w * (1.0 / (k_rrf + rank))
    fused = sorted(store.values(), key=lambda d: scores[_uid(d)], reverse=True)
    for d in fused:
        d.metadata["fused_score"] = float(scores[_uid(d)])
    return fused


# ----------------------------------------------------- system
class BaselineSystem:
    """Holds the three retrievers and exposes ``waterfall / voting / confidence``."""

    def __init__(
        self,
        bm25,
        dense,
        graph,
        classifier: Optional[QueryClassifierAgent] = None,
        pre_k: int = 120,
    ) -> None:
        self.bm25 = bm25
        self.dense = dense
        self.graph = graph
        self.classifier = classifier
        self.pre_k = pre_k

    def _parallel_fusion(
        self,
        query: str,
        top_k: int = 5,
        use_graph: bool = True,
        weights: Optional[Dict[str, float]] = None,
    ) -> Tuple[List[Document], List[str]]:
        trace: List[str] = []
        bm25_docs = self.bm25.search(query, top_k=self.pre_k)
        trace.append(f"BM25 retrieved {len(bm25_docs)}")
        dense_docs = self.dense.search(query, top_k=self.pre_k)
        trace.append(f"Dense retrieved {len(dense_docs)}")
        graph_docs: List[Document] = []
        if use_graph:
            graph_docs = self.graph.retrieve(query, top_k=self.pre_k)
            trace.append(f"Graph retrieved {len(graph_docs)}")
        bm25_docs = _safe_unique(bm25_docs)
        dense_docs = _safe_unique(dense_docs)
        graph_docs = _safe_unique(graph_docs)
        fused = _rrf_fuse(
            runs={"bm25": bm25_docs, "dense": dense_docs, "graph": graph_docs},
            k_rrf=60,
            weights=weights or {"bm25": 1.2, "dense": 1.0, "graph": 0.6},
        )
        trace.append("Weighted RRF")
        return fused[:top_k], trace

    def waterfall(self, query: str, top_k: int = 5) -> Tuple[List[Document], List[str]]:
        """BM25+Dense first; only escalate to GraphRAG if top-doc word overlap < 5%."""
        docs, trace = self._parallel_fusion(
            query, top_k=top_k, use_graph=False,
            weights={"bm25": 1.2, "dense": 1.0, "graph": 0.0},
        )
        q_terms = {t.lower() for t in query.split() if t.strip()}
        if docs:
            top_text = (docs[0].metadata.get("original_text") or docs[0].page_content or "").lower()
        else:
            top_text = ""
        overlap = len(q_terms & set(top_text.split())) / max(len(q_terms), 1)
        if overlap < 0.05:
            docs2, trace2 = self._parallel_fusion(
                query, top_k=top_k, use_graph=True,
                weights={"bm25": 1.1, "dense": 1.0, "graph": 0.7},
            )
            return docs2, trace + ["Fallback: low overlap -> add Graph"] + trace2
        trace.append(f"Critic: overlap={overlap:.3f} ok")
        return docs, trace

    def voting(self, query: str, top_k: int = 5) -> Tuple[List[Document], List[str]]:
        """Parallel BM25+Dense+Graph fused with weighted RRF."""
        return self._parallel_fusion(
            query, top_k=top_k, use_graph=True,
            weights={"bm25": 1.2, "dense": 1.0, "graph": 0.6},
        )

    def confidence(self, query: str, top_k: int = 5) -> Tuple[List[Document], List[str]]:
        """Classify the query and pick weights conditionally."""
        if self.classifier is None:
            self.classifier = QueryClassifierAgent()
        cls = self.classifier.classify(query).strip().upper()
        if "FACTOID" in cls:
            w = {"bm25": 1.3, "dense": 1.0, "graph": 0.8}
            mode = "factoid -> BM25 + Graph boosted"
        elif "SEMANTIC" in cls:
            w = {"bm25": 0.9, "dense": 1.3, "graph": 0.6}
            mode = "semantic -> Dense boosted"
        else:
            w = {"bm25": 1.0, "dense": 1.1, "graph": 0.5}
            mode = "hybrid -> balanced"
        docs, trace = self._parallel_fusion(query, top_k=top_k, use_graph=True, weights=w)
        trace.insert(0, f"Confidence router: {mode}")
        return docs, trace


# ----------------------------------------------------- adapter for evaluation
class _StrategyAdapter:
    """Thin ``.search(query, top_k)`` wrapper so a strategy can be used as a retriever."""

    def __init__(self, system: BaselineSystem, strategy: str) -> None:
        self.system = system
        self.strategy = strategy
        self.name = strategy.capitalize()

    def search(self, query: str, top_k: int = 100) -> List[Document]:
        docs, _ = getattr(self.system, self.strategy)(query, top_k=top_k)
        return docs


def make_strategies(system: BaselineSystem) -> Dict[str, _StrategyAdapter]:
    return {
        "Waterfall": _StrategyAdapter(system, "waterfall"),
        "Voting": _StrategyAdapter(system, "voting"),
        "Confidence": _StrategyAdapter(system, "confidence"),
    }
