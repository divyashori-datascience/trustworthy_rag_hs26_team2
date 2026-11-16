# Step 2 — Reliability-Aware Agentic RAG: System Design

**Status:** Draft v0.1
**Scope:** Architecture, agents, reliability signals, decision policy, and justification for the Step 2 deliverable. Implementation follows in Step 3.

---

## 0. Context and design decision

The Step 1 baseline is **retrieval-only**: it runs BM25, Dense, and GraphRAG retrievers under three fixed orchestration strategies (waterfall, voting, confidence) and reports retrieval metrics. Half of the failure modes named in the assignment rubric — *synthesis*, *grounding*, *overconfidence*, *contradiction* — are unobservable in this configuration because there is no answer-generation layer.

Step 2 therefore introduces:

1. An **answer-generation agent** (LLM call, OpenAI `gpt-4o-mini` via the existing `openai` dependency) so grounding and synthesis become observable.
2. A **PolicyController** that reasons about reliability signals and chooses the next action, rather than running a fixed orchestration end-to-end.
3. A **DecisionTrace** artifact for every query, satisfying the "make orchestration interpretable" requirement.

**Key design decision (locked in):** the three baseline orchestration strategies (waterfall / voting / confidence) are **kept as named retrieval modes** that the PolicyController selects between per query. They are not replaced. This reuses validated code and gives us a concrete adaptive-routing mechanism for Step 3 grounded in data we already have (the per-query outcome table in `results/baseline/failure_report.md` shows which strategy won each query — direct training signal for routing).

---

## 1. Architecture

The system is composed of six specialized agents plus a shared blackboard (the `RunState`) that they read and write. The architecture **separates answer production from answer checking from decision control**, as required by the rubric.

```
                                   ┌──────────────────────┐
                                   │   PolicyController   │ ◄── reads signals,
                                   │  (orchestration /    │     emits actions,
                                   │   decision policy)   │     logs reasons
                                   └──────────┬───────────┘
                                              │ action
        ┌─────────────────────────────────────┼─────────────────────────────────────┐
        ▼                                     ▼                                     ▼
┌──────────────────┐              ┌──────────────────────┐              ┌────────────────────┐
│  QueryProfiler   │   query →    │ RetrievalCoordinator │   chunks →   │  EvidenceAnalyzer  │
│  (lang, type,    │              │  (BM25/Dense/Graph,  │              │  (sufficiency,     │
│   ambiguity)     │              │   3 orch. modes)     │              │   agreement,       │
└──────────────────┘              └──────────────────────┘              │   contradiction)   │
                                              ▲                         └─────────┬──────────┘
                                              │ recovery actions                  │
                                              │ (rewrite / switch mode / re-rank) │ signals
                                              │                                   │
                                  ┌───────────┴────────────┐                      │
                                  │                        │                      ▼
                          ┌───────┴────────┐      ┌────────┴────────┐    (back to PolicyController)
                          │ AnswerGenerator│ ───► │ Verifier/Critic │
                          │   (LLM draft)  │      │ (groundedness)  │
                          └────────────────┘      └─────────────────┘
                          ↑ produces answer        ↑ checks answer
```

**Separation of concerns (rubric requirement):**

| Role                | Owned by             | Cannot do                                  |
|---------------------|----------------------|--------------------------------------------|
| Answer production   | `AnswerGenerator`    | Decide whether to answer / abstain         |
| Answer checking     | `Verifier`           | Generate or modify the answer              |
| Decision control    | `PolicyController`   | Generate, retrieve, or judge directly      |

This separation is what distinguishes the Step 2 design from a pipeline that just bolts a critic onto the baseline.

---

## 2. Agents

### 2.1 QueryProfiler

- **Inputs:** raw query string.
- **Outputs:** `{lang: en|de, query_type: entity|list|definition|opinion|multihop, ambiguity_flag: bool, ambiguity_reason: str|None, entities: list[str]}`.
- **Implementation sketch:** language detection via `langdetect` (already in deps); query type via FLAN-T5 zero-shot classifier (already in deps via `transformers`); ambiguity via the `is_ambiguous()` heuristic from `src/baseline/failure_analysis.py` generalized beyond benchmark notes (e.g., vague pronouns, multiple plausible referents).
- **Cost:** local CPU model + one regex pass. ~50 ms.

