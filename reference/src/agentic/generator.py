"""AnswerGenerator — Claude drafts a grounded, cited answer from the chunks.

The prompt forces three behaviours that the verifier later checks:
* answer only from the provided chunks (no outside knowledge),
* cite the chunk ids used, and
* say so explicitly when the chunks do not contain the answer (rather than
  hallucinating) — this gives the policy a clean signal to abstain on.
"""
from __future__ import annotations

from typing import List, Optional

from baseline import config

from .llm import LLMClient, default_client
from .state import Chunk

_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}},
        "evidence_found": {
            "type": "boolean",
            "description": (
                "true if the chunks let you answer the question even partially; "
                "false only if the chunks contain essentially nothing relevant."
            ),
        },
    },
    "required": ["answer", "citations", "evidence_found"],
    "additionalProperties": False,
}

_SYSTEM = """You answer questions about ETH Zurich using ONLY the evidence chunks provided.

Rules:
- Use only facts stated in the chunks. Do NOT use outside knowledge.
- evidence_found: set true if the chunks let you answer the question EVEN PARTIALLY
  — a partial but supported answer still counts. Set it false ONLY when the chunks
  contain essentially nothing relevant to the question. When you give a partial
  answer, state plainly which parts of the question the evidence does not cover.
  Never guess beyond the chunks.
- Cite the chunk ids you actually used in "citations".
- Keep the answer concise and directly responsive to the question.
- Answer in the same language as the question."""


def _format_chunks(chunks: List[Chunk], k: int) -> str:
    lines = []
    for c in chunks[:k]:
        lines.append(f"[{c.chunk_id}] {c.short(700)}")
    return "\n\n".join(lines)


class AnswerGenerator:
    def __init__(self, llm: Optional[LLMClient] = None, k: int = 5) -> None:
        self.llm = llm or default_client()
        self.k = k

    def generate(self, query: str, chunks: List[Chunk]) -> dict:
        evidence = _format_chunks(chunks, self.k)
        user = f"Question: {query}\n\nEvidence chunks:\n{evidence}"
        data = self.llm.complete_json(
            system=_SYSTEM,
            user=user,
            schema=_SCHEMA,
            model=config.AGENT_MODEL_GENERATION,
            max_tokens=900,
        )
        return {
            "answer": data.get("answer", "").strip(),
            "citations": [c for c in data.get("citations", []) if isinstance(c, str)],
            "evidence_found": bool(data.get("evidence_found", True)),
        }
