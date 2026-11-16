"""QueryProfiler — query understanding (language, type, ambiguity, entities).

The profile drives two decisions downstream: the initial retrieval mode
(``choose_by_type`` in the policy) and whether the query should trigger a
clarification branch (``ambiguity_flag``).

Primary path: one structured Claude call (fast utility model). Fallback (no
API key): ``langdetect`` for language + the Step 1 ``is_ambiguous`` heuristic,
with a keyword query-type guess. The fallback keeps the pipeline runnable for
smoke tests and makes the LLM contribution measurable in the ablation.
"""
from __future__ import annotations

import re
from typing import Optional

from baseline import config
from baseline.failure_analysis import is_ambiguous

from .llm import LLMClient, LLMUnavailableError, default_client
from .state import Profile

_QUERY_TYPES = ["entity", "list", "definition", "opinion", "multihop"]

_SCHEMA = {
    "type": "object",
    "properties": {
        "lang": {"type": "string", "enum": ["en", "de"]},
        "query_type": {"type": "string", "enum": _QUERY_TYPES},
        "ambiguity_flag": {"type": "boolean"},
        "ambiguity_reason": {"type": "string"},
        "entities": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["lang", "query_type", "ambiguity_flag", "ambiguity_reason", "entities"],
    "additionalProperties": False,
}

_SYSTEM = """You profile a single search query for a retrieval system over an ETH Zurich corpus.

Return a JSON object describing the query:
- lang: "en" or "de" (the language the query is written in).
- query_type: one of entity, list, definition, opinion, multihop.
    entity     = asks for one specific named fact (who/when/where, a single answer).
    list       = asks for a set/enumeration ("who are the people who...", "what projects...").
    definition = asks what something is ("what is X?").
    opinion    = asks for a judgement or persuasion ("why should I...", "why should X get...").
    multihop   = needs combining facts across entities/time ("who did X in year Y, and what did they find?").
- ambiguity_flag: set true ONLY when the query itself has multiple genuinely
    different valid interpretations, or is so open-ended/subjective that no single
    answer could be correct, so a clarifying question is essential. Be conservative
    — most queries are NOT ambiguous.
    Ambiguous: "who are famous ETH alumni?" (no criterion for 'famous'; unbounded set),
      "why should I study at ETH?" (subjective/open-ended), "why should ETH get more funding?".
    NOT ambiguous: any specific factual question, even if it may not be answerable
      from this corpus. "when did the insight get to mars?" is a precise factual
      question → NOT ambiguous. Do NOT flag ambiguity because the answer might be
      missing from the corpus, off-topic for ETH, or could be phrased more narrowly —
      that is a retrieval concern, not query ambiguity.
- ambiguity_reason: one short sentence; empty string if not ambiguous.
- entities: key named entities or topic keywords in the query (lowercased, 0-5 items).

Be decisive and concise."""


# Lightweight query-type heuristic for the no-LLM fallback.
def _heuristic_type(q: str) -> str:
    ql = q.lower()
    if re.search(r"\b(who are|which|list|what (are|projects|research))\b", ql):
        return "list"
    if re.search(r"\bwhat is\b|\bwhat are .* called\b", ql):
        return "definition"
    if re.search(r"\bwhy\b|\bshould\b", ql):
        return "opinion"
    if " and " in ql and re.search(r"\bwho\b|\bwhat\b", ql):
        return "multihop"
    return "entity"


class QueryProfiler:
    def __init__(self, llm: Optional[LLMClient] = None) -> None:
        self.llm = llm or default_client()

    def profile(self, query: str, qa_item: Optional[dict] = None) -> Profile:
        if self.llm.available:
            try:
                return self._profile_llm(query)
            except (LLMUnavailableError, Exception):  # noqa: BLE001 - fall back gracefully
                pass
        return self._profile_heuristic(query, qa_item)

    def _profile_llm(self, query: str) -> Profile:
        data = self.llm.complete_json(
            system=_SYSTEM,
            user=f"Query: {query}",
            schema=_SCHEMA,
            model=config.AGENT_MODEL_UTILITY,
            max_tokens=400,
        )
        return Profile(
            lang=data.get("lang", "en"),
            query_type=data.get("query_type", "entity"),
            ambiguity_flag=bool(data.get("ambiguity_flag", False)),
            ambiguity_reason=(data.get("ambiguity_reason") or None),
            entities=[e for e in data.get("entities", []) if isinstance(e, str)][:5],
        )

    def _profile_heuristic(self, query: str, qa_item: Optional[dict]) -> Profile:
        try:
            from langdetect import detect

            lang = detect(query)
            lang = lang if lang in ("en", "de") else "en"
        except Exception:  # noqa: BLE001
            lang = "en"
        ambig = is_ambiguous(qa_item) if qa_item else False
        return Profile(
            lang=lang,
            query_type=_heuristic_type(query),
            ambiguity_flag=ambig,
            ambiguity_reason="benchmark notes flag this as ambiguous" if ambig else None,
            entities=[w for w in re.findall(r"[a-z]{4,}", query.lower())][:5],
        )