### 2.2 RetrievalCoordinator

- **Inputs:** profiled query, mode hint from PolicyController (`bm25` | `dense` | `graphrag` | `waterfall` | `voting` | `confidence`).
- **Outputs:** `{chunks: [{id, text, score, source}], mode_used: str}`.
- **Implementation sketch:** thin wrapper over the existing `src/baseline/retrievers.py` and `orchestration.py` — no new retrievers built. The mode parameter selects between single-retriever calls and the three orchestration strategies.
- **Recovery support:** accepts a *rewritten* query string and a *previously-tried-modes* list so it can try a different mode on retry.

### 2.3 EvidenceAnalyzer

- **Inputs:** profiled query, retrieved chunks.
- **Outputs:** the full reliability-signal vector (Section 3).
- **Implementation sketch:** runs the signal computations defined below. No LLM call (cheap pass).

### 2.4 AnswerGenerator

- **Inputs:** query, top-k chunks (k=5), language hint.
- **Outputs:** `{draft_answer: str, citations: list[chunk_id], generation_metadata: {...}}`.
- **Implementation sketch:** single OpenAI call with a templated prompt that requires citation of chunk IDs. The prompt explicitly forbids hallucinating beyond the chunks ("if the chunks don't contain the answer, say so").
- **Cost:** ~1 LLM call, ~$0.001 per query at `gpt-4o-mini` rates.

### 2.5 Verifier / Critic

- **Inputs:** query, draft answer, retrieved chunks.
- **Outputs:** `{grounded: bool, grounding_score: float, unsupported_claims: list[str], reason: str}`.
- **Implementation sketch:** two-tier — first a cheap NLI entailment check (HuggingFace model, already in deps via `transformers`) per claim → chunks; if borderline, escalate to an LLM-judge call.
- **Cost:** NLI is local; LLM escalation only fires on borderline cases (~30% of queries).

### 2.6 PolicyController

- **Inputs:** the full `RunState` (profile + chunks + signals + draft + verifier output + retry budget).
- **Outputs:** next action ∈ {`retrieve`, `rewrite_and_retrieve`, `switch_mode_and_retrieve`, `rerank`, `generate`, `verify`, `clarify`, `abstain`, `answer`} + a logged reason string.
- **Implementation sketch:** rule-based state machine (Section 4). Step 3 may upgrade this to a learned router (extra-challenge bonus territory).

---

## 3. Reliability signals

Each signal has: a name, a formula, an output range, and a threshold for the policy. Thresholds are initial guesses to be calibrated in Step 4 against the failure-report ground truth.

| Signal                  | Formula (informal)                                                                                  | Range  | Initial threshold | Failure mode it targets       |
|-------------------------|-----------------------------------------------------------------------------------------------------|--------|-------------------|-------------------------------|
| `sufficiency`           | weighted mix of: (a) score-gap rank-1 vs rank-5, (b) entity coverage of query, (c) top-1 abs score | [0,1]  | `< 0.40` → low    | partial_recall, ranking_failure |
| `chunk_agreement`       | mean pairwise cosine similarity of embeddings of top-k chunks                                       | [0,1]  | `< 0.35` → low    | retrieval noise / drift       |
| `grounding`             | NLI entailment(answer ⇐ chunks); per-claim, then averaged                                           | [0,1]  | `< 0.60` → ungrounded | grounding_failure         |
| `contradiction`         | max pairwise NLI(`contradicts`) across chunks                                                       | [0,1]  | `> 0.50` → conflict | contradiction_failure       |
| `ambiguity`             | bool flag from QueryProfiler + heuristic on entity multiplicity                                     | {0,1}  | `== 1` → clarify  | ambiguity_failure             |
| `confidence`            | weighted aggregate: `0.4·sufficiency + 0.4·grounding + 0.2·(1-contradiction)`                       | [0,1]  | reported as-is    | overconfidence_failure        |

**Why these specific signals.** Each is directly motivated by Step 1 evidence:

