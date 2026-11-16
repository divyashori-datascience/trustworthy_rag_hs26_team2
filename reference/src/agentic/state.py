"""Shared state and the DecisionTrace interpretability artifact.

``RunState`` is the blackboard the agents read and write as a query flows
through the pipeline. ``DecisionTrace`` is the per-query JSON record required by
the Step 2 "make orchestration interpretable" deliverable: every retrieval,
analysis, decision (with a human-readable reason), generation, and verification
step is appended to ``timeline`` as it happens. Step 4 reads these traces for
the qualitative analysis (clarification / abstention / recovery / ablation).
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Action(str, Enum):
    """Actions the PolicyController can emit."""

    RETRIEVE = "retrieve"
    REWRITE_AND_RETRIEVE = "rewrite_and_retrieve"
    SWITCH_MODE_AND_RETRIEVE = "switch_mode_and_retrieve"
    GENERATE = "generate"
    VERIFY = "verify"
    CLARIFY = "clarify"
    ABSTAIN = "abstain"
    ANSWER = "answer"


@dataclass
class Profile:
    lang: str = "en"
    query_type: str = "entity"  # entity | list | definition | opinion | multihop
    ambiguity_flag: bool = False
    ambiguity_reason: Optional[str] = None
    entities: List[str] = field(default_factory=list)


@dataclass
class Chunk:
    chunk_id: str
    text: str
    score: float
    source: str = ""

    def short(self, n: int = 600) -> str:
        t = self.text.replace("\n", " ").strip()
        return t[:n]


@dataclass
class Signals:
    """The reliability-signal vector computed by EvidenceAnalyzer."""

    sufficiency: float = 0.0
    chunk_agreement: float = 0.0
    grounding: float = 0.0
    contradiction: float = 0.0
    ambiguity: int = 0
    confidence: float = 0.0

    def as_dict(self) -> dict:
        return {k: round(v, 4) if isinstance(v, float) else v for k, v in asdict(self).items()}


@dataclass
class DecisionTrace:
    """The interpretable record saved per query (one JSON file)."""

    qid: str
    query: str
    profile: Dict[str, Any] = field(default_factory=dict)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    final: Dict[str, Any] = field(default_factory=dict)
    _t0: float = field(default_factory=time.perf_counter, repr=False)

    def _ms(self) -> int:
        return int((time.perf_counter() - self._t0) * 1000)

    def log(self, step: str, **payload: Any) -> None:
        entry = {"step": step, "t_ms": self._ms()}
        entry.update(payload)
        self.timeline.append(entry)

    def to_dict(self) -> dict:
        return {
            "qid": self.qid,
            "query": self.query,
            "profile": self.profile,
            "timeline": self.timeline,
            "final": self.final,
        }


@dataclass
class RunState:
    """Mutable blackboard for one query's journey through the pipeline."""

    qid: str
    query: str
    profile: Optional[Profile] = None
    current_query: str = ""          # may be rewritten during recovery
    mode: str = ""                   # current retrieval mode
    tried_modes: List[str] = field(default_factory=list)
    chunks: List[Chunk] = field(default_factory=list)
    signals: Signals = field(default_factory=Signals)
    draft_answer: Optional[str] = None
    citations: List[str] = field(default_factory=list)
    verifier: Dict[str, Any] = field(default_factory=dict)
    retries_left: int = 2
    trace: Optional[DecisionTrace] = None

    def __post_init__(self) -> None:
        if not self.current_query:
            self.current_query = self.query
