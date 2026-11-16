"""PolicyController — the decision logic and adaptive orchestration.

This is what distinguishes the system from a fixed pipeline: it reads the
reliability signals and the verifier's verdict and decides what to do next,
logging a human-readable reason for every choice. It implements:

* (D) Clarification — ambiguous queries route to a clarifying question.
* (E) Abstention — low evidence or ungrounded drafts with no retries left
  route to an explicit abstention rather than an unreliable answer.
* (G) Adaptive recovery (the mandatory orchestration-changing mechanism) —
  on low sufficiency or an ungrounded draft, the controller changes behaviour:
  it rewrites the query and/or switches to a retrieval mode not yet tried,
  with the *initial* mode chosen per query from its type.

Thresholds are gathered here so all reliability decisions live in one place;
Step 4 calibrates them against the benchmark.

Separation of concerns (Step 2): the controller decides but never retrieves,
generates, or judges directly — it returns an Action for the pipeline to run.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from baseline import config

from .llm import LLMClient, default_client
from .retrieval import RetrievalCoordinator
from .state import Action, Profile, RunState


@dataclass
class Thresholds:
    sufficiency_low: float = 0.40
    grounding_min: float = 0.60
    contradiction_high: float = 0.50
    # A query flagged ambiguous only routes to clarification when retrieval did
    # NOT already yield strong, coherent evidence — a guard against clarifying a
    # question we could simply answer.
    clarify_sufficiency_max: float = 0.65


# Initial retrieval mode by query type (Step 2 §"choose_by_type").
_MODE_BY_TYPE = {
    "entity": "bm25",
    "list": "voting",
    "definition": "dense",
    "opinion": "confidence",
    "multihop": "graphrag",
}


class PolicyController:
    def __init__(
        self,
        thresholds: Optional[Thresholds] = None,
        llm: Optional[LLMClient] = None,
        *,
        enable_recovery: bool = True,
        enable_clarify: bool = True,
        enable_abstain: bool = True,
    ) -> None:
        self.t = thresholds or Thresholds()
        self.llm = llm or default_client()
        # Feature flags so Step 4 can ablate each mechanism.
        self.enable_recovery = enable_recovery
        self.enable_clarify = enable_clarify
        self.enable_abstain = enable_abstain

    # ----------------------------------------------------- mode selection
    def choose_initial_mode(self, profile: Optional[Profile]) -> str:
        qt = profile.query_type if profile else "entity"
        return _MODE_BY_TYPE.get(qt, "voting")

    # ----------------------------------------------------- decision points
    def decide_after_evidence(self, state: RunState) -> tuple:
        """Decide what to do once chunks + pre-generation signals are in."""
        sig = state.signals

        if (
            self.enable_clarify
            and sig.ambiguity == 1
            and sig.sufficiency < self.t.clarify_sufficiency_max
        ):
            reason = (
                "ambiguity flag set"
                + (f" ({state.profile.ambiguity_reason})" if state.profile and state.profile.ambiguity_reason else "")
                + f"; evidence not strong (sufficiency {sig.sufficiency:.2f} < "
                f"{self.t.clarify_sufficiency_max:.2f}) → clarify instead of answering"
            )
            return Action.CLARIFY, reason

        if sig.sufficiency < self.t.sufficiency_low:
            if self.enable_recovery and state.retries_left > 0:
                return (
                    Action.SWITCH_MODE_AND_RETRIEVE,
                    f"sufficiency {sig.sufficiency:.2f} < {self.t.sufficiency_low:.2f}; "
                    f"mode '{state.mode}' tried; recovering with a new mode + rewrite",
                )
            if self.enable_abstain:
                return (
                    Action.ABSTAIN,
                    f"sufficiency {sig.sufficiency:.2f} < {self.t.sufficiency_low:.2f} "
                    f"and no retries left → abstain",
                )
        return (
            Action.GENERATE,
            f"sufficiency {sig.sufficiency:.2f} ≥ {self.t.sufficiency_low:.2f} → generate",
        )

    def decide_after_generate(self, state: RunState, evidence_found: bool) -> tuple:
        """If the generator reports no evidence, recover or abstain; else verify."""
        if not evidence_found:
            if self.enable_recovery and state.retries_left > 0:
                return (
                    Action.SWITCH_MODE_AND_RETRIEVE,
                    "generator reports evidence does not contain the answer; recovering",
                )
            if self.enable_abstain:
                return Action.ABSTAIN, "generator found no supporting evidence → abstain"
        return Action.VERIFY, "draft produced → verify groundedness"

    def decide_after_verify(self, state: RunState) -> tuple:
        """Turn the verifier verdict into the final action."""
        v = state.verifier
        grounded = v.get("grounded", False)
        gscore = float(v.get("grounding_score", 0.0))
        contra = float(v.get("contradiction_score", 0.0))

        if grounded and gscore >= self.t.grounding_min:
            if contra > self.t.contradiction_high:
                return (
                    Action.ANSWER,
                    f"grounded (score {gscore:.2f}) but evidence conflicts "
                    f"(contradiction {contra:.2f}) → answer with conflict flag",
                )
            return Action.ANSWER, f"grounded (score {gscore:.2f}) → answer"

        # not grounded
        if self.enable_recovery and state.retries_left > 0:
            return (
                Action.SWITCH_MODE_AND_RETRIEVE,
                f"ungrounded (score {gscore:.2f} < {self.t.grounding_min:.2f}); "
                f"recovering with a new mode + rewrite",
            )
        if self.enable_abstain:
            return (
                Action.ABSTAIN,
                f"ungrounded (score {gscore:.2f} < {self.t.grounding_min:.2f}) "
                f"and no retries left → abstain",
            )
        return Action.ANSWER, "abstention disabled (ablation) → answer despite weak grounding"


# ------------------------------------------------------------- query rewrite
_REWRITE_SYSTEM = """You rewrite a search query to improve retrieval over an ETH Zurich corpus.

The previous query retrieved weak or insufficient evidence. Produce ONE improved
query that:
- expands acronyms and adds synonyms / alternative phrasings,
- keeps the same information need,
- if the query is German, also works in English (you may translate),
- is a single line, no explanation.

Return only the rewritten query text."""


class QueryRewriter:
    def __init__(self, llm: Optional[LLMClient] = None) -> None:
        self.llm = llm or default_client()

    def rewrite(self, query: str) -> str:
        if not self.llm.available:
            return query
        try:
            out = self.llm.complete_text(
                system=_REWRITE_SYSTEM,
                user=f"Query: {query}",
                model=config.AGENT_MODEL_UTILITY,
                max_tokens=120,
            )
            return out.splitlines()[0].strip() if out else query
        except Exception:  # noqa: BLE001
            return query