- `sufficiency` addresses the **partial_recall** cluster (5–9 queries per strategy where some gold chunks are in top-5 but not all).
- `grounding` addresses the **synthesis / grounding** failure modes that were unobservable in retrieval-only mode.
- `contradiction` is included because the corpus contains time-shifted information (e.g., who held a role *in* year X) where retrieved chunks can disagree.
- `ambiguity` is necessary because the benchmark explicitly contains 3 ambiguous-by-design questions whose ideal behavior is *clarify*, not answer.
- `confidence` is the single number we report alongside an answer (rubric category H).

---

## 4. Decision policy

The PolicyController is a state machine with a bounded retry budget (max 2 recovery loops per query) to keep latency ≤ ~10 s in the typical case.

```
                    ┌──────────────────┐
                    │ START: query in  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ QueryProfiler    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
   ┌──────────────► │ Retrieve (mode = │
   │                │ choose_by_type)  │
   │                └────────┬─────────┘
   │                         │
   │                         ▼
   │                ┌──────────────────┐
   │                │ EvidenceAnalyzer │
   │                └────────┬─────────┘
   │                         │
   │                         ▼
   │              ┌──────────────────────┐
   │              │ Decide on signals:   │
   │              │                      │
   │              │ ambiguity == 1       │──► CLARIFY (return clarification Q)
   │              │                      │
   │              │ contradiction HIGH   │──► REPORT CONFLICT or ABSTAIN
   │              │                      │
   │              │ sufficiency LOW &    │
   │              │   retries left       │──► RECOVER (rewrite + switch mode) ──┐
   │              │                      │                                     │
   │              │ sufficiency LOW &    │                                     │
   │              │   no retries         │──► ABSTAIN                          │
   │              │                      │                                     │
   │              │ sufficiency OK       │──► GENERATE ─► VERIFY               │
   │              └──────────────────────┘         │                           │
   │                                               ▼                           │
   │                                      ┌──────────────────┐                 │
   │                                      │ grounded == True │ ──► ANSWER (with confidence)
   │                                      │ grounded == False│                 │
   │                                      │ & retries left   │ ──► RERANK or RETRIEVE
   │                                      │ grounded == False│                 │
   │                                      │ & no retries     │ ──► ABSTAIN     │
   │                                      └──────────────────┘                 │
   │                                                                           │
   └───────────────────────────────────────────────────────────────────────────┘
```

### Mode selection (`choose_by_type`)

The PolicyController picks the initial retrieval mode based on the QueryProfiler's `query_type`. Initial heuristics (to be replaced by a learned router as Extra Challenge #1):

| query_type   | Initial mode  | Rationale                                                          |
|--------------|---------------|--------------------------------------------------------------------|
| `entity`     | `bm25`        | Named-entity lookup → lexical match wins                           |
| `list`       | `voting`      | Multiple gold chunks → fusion captures more                        |
| `definition` | `dense`       | Paraphrastic match → embeddings                                    |
| `opinion`    | `confidence`  | Vague phrasing → confidence-weighting handles it                   |
| `multihop`   | `graphrag`    | Cross-entity reasoning → graph traversal                           |

### Recovery actions

When `sufficiency` is low and we have retries:

1. **Rewrite the query** (LLM-driven query expansion — add synonyms, expand acronyms, translate EN↔DE).
2. **Switch mode** to a retriever not yet tried.
3. **Cross-encoder rerank** on the top-100 pool. Step 1 showed gold chunks are usually in the top-100 but not top-5 — this is the most direct fix for `ranking_failure`.

The PolicyController logs *which* recovery action it picked and *why*.

---

## 5. Interpretability — DecisionTrace schema

Every query produces one trace JSON saved to `results/agentic/traces/<qid>.json`:

