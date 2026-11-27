"""Turn one decision trace into calibration features.

Feature groups (used for the ablation; each group adds to the previous ones):

  G0  baseline      the reference system's own confidence score
  G1  signals       final sufficiency, chunk agreement, grounding, contradiction,
                    number of unsupported claims
  G2  process       how the system got there: retrieval rounds, recoveries, mode changes,
                    generator 'no evidence' rounds, sufficiency trajectory, ambiguity flag,
                    question language, latency
  G3  answer text   does the answer actually answer? hedge / non-answer phrases,
                    answer length, number of citations

Everything is read from the saved trace: no extra model or API calls.
"""
from __future__ import annotations

import re

# Phrases that signal the 'answer' is really a non-answer (Step 1, Q10/Q12/Q20).
_HEDGES = [
    r"do(?:es)? not (?:contain|mention|provide|give|specify|state|include|say|identify|describe|cover)",
    r"no (?:specific |explicit |direct )?(?:information|mention|data|details|evidence)",
    r"not (?:clearly |explicitly )?(?:stated|mentioned|specified|provided|available|covered)",
    r"(?:cannot|can't|unable to) (?:determine|confirm|find|identify|answer)",
    r"(?:only )?partially (?:covers?|answer)",
    r"the (?:provided |available )?(?:chunks|evidence|context|sources) (?:do not|don't|does not)",
    r"unclear",
    r"insufficient",
]
_HEDGE_RE = [re.compile(p, re.I) for p in _HEDGES]

GROUPS = {
    "G0": ["base_conf"],
    "G1": ["suff", "agree", "ground", "contra", "n_unsupported"],
    "G2": ["n_retrieve", "n_recover", "mode_changed", "n_no_evidence", "suff_first",
           "suff_gain", "ambiguous", "lang_de", "latency_s"],
    "G3": ["n_hedges", "has_hedge", "answer_len_log", "n_citations"],
}


def _steps(trace, name):
    return [s for s in trace.get("timeline", []) if s.get("step") == name]


def features(trace: dict) -> dict:
    fin = trace.get("final", {}) or {}
    sig = fin.get("signals") or {}
    analyses = [s.get("signals", {}) for s in _steps(trace, "analyze")]
    verifies = _steps(trace, "verify")
    gens = _steps(trace, "generate")
    rets = _steps(trace, "retrieve")
    prof = trace.get("profile", {}) or {}
    ans = fin.get("answer") or ""
    suff_series = [a.get("sufficiency", 0.0) or 0.0 for a in analyses] or [0.0]
    last_v = verifies[-1] if verifies else {}
    hedges = sum(len(r.findall(ans)) for r in _HEDGE_RE)
    t_ms = max([s.get("t_ms", 0) or 0 for s in trace.get("timeline", [])] + [0])
    import math

    return {
        "base_conf": float(fin.get("confidence") or 0.0),
        "suff": float(sig.get("sufficiency", suff_series[-1]) or 0.0),
        "agree": float(sig.get("chunk_agreement", 0.0) or 0.0),
        "ground": float(sig.get("grounding", last_v.get("grounding_score") or 0.0) or 0.0),
        "contra": float(sig.get("contradiction", last_v.get("contradiction_score") or 0.0) or 0.0),
        "n_unsupported": float(len(last_v.get("unsupported_claims") or [])),
        "n_retrieve": float(len(rets)),
        "n_recover": float(len(_steps(trace, "recover"))),
        "mode_changed": float(len({r.get("mode") for r in rets}) > 1),
        "n_no_evidence": float(sum(1 for g in gens if g.get("evidence_found") is False)),
        "suff_first": float(suff_series[0]),
        "suff_gain": float(suff_series[-1] - suff_series[0]),
        "ambiguous": float(bool(prof.get("ambiguity_flag"))),
        "lang_de": float(prof.get("lang") == "de"),
        "latency_s": float(t_ms) / 1000.0,
        "n_hedges": float(hedges),
        "has_hedge": float(hedges > 0),
        "answer_len_log": math.log1p(len(ans.split())),
        "n_citations": float(len(fin.get("citations") or [])),
    }


def columns(upto: str) -> list[str]:
    """All feature names of the groups up to and including `upto` (e.g. 'G2')."""
    out = []
    for g in ["G0", "G1", "G2", "G3"]:
        out += GROUPS[g]
        if g == upto:
            break
    return out
