# Step 3 — Reliability Mechanisms & Adaptive Recovery: Progress

**Status:** Implementation complete, smoke test passed end-to-end on 2 benchmark queries.
**Scope of this doc:** what has been built for the Step 3 deliverable, how it maps to the rubric, how to run it, and what remains.

---

## 1. What Step 3 requires

The assignment (25 points) asks for **at least four substantial reliability mechanisms**, with **at least one that adapts the orchestration** (changes behaviour dynamically when a problem is detected). The categories are: (A) evidence sufficiency, (B) groundedness verification, (C) contradiction detection, (D) clarification, (E) abstention, (F) self-reflection/critique, (G) recovery, (H) trust/confidence scoring.

This implementation delivers **all four required mechanisms plus three bonus ones**, on top of the Step 1 retrieval baseline, using **Claude (Anthropic SDK)** for the LLM-backed agents.

---

## 2. Mechanisms implemented → rubric mapping

| Rubric category | Where | What it does |
|---|---|---|
| **(A) Evidence Sufficiency** ✅ required | `signals.py` → `EvidenceAnalyzer` | Local (no-LLM) `sufficiency` signal: blend of query↔chunk semantic relevance, query-entity coverage, and chunk agreement (MiniLM embeddings). Gate before generation. |
| **(B) Groundedness Verification** ✅ required | `verifier.py` → `Verifier` | Claude judge: is every claim in the draft supported by the chunks? Returns `grounded`, `grounding_score`, `unsupported_claims`. |
| **(E) Abstention** ✅ required | `policy.py` → `PolicyController` | Explicit ABSTAIN branch tied to signals: low sufficiency with no retries, or ungrounded draft with no retries. |
| **(G) Adaptive Recovery** ✅ required + **adaptation requirement** | `policy.py` + `pipeline.py` | The orchestration-changing mechanism: on low sufficiency or an ungrounded draft, the controller **rewrites the query and switches to a retrieval mode not yet tried**. Initial mode is chosen *per query* from its type. Behaviour depends on detected signals and previous outcomes. |
| **(C) Contradiction Detection** ⭐ bonus | `verifier.py` | `contradiction_score` (do the chunks disagree?); a high score sets a `conflict_flag` on the answer. |
| **(D) Clarification** ⭐ bonus | `profiler.py` + `policy.py` | Ambiguous queries (flagged by the profiler) route to a generated clarifying question instead of an answer. |
| **(F) Self-Reflection / Critique** ⭐ bonus | `verifier.py` | The verifier reviews the draft and the policy acts on its verdict (revise via recovery, abstain, or answer). |
| **(H) Trust / Confidence Scoring** ⭐ bonus | `signals.py` | `confidence = 0.4·sufficiency + 0.4·grounding + 0.2·(1−contradiction)`, reported with every answer. |

**Adaptation requirement (must-have):** satisfied by (G) — the controller routes differently per query type, chooses a different recovery action based on the detected failure, and avoids re-trying modes that already failed.

---

## 3. Architecture as built

Six specialized agents + a PolicyController over a shared `RunState` blackboard, exactly per `docs/step2_design.md`. Answer **production** (`AnswerGenerator`), answer **checking** (`Verifier`), and **decision control** (`PolicyController`) are separated — the verifier may judge but not rewrite; the controller decides but does not retrieve/generate/judge directly.

```
src/agentic/
├── llm.py         # Anthropic SDK wrapper: structured JSON, prompt caching, token+cost tally
├── state.py       # RunState (blackboard) + DecisionTrace (interpretability artifact)
├── profiler.py    # QueryProfiler: lang / type / ambiguity / entities (LLM + heuristic fallback)
├── signals.py     # EvidenceAnalyzer: sufficiency, chunk_agreement, confidence aggregation
├── retrieval.py   # RetrievalCoordinator: wraps Step 1 BaselineSystem; mode switch + rewrite
├── generator.py   # AnswerGenerator: Claude, grounded, cited, refuses when unsupported
├── verifier.py    # Verifier/Critic: Claude judge (grounded? contradiction? unsupported claims?)
├── policy.py      # PolicyController state machine + QueryRewriter (recovery lever)
└── pipeline.py    # AgenticRAG: runs the loop, emits a DecisionTrace per query
```

### Control flow (the state machine)

```
profile → choose initial mode (by query type)
  └─ loop (bounded by retry budget = 2):
       retrieve(current_query, mode)
       analyze → sufficiency, chunk_agreement, ambiguity
       DECIDE:
         ambiguity            → CLARIFY  (final)
         sufficiency low, retries left  → RECOVER (rewrite + switch mode), loop
         sufficiency low, no retries    → ABSTAIN (final)
         else                 → GENERATE
       generate (grounded, cited)
       DECIDE:
         no evidence found, retries left → RECOVER, loop
         no evidence found, no retries   → ABSTAIN (final)
         else                 → VERIFY
       verify → grounding_score, contradiction_score; compute confidence
       DECIDE:
         grounded             → ANSWER (final; conflict_flag if contradiction high)
         ungrounded, retries left → RECOVER, loop
         ungrounded, no retries   → ABSTAIN (final)
```

### Reliability signals & initial thresholds (calibrated in Step 4)

| Signal | Source | Threshold |
|---|---|---|
| `sufficiency` ∈ [0,1] | embeddings (local) | `< 0.40` → low |
| `chunk_agreement` ∈ [0,1] | embeddings (local) | reported |
| `grounding` ∈ [0,1] | Claude verifier | `< 0.60` → ungrounded |
| `contradiction` ∈ [0,1] | Claude verifier | `> 0.50` → conflict |
| `ambiguity` ∈ {0,1} | profiler | `== 1` → clarify |
| `confidence` ∈ [0,1] | aggregate | reported |