```json
{
  "qid": "Q14",
  "query": "who is working on methods for targeted cancer treatment, and what do they use?",
  "profile": {
    "lang": "en", "query_type": "list", "ambiguity_flag": false, "entities": ["cancer", "ETH"]
  },
  "timeline": [
    {"step": "retrieve", "mode": "voting",     "n_chunks": 100, "elapsed_ms": 320},
    {"step": "analyze",  "signals": {"sufficiency": 0.31, "chunk_agreement": 0.42,
                                     "ambiguity": 0, "contradiction": 0.08}},
    {"step": "decide",   "action": "switch_mode_and_retrieve",
                         "reason": "sufficiency 0.31 < 0.40 threshold; mode 'voting' tried; switching to 'graphrag'",
                         "retries_left": 1},
    {"step": "retrieve", "mode": "graphrag",   "n_chunks": 100, "elapsed_ms": 410},
    {"step": "analyze",  "signals": {"sufficiency": 0.58, ...}},
    {"step": "decide",   "action": "generate", "reason": "sufficiency 0.58 ≥ 0.40"},
    {"step": "generate", "draft_answer": "...", "citations": ["c_1208", "c_4471"]},
    {"step": "verify",   "grounded": true, "grounding_score": 0.81},
    {"step": "decide",   "action": "answer",   "reason": "grounded; confidence 0.71"}
  ],
  "final": {
    "action": "answer",
    "answer": "...",
    "citations": ["c_1208", "c_4471"],
    "confidence": 0.71
  }
}
```

This trace is the artifact Step 4 will use for qualitative analysis (clarification cases, abstention cases, recovery cases, and the ablation study).

---

## 6. Justification — mapping back to Step 1 evidence

Every architectural choice in this document is motivated by a concrete observation from `results/baseline/failure_report.md`:

| Step 1 observation                                                              | Design response                                                                |
|---------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| `ranking_failure` dominates (13–16/24 per strategy); gold chunks often in top-100 but not top-5 | Verifier + cross-encoder rerank as a recovery action over the top-100 pool   |
| `partial_recall` 5–9 cases; system has *some* evidence but not enough           | `sufficiency` signal + abstain branch when no retries remain                   |
| `orchestration_miss`: waterfall picks wrong strategy on 5/24 queries even when another mode would have succeeded | Per-query mode selection in the PolicyController + switch-mode recovery action |
| 3 ambiguous-by-design questions whose ideal behavior is *clarify*               | `ambiguity` signal + dedicated CLARIFY branch in the policy                    |
| Q6, Q7, Q22 retrieval_failure (0 hits in top-100) — corpus / lexical mismatch   | RECOVER branch with LLM-driven query rewrite before declaring abstention       |
| No "success" outcome anywhere — broad questions have hundreds of gold chunks    | Reliability ≠ coverage; we report `confidence` and `grounded` rather than insisting on full top-5 recall |
| Synthesis / grounding / overconfidence unobservable in retrieval-only mode      | Introduce AnswerGenerator + Verifier so these become measurable               |

---

## 7. What this design commits to for Step 3

Step 3 requires implementing **at least four substantial mechanisms**, with at least one that adapts orchestration. From this design, the four are:

1. **(A) Evidence Sufficiency Estimation** — `EvidenceAnalyzer.sufficiency`.
2. **(B) Groundedness Verification** — `Verifier` (NLI + LLM-judge escalation).
3. **(E) Abstention Mechanism** — explicit ABSTAIN branch tied to sufficiency / grounding signals.
4. **(G) Recovery Mechanism + adaptive routing** — query rewrite, mode switching, rerank — **this is the adaptation requirement**, since the choice depends on detected signals and previous outcomes.

(C) Contradiction detection and (D) Clarification are also present and would be reported as bonus mechanisms or used for the Step 4 ablation.

---

## 8. Open questions (decide before Step 3 starts)

- **LLM choice:** confirm `gpt-4o-mini` vs. a local model (latency vs. cost vs. determinism for the report).
- **Verifier model:** which NLI checkpoint? (`roberta-large-mnli` is a safe default but heavy; `cross-encoder/nli-deberta-v3-small` is faster.)
- **Threshold calibration:** the values in Section 3 are guesses. Step 4's evaluation should include a sensitivity sweep, and the report should show the calibration plot.
- **Bilingual handling:** does the verifier need to operate in the original language or do we translate first? (Probably translate to EN for the NLI step.)
- **Trace storage:** JSON-per-query keeps things inspectable but bloats; consider a single JSONL file if we exceed 100 traces.
