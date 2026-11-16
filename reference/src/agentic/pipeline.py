"""AgenticRAG — the reliable & adaptive pipeline that wires the agents together.

It runs the PolicyController's state machine over one query, executing the
action the controller emits at each junction and recording every step in a
DecisionTrace. The bounded retry budget (``retries_left``) keeps recovery loops
finite. The same object answers a single query (``answer``) or the whole
benchmark (driven by ``scripts/run_agentic.py``).

Construction loads the Step 1 retrievers once (expensive) and reuses them.
"""
from __future__ import annotations

from typing import Optional

from baseline import config
from baseline.orchestration import BaselineSystem
from baseline.retrievers import load_bm25, load_dense, load_graphrag

from .generator import AnswerGenerator
from .llm import LLMClient, default_client
from .policy import PolicyController, QueryRewriter, Thresholds
from .profiler import QueryProfiler
from .retrieval import RetrievalCoordinator
from .signals import EvidenceAnalyzer
from .state import Action, DecisionTrace, RunState
from .verifier import Verifier

_CLARIFY_SYSTEM = """The user's question is under-specified for a retrieval system about ETH Zurich.
Ask ONE short clarifying question that would let you answer well. Return only the question."""


class AgenticRAG:
    def __init__(
        self,
        system: BaselineSystem,
        llm: Optional[LLMClient] = None,
        thresholds: Optional[Thresholds] = None,
        *,
        max_retries: int = 2,
        gen_k: int = 5,
        enable_recovery: bool = True,
        enable_clarify: bool = True,
        enable_abstain: bool = True,
    ) -> None:
        self.llm = llm or default_client()
        self.coord = RetrievalCoordinator(system)
        self.profiler = QueryProfiler(self.llm)
        self.analyzer = EvidenceAnalyzer()
        self.generator = AnswerGenerator(self.llm, k=gen_k)
        self.verifier = Verifier(self.llm, k=gen_k)
        self.rewriter = QueryRewriter(self.llm)
        self.policy = PolicyController(
            thresholds,
            self.llm,
            enable_recovery=enable_recovery,
            enable_clarify=enable_clarify,
            enable_abstain=enable_abstain,
        )
        self.max_retries = max_retries
        self.gen_k = gen_k

    # --------------------------------------------------- factory
    @classmethod
    def from_pretrained(cls, **kwargs) -> "AgenticRAG":
        """Load the Step 1 retrievers and build the system."""
        bm25 = load_bm25()
        dense = load_dense()
        graph = load_graphrag()
        system = BaselineSystem(bm25=bm25, dense=dense, graph=graph)
        return cls(system, **kwargs)

    # --------------------------------------------------- main entry
    def answer(self, qid: str, query: str, qa_item: Optional[dict] = None) -> DecisionTrace:
        trace = DecisionTrace(qid=str(qid), query=query)
        state = RunState(qid=str(qid), query=query, retries_left=self.max_retries, trace=trace)

        # 1. Profile
        state.profile = self.profiler.profile(query, qa_item)
        trace.profile = self.profiler_profile_dict(state)
        state.mode = self.policy.choose_initial_mode(state.profile)
        trace.log("profile", **trace.profile, initial_mode=state.mode)

        # 2. State-machine loop
        while True:
            # --- retrieve
            state.chunks = self.coord.retrieve(state.current_query, state.mode, top_k=8)
            trace.log(
                "retrieve",
                mode=state.mode,
                query=state.current_query,
                n_chunks=len(state.chunks),
                top_ids=[c.chunk_id for c in state.chunks[: self.gen_k]],
            )

            # --- analyze (pre-generation signals)
            self.analyzer.analyze(state.current_query, state.chunks, state.profile, state.signals)
            trace.log("analyze", signals=state.signals.as_dict())

            action, reason = self.policy.decide_after_evidence(state)
            trace.log("decide", action=action.value, reason=reason, retries_left=state.retries_left)

            if action == Action.CLARIFY:
                return self._finalize_clarify(state, trace)
            if action == Action.ABSTAIN:
                return self._finalize_abstain(state, trace, reason)
            if action == Action.SWITCH_MODE_AND_RETRIEVE:
                self._recover(state, trace)
                continue

            # --- generate
            gen = self.generator.generate(state.current_query, state.chunks)
            state.draft_answer = gen["answer"]
            state.citations = gen["citations"]
            trace.log(
                "generate",
                draft_answer=state.draft_answer,
                citations=state.citations,
                evidence_found=gen["evidence_found"],
            )

            action, reason = self.policy.decide_after_generate(state, gen["evidence_found"])
            trace.log("decide", action=action.value, reason=reason, retries_left=state.retries_left)
            if action == Action.ABSTAIN:
                return self._finalize_abstain(state, trace, reason)
            if action == Action.SWITCH_MODE_AND_RETRIEVE:
                self._recover(state, trace)
                continue

            # --- verify
            v = self.verifier.verify(state.current_query, state.draft_answer, state.chunks)
            state.verifier = v
            state.signals.grounding = v["grounding_score"]
            state.signals.contradiction = v["contradiction_score"]
            state.signals.confidence = self.analyzer.aggregate_confidence(state.signals)
            trace.log("verify", **v, signals=state.signals.as_dict())

            action, reason = self.policy.decide_after_verify(state)
            trace.log("decide", action=action.value, reason=reason, retries_left=state.retries_left)

            if action == Action.ANSWER:
                conflict = v["contradiction_score"] > self.policy.t.contradiction_high
                return self._finalize_answer(state, trace, conflict=conflict)
            if action == Action.SWITCH_MODE_AND_RETRIEVE:
                self._recover(state, trace)
                continue
            # ABSTAIN
            return self._finalize_abstain(state, trace, reason)

    # --------------------------------------------------- helpers
    @staticmethod
    def profiler_profile_dict(state: RunState) -> dict:
        p = state.profile
        return {
            "lang": p.lang,
            "query_type": p.query_type,
            "ambiguity_flag": p.ambiguity_flag,
            "ambiguity_reason": p.ambiguity_reason,
            "entities": p.entities,
        }

    def _recover(self, state: RunState, trace: DecisionTrace) -> None:
        """Adaptive recovery: rewrite the query and switch to a new mode."""
        state.tried_modes.append(state.mode)
        new_query = self.rewriter.rewrite(state.query)
        new_mode = self.coord.next_mode(
            state.profile.query_type if state.profile else "entity", state.tried_modes
        )
        state.retries_left -= 1
        trace.log(
            "recover",
            rewritten_query=new_query,
            old_mode=state.mode,
            new_mode=new_mode,
            retries_left=state.retries_left,
        )
        state.current_query = new_query
        state.mode = new_mode

    def _finalize_answer(self, state: RunState, trace: DecisionTrace, conflict: bool) -> DecisionTrace:
        trace.final = {
            "action": "answer",
            "answer": state.draft_answer,
            "citations": state.citations,
            "confidence": state.signals.confidence,
            "conflict_flag": conflict,
            "mode_used": state.mode,
            "signals": state.signals.as_dict(),
        }
        trace.log("final", **trace.final)
        return trace

    def _finalize_abstain(self, state: RunState, trace: DecisionTrace, reason: str) -> DecisionTrace:
        trace.final = {
            "action": "abstain",
            "answer": None,
            "abstain_reason": reason,
            "confidence": state.signals.confidence,
            "mode_used": state.mode,
            "signals": state.signals.as_dict(),
        }
        trace.log("final", **trace.final)
        return trace

    def _finalize_clarify(self, state: RunState, trace: DecisionTrace) -> DecisionTrace:
        question = self._clarification_question(state.query)
        trace.final = {
            "action": "clarify",
            "answer": None,
            "clarifying_question": question,
            "confidence": state.signals.confidence,
            "mode_used": state.mode,
            "signals": state.signals.as_dict(),
        }
        trace.log("final", **trace.final)
        return trace

    def _clarification_question(self, query: str) -> str:
        if not self.llm.available:
            return "Could you clarify what specifically you would like to know?"
        try:
            return self.llm.complete_text(
                system=_CLARIFY_SYSTEM,
                user=f"Question: {query}",
                model=config.AGENT_MODEL_UTILITY,
                max_tokens=120,
            ).splitlines()[0].strip()
        except Exception:  # noqa: BLE001
            return "Could you clarify what specifically you would like to know?"
