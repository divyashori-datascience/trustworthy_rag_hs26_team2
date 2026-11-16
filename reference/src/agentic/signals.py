"""EvidenceAnalyzer — computes the reliability-signal vector.

Two cheap, local (no-LLM) signals are computed *before* generation so the
PolicyController can decide whether the evidence is even worth answering from:

* ``sufficiency``      — is there enough relevant evidence? A blend of
  query↔chunk semantic relevance, query-entity coverage, and chunk agreement.
* ``chunk_agreement``  — do the retrieved chunks talk about the same thing?
  Mean pairwise cosine of the top-k chunk embeddings (low ⇒ noisy retrieval).

``grounding`` and ``contradiction`` come from the LLM Verifier *after*
generation; ``confidence`` is the aggregate reported alongside the answer.
Thresholds live in ``policy.py`` so all the decision logic is in one place.

Embeddings use ``all-MiniLM-L6-v2`` (already a project dependency via GraphRAG)
— small and fast, loaded lazily so importing this module is free.
"""
from __future__ import annotations

import re
from typing import List, Optional

import numpy as np

from .state import Chunk, Profile, Signals

_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "at", "for", "and", "or", "is",
    "are", "was", "were", "who", "what", "when", "where", "how", "why", "did",
    "do", "does", "with", "that", "this", "by", "from", "as", "it", "eth",
}


def _norm(x: float) -> float:
    """Map a cosine similarity in [-1, 1] to [0, 1]."""
    return max(0.0, min(1.0, (x + 1.0) / 2.0))


class EvidenceAnalyzer:
    def __init__(self, embed_model: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self._embed_model = embed_model
        self._embedder = None

    def _embed(self, texts: List[str]) -> np.ndarray:
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer

            self._embedder = SentenceTransformer(self._embed_model)
        return self._embedder.encode(texts, normalize_embeddings=True)

    def analyze(
        self,
        query: str,
        chunks: List[Chunk],
        profile: Optional[Profile],
        signals: Optional[Signals] = None,
        top_k: int = 5,
    ) -> Signals:
        """Compute the pre-generation signals on the top-k chunks."""
        sig = signals or Signals()
        sig.ambiguity = int(bool(profile and profile.ambiguity_flag))

        top = chunks[:top_k]
        if not top:
            sig.sufficiency = 0.0
            sig.chunk_agreement = 0.0
            return sig

        texts = [c.short(800) for c in top]
        embs = self._embed([query] + texts)
        q_emb, c_embs = embs[0], embs[1:]

        # query <-> chunk relevance
        q_sims = c_embs @ q_emb
        q_chunk_relevance = _norm(float(np.mean(q_sims)))

        # pairwise chunk agreement
        if len(c_embs) > 1:
            sim_mat = c_embs @ c_embs.T
            iu = np.triu_indices(len(c_embs), k=1)
            chunk_agreement = _norm(float(np.mean(sim_mat[iu])))
        else:
            chunk_agreement = 1.0

        # query-entity coverage in the top chunks
        coverage = self._entity_coverage(query, profile, texts)

        sig.chunk_agreement = chunk_agreement
        sig.sufficiency = round(
            0.55 * q_chunk_relevance + 0.30 * coverage + 0.15 * chunk_agreement, 4
        )
        return sig

    @staticmethod
    def _entity_coverage(query: str, profile: Optional[Profile], texts: List[str]) -> float:
        if profile and profile.entities:
            terms = [t.lower() for t in profile.entities]
        else:
            terms = [
                w for w in re.findall(r"[a-zà-ÿ]{3,}", query.lower()) if w not in _STOP
            ]
        if not terms:
            return 0.5
        blob = " ".join(texts).lower()
        hits = sum(1 for t in terms if t in blob)
        return hits / len(terms)

    @staticmethod
    def aggregate_confidence(sig: Signals) -> float:
        """Single reported trust score (rubric category H)."""
        return round(
            0.4 * sig.sufficiency + 0.4 * sig.grounding + 0.2 * (1.0 - sig.contradiction), 4
        )
