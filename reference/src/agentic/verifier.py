"""Verifier / Critic — Claude judges the draft against the evidence.

This single agent implements three rubric mechanisms at once:
* (B) Groundedness / support verification — is every claim supported by a chunk?
* (C) Contradiction detection — do the chunks disagree with each other?
* (F) Self-reflection / critique — it reviews the draft and recommends an action.

It returns structured fields the PolicyController turns into decisions:
``grounded`` + ``grounding_score`` (B), ``contradiction_score`` (C),
``unsupported_claims`` (what to fix), and a free-text ``reason`` for the trace.

Separation of concerns (Step 2 requirement): the verifier may judge but may not
rewrite the answer — only the PolicyController decides what happens next.
"""
from __future__ import annotations

from typing import List, Optional

from baseline import config

from .llm import LLMClient, default_client
from .state import Chunk

_SCHEMA = {
    "type": "object",
    "properties": {
        "grounded": {"type": "boolean"},
        "grounding_score": {"type": "number"},
        "contradiction_score": {"type": "number"},
        "unsupported_claims": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
    "required": [
        "grounded",
        "grounding_score",
        "contradiction_score",
        "unsupported_claims",
        "reason",
    ],
    "additionalProperties": False,
}

_SYSTEM = """You are a strict verifier for a retrieval-augmented QA system about ETH Zurich.

You are given a question, a draft answer, and the evidence chunks the answer was
based on. Judge ONLY whether the draft is supported by the evidence — do not use
outside knowledge and do not rewrite the answer.

Return JSON:
- grounded: true only if every factual claim in the draft is supported by the chunks.
- grounding_score: 0.0-1.0, the fraction of the draft's claims that are supported.
- contradiction_score: 0.0-1.0, how much the evidence chunks contradict EACH OTHER
    on the point being asked (0 = consistent, 1 = direct conflict).
- unsupported_claims: list any claims in the draft not backed by the chunks (empty if none).
- reason: one or two sentences explaining the judgement.

If the draft itself states the evidence does not contain the answer, treat it as
grounded (it makes no unsupported claims)."""


def _format_chunks(chunks: List[Chunk], k: int) -> str:
    return "\n\n".join(f"[{c.chunk_id}] {c.short(700)}" for c in chunks[:k])


class Verifier:
    def __init__(self, llm: Optional[LLMClient] = None, k: int = 5) -> None:
        self.llm = llm or default_client()
        self.k = k

    def verify(self, query: str, draft_answer: str, chunks: List[Chunk]) -> dict:
        evidence = _format_chunks(chunks, self.k)
        user = (
            f"Question: {query}\n\n"
            f"Draft answer:\n{draft_answer}\n\n"
            f"Evidence chunks:\n{evidence}"
        )
        data = self.llm.complete_json(
            system=_SYSTEM,
            user=user,
            schema=_SCHEMA,
            model=config.AGENT_MODEL_VERIFIER,
            max_tokens=700,
        )
        return {
            "grounded": bool(data.get("grounded", False)),
            "grounding_score": float(data.get("grounding_score", 0.0)),
            "contradiction_score": float(data.get("contradiction_score", 0.0)),
            "unsupported_claims": [
                c for c in data.get("unsupported_claims", []) if isinstance(c, str)
            ],
            "reason": data.get("reason", ""),
        }
