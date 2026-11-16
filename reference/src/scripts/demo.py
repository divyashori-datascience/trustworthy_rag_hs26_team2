"""System demonstration — replays three pre-computed DecisionTraces.

This script requires NO API keys and NO retriever artifacts.
It reads from the committed results in results/agentic/ and prints a
human-readable walk-through of three representative queries:

  1. A grounded answer   (Q4  — InSight lander on Mars)
  2. An abstention       (Q1  — ETH president in 2003, out-of-corpus)
  3. A clarification     (R2  — "How many students are enrolled?", ambiguous)

Usage (from repo root):
    python -m src.scripts.demo
"""
from __future__ import annotations

import io
import json
import pathlib
import sys
import textwrap

# Force UTF-8 output on Windows so special characters in trace content don't crash
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_REPO = pathlib.Path(__file__).resolve().parents[2]

# Paths to the three pre-computed trace files already in the repo
DEMO_CASES = [
    {
        "trace": _REPO / "results" / "agentic" / "traces" / "4.json",
        "expected": "answer",
        "note": "Clear factoid with corpus evidence -> grounded answer, no recovery needed",
    },
    {
        "trace": _REPO / "results" / "agentic" / "traces" / "1.json",
        "expected": "abstain",
        "note": "Out-of-corpus question -> three recovery attempts across all modes -> abstain",
    },
    {
        "trace": _REPO / "results" / "agentic" / "reliability" / "traces" / "R2.json",
        "expected": "clarify",
        "note": "Genuinely ambiguous query (which year / programme?) -> clarification",
    },
]

# ── ANSI colours (auto-disabled when not a TTY) ──────────────────────────────
_TTY    = sys.stdout.isatty()
_GREEN  = "\033[32m" if _TTY else ""
_YELLOW = "\033[33m" if _TTY else ""
_RED    = "\033[31m" if _TTY else ""
_BOLD   = "\033[1m"  if _TTY else ""
_RESET  = "\033[0m"  if _TTY else ""
_HR1    = "=" * 70
_HR2    = "-" * 70

ACTION_COLOUR = {"answer": _GREEN, "abstain": _RED, "clarify": _YELLOW}

def _c(action: str, text: str) -> str:
    return f"{ACTION_COLOUR.get(action, '')}{text}{_RESET}"

def _wrap(text: str, indent: int = 4) -> str:
    pad = " " * indent
    return textwrap.fill(text, width=80, initial_indent=pad, subsequent_indent=pad)


# ── Trace printer ─────────────────────────────────────────────────────────────

def _print_timeline(timeline: list) -> None:
    print(f"\n  {_BOLD}Step-by-step DecisionTrace:{_RESET}")
    for step in timeline:
        s   = step["step"]
        t   = step.get("t_ms", 0)
        pad = f"    [{t:>6} ms]"

        if s == "profile":
            print(f"{pad} PROFILE   lang={step['lang']}"
                  f"  type={step['query_type']}"
                  f"  ambiguous={step['ambiguity_flag']}"
                  f"  -> initial mode: {step['initial_mode']}")

        elif s == "retrieve":
            print(f"{pad} RETRIEVE  mode={step['mode']:<12}"
                  f"  chunks={step['n_chunks']}")

        elif s == "analyze":
            sig = step["signals"]
            print(f"{pad} ANALYZE   sufficiency={sig['sufficiency']:.2f}"
                  f"  agreement={sig['chunk_agreement']:.2f}"
                  f"  ambiguity={sig['ambiguity']}")

        elif s == "decide":
            act = step["action"]
            print(f"{pad} DECIDE    -> {_c(act, act.upper())}"
                  f"   retries_left={step.get('retries_left', '?')}")
            print(f"               reason: {step['reason']}")

        elif s == "recover":
            print(f"{pad} RECOVER   {step['old_mode']} -> {step['new_mode']}")
            rw = step.get("rewritten_query", "")[:72]
            print(f"               rewrite: \"{rw}\"")

        elif s == "generate":
            draft = step.get("draft_answer", "")[:110].replace("\n", " ")
            print(f"{pad} GENERATE  evidence_found={step['evidence_found']}")
            print(f"               draft: \"{draft}...\"")

        elif s == "verify":
            print(f"{pad} VERIFY    grounded={step['grounded']}"
                  f"  score={step['grounding_score']:.2f}"
                  f"  unsupported={len(step.get('unsupported_claims', []))}")

        elif s == "final":
            pass   # printed separately


def _print_case(case: dict) -> None:
    trace_path: pathlib.Path = case["trace"]
    if not trace_path.exists():
        print(f"  [SKIP] trace file not found: {trace_path}")
        return

    data   = json.loads(trace_path.read_text(encoding="utf-8"))
    final  = data.get("final", {})
    action = final.get("action", "?")
    qid    = data.get("qid", "?")
    query  = data.get("query", "?")
    conf   = final.get("confidence", 0.0)

    print()
    print(_HR1)
    print(f"{_BOLD}Query [{qid}]:{_RESET}  {query}")
    print(f"Note:    {case['note']}")
    print(_HR2)

    _print_timeline(data.get("timeline", []))

    print()
    print(f"  {_BOLD}Outcome:{_RESET}  {_c(action, action.upper())}"
          f"   confidence={conf:.3f}")

    if action == "answer":
        answer    = final.get("answer", "")
        citations = final.get("citations", [])
        print(f"\n  {_BOLD}Answer:{_RESET}")
        print(_wrap(answer))
        print(f"\n  Citations ({len(citations)}): {citations[:4]}"
              f"{'...' if len(citations) > 4 else ''}")

    elif action == "abstain":
        reason = final.get("abstain_reason", "")
        print(f"\n  {_BOLD}Abstain reason:{_RESET}  {reason}")

    elif action == "clarify":
        cq = final.get("clarifying_question", "")
        print(f"\n  {_BOLD}Clarifying question:{_RESET}")
        print(_wrap(cq))

    # show signal summary
    signals = final.get("signals", {})
    if signals:
        print(f"\n  Signals: sufficiency={signals.get('sufficiency', 0):.2f}"
              f"  grounding={signals.get('grounding', 0):.2f}"
              f"  contradiction={signals.get('contradiction', 0):.2f}"
              f"  ambiguity={signals.get('ambiguity', 0)}")

    print(_HR1)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    print(_HR1)
    print(f"{_BOLD}Reliable & Adaptive Agentic RAG — System Demonstration{_RESET}")
    print("Replaying 3 pre-computed DecisionTraces (no API key or retrievers needed)")
    print(f"Full traces: results/agentic/traces/   |   Benchmark: 25 questions")
    print(_HR1)

    for case in DEMO_CASES:
        _print_case(case)

    print()
    print("Demonstration complete.")
    print()
    print("These traces were produced by running:")
    print("  python -m src.scripts.run_agentic      # full 25-question benchmark")
    print()
    print("To run the live pipeline yourself (requires ANTHROPIC_API_KEY +")
    print("retriever artifacts from Baseline/storage/):")
    print("  python -m src.scripts.run_agentic --limit 3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