### Initial retrieval mode by query type (`choose_by_type`)

`entity → bm25` · `list → voting` · `definition → dense` · `opinion → confidence` · `multihop → graphrag`. Recovery then switches to a complementary mode not yet tried.

---

## 4. LLM integration (Claude)

- All LLM calls go through `src/agentic/llm.py` using the official **Anthropic SDK**.
- Models are configurable via `.env`: **generation/verification → `claude-opus-4-7`**, **profiling/rewriting/clarification → `claude-haiku-4-5`**.
- Structured outputs via `output_config.format` (JSON schema) for the profiler, generator, and verifier.
- **Prompt caching** on the (stable) system prompts; **token + approximate USD cost** accumulated per run (rubric asks for a cost indicator).
- Graceful degradation: profiler falls back to `langdetect` + the Step 1 `is_ambiguous` heuristic if no key; the pipeline still imports and the decision logic is testable without any API calls.

---

## 5. Interpretability — DecisionTrace

Every query produces `results/agentic/traces/<qid>.json` with a `timeline` of every step (retrieve / analyze / decide / generate / verify / recover / final), each decision carrying a **human-readable reason** and the signal values that drove it. This is the artifact Step 4 uses for the qualitative analysis (clarification, abstention, recovery, conflict cases) and the ablation.

---

## 6. How to run

```bash
# 1. Key (done): ANTHROPIC_API_KEY=... in .env  (gitignored)

# 2. Smoke test (first run loads/downloads retriever + embedder models)
python -m src.scripts.run_agentic --limit 2

# 3. Full benchmark
python -m src.scripts.run_agentic

# 4. Ablations for Step 4 (disable one mechanism each)
python -m src.scripts.run_agentic --ablation no_recovery
python -m src.scripts.run_agentic --ablation no_abstain
python -m src.scripts.run_agentic --ablation no_clarify
```

Outputs under `results/agentic/` (or `results/agentic/<ablation>/`):
`traces/<qid>.json`, `answers.json`, `run_summary.json` (action counts, latency, LLM cost).

---

## 7. Validation status

- ✅ Package imports cleanly with no API key (lazy SDK construction).
- ✅ PolicyController decision logic unit-tested — all 8 state-machine branches (clarify / recover / abstain / generate / answer / conflict / ungrounded paths / ablation) pass.
- ✅ Live Anthropic API call verified end-to-end (key loads, SDK authenticates).
- ✅ End-to-end smoke run (`--limit 2`) passed — both mechanisms fired on real queries.

### Smoke-test results (2 queries, `full` config)

| Q | Query | Outcome | Conf. | Notes |
|---|---|---|---|---|
| Q1 | who was president of eth in 2003? | **abstain** | 0.0 | Answer ("olaf kübler") is **not in the corpus** (Step 1: `no_qrels`). System tried bm25 → voting → graphrag with query rewrites, never found support, and abstained instead of hallucinating. Ideal reliability behaviour. |
| Q2 | who were the rectors of eth between 2017 and 2022? | **answer** | 0.83 | Recovered voting → graphrag → confidence, produced a grounded partial answer (Springman + four Vice-Rectors with terms), verifier confirmed `grounding_score=1.0`, honestly noted the list is incomplete. Step 1 had this as `ranking_failure` (gold in top-100 not top-5). |

LLM usage for the 2 queries: 13 calls, ~14k input / 1.2k output tokens, **≈ $0.088** (7 Opus + 6 Haiku). The DecisionTraces (`results/agentic/traces/{1,2}.json`) show every retrieve/analyze/decide/recover step with reasons.

### Findings to act on (Step 4 calibration)

1. **One-time GraphRAG cold-cache cost.** The first retrieval that uses the graph index embeds all candidate chunks (~270 s on CPU), then caches them — Q1 took 308 s but Q2 only 33 s. Across the full benchmark this is paid once. Worth a sentence in the report's efficiency discussion; could be pre-warmed.
2. **Generator's `evidence_found` is conservative.** For list questions with no complete answer (e.g. Q2 has 53 gold chunks), the generator returned `evidence_found=false` on partial evidence, triggering extra recovery loops before finally answering. The system still lands correctly, but burns passes. Tuning the generator prompt to set `evidence_found=true` on *partial* support would cut latency/cost — a clean calibration result to report.

---

## 8. Remaining work

**Finish Step 3**
- [ ] Complete smoke run; inspect a real DecisionTrace for correctness.
- [ ] Run the full 25-question benchmark; sanity-check action distribution (answers vs abstain vs clarify).
- [ ] Tune thresholds if the first run is obviously mis-calibrated (full calibration is Step 4).

**Step 4 (Evaluation) — enabled by what's built**
- [ ] Retrieval/answer metrics vs the Step 1 baseline.
- [ ] Reliability metrics: grounded-answer rate, correct/false abstention rate, recovery success rate, confidence↔correctness alignment.
- [ ] **Benchmark extension**: ambiguous / insufficient-evidence / conflicting-evidence / adversarial cases (the mechanisms are ready to be exercised).
- [ ] Ablations (flags already implemented) + at least one ablation study.
- [ ] Qualitative examples pulled from the traces.

**Housekeeping**
- [ ] Tool-usage disclosure for the report (Claude Code used for implementation).
- [ ] Rotate the API key after the project.
