"""Step 3 — reliable & adaptive agentic RAG system.

A reliability-aware multi-agent pipeline built on the Step 1 baseline retrievers.
See ``docs/step2_design.md`` for the architecture and ``pipeline.AgenticRAG`` for
the entry point.
"""
from .pipeline import AgenticRAG
from .policy import PolicyController, Thresholds
from .state import Action, DecisionTrace, RunState

__all__ = [
    "AgenticRAG",
    "PolicyController",
    "Thresholds",
    "Action",
    "DecisionTrace",
    "RunState",
]
