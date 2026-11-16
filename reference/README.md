# Reliable and Adaptive Agentic RAG — ETH Zurich Corpus

**Course:** Advanced Generative AI (FS26) — HSLU Applied Data Science & AI Master's  
**Organizers:** Prof. em. Dr. Gerd Kortemeyer (ETH Zurich / MSU), Dr. Guang Lu (HSLU), Dr. Diego Antognini (Google DeepMind)

---

## Overview

This project extends a multilingual multi-agent RAG baseline into a **reliable and adaptive agentic system** that reasons about evidence quality, grounds every answer in retrieved chunks, and knows when to abstain, clarify, or recover, rather than always producing an answer.

The system is built on top of three prebuilt retrievers (BM25, Dense/ChromaDB, GraphRAG) over the ETH Zurich web corpus and adds:

- **Evidence sufficiency estimation** before generation
- **Groundedness verification** (Claude judge) after generation
- **Adaptive recovery** — query rewriting + retrieval-mode switching when evidence is weak
- **Abstention** when evidence remains insufficient after recovery
- **Clarification** for genuinely ambiguous queries
- **Contradiction detection** and a **trust/confidence score** per answer

Full design, results, and critical reflection are in
[`docs/final_report.pdf`](docs/final_report.pdf) (source: [`docs/final_report.md`](docs/final_report.md)).

---

## For Evaluators — How to Verify Each Step

> **All results are pre-computed and committed**, so the project can be reviewed
> directly without re-running anything. Every result, trace, metric, and figure is
> already in this repository and can be opened directly on GitHub. The links below
> take you to each graded step's deliverable.
>
> The *live* pipeline can only be re-executed with the prebuilt retriever
> artifacts (BM25 / Chroma / GraphRAG indexes), which are **too large for GitHub
> and are therefore not included** — see [Retriever artifacts](#retriever-artifacts-required-for-steps-3-5).
> This affects re-running only; **all committed results below are complete and
> were produced by the full pipeline.** The
> [demonstration](#2-system-demonstration-fastest-way-to-see-the-system-work)
> also runs with no artifacts and no API key.

**Start here:** read the report — [`docs/final_report.pdf`](docs/final_report.pdf).

| Step (points) | What to look at | Where |
|---|---|---|
| **1 — Baseline + Failure Analysis** (15) | Reproduced baseline code; metrics table (P@k, Recall@k, MRR, latency); structured failure taxonomy | Code: [`src/baseline/`](src/baseline) · Metrics: [`results/baseline/metrics_summary.csv`](results/baseline/metrics_summary.csv) · Failures: [`results/baseline/failure_report.md`](results/baseline/failure_report.md) · Report §2–§3 |
| **2 — Reliability-Aware Design** (20) | 6-agent architecture, reliability signals, decision policy, separation of concerns | Design doc: [`docs/step2_design.md`](docs/step2_design.md) · Diagram: [`docs/architecture.png`](docs/architecture.png) · Report §4 |
| **3 — Reliability Mechanisms + Adaptive Recovery** (25) | 7 implemented mechanisms; per-query decision traces showing every action + reason | Code: [`src/agentic/`](src/agentic) (`signals.py`, `verifier.py`, `policy.py`, `pipeline.py`) · Traces: [`results/agentic/traces/`](results/agentic/traces) · Report §5–§6 |
| **4 — Evaluation + Analysis** (10) | Quantitative metrics, ablation study, benchmark extension, calibration | Metrics: [`results/agentic/evaluation_metrics.json`](results/agentic/evaluation_metrics.json) + [`evaluation.md`](results/agentic/evaluation.md) · Ablations: [`results/agentic/no_recovery/`](results/agentic/no_recovery), `no_abstain/`, `no_clarify/` · Extension: [`results/agentic/reliability/`](results/agentic/reliability) · Eval doc: [`docs/step4_evaluation.md`](docs/step4_evaluation.md) · Report §7–§8 |
| **5 — Final Report** (5) | Complete report covering all steps + critical reflection + tool disclosure | [`docs/final_report.pdf`](docs/final_report.pdf) |
| **Extra Challenge #2 — Confidence Calibration** | ECE 0.47 reliability diagram + analysis | [`results/agentic/confidence_calibration.png`](results/agentic/confidence_calibration.png) · Report §7 |

**Required deliverables (project brief):**

| Deliverable | Where |
|---|---|
| Codebase / Notebook | [`src/`](src) |
| Final Report | [`docs/final_report.pdf`](docs/final_report.pdf) |
| Evaluation Results | [`results/`](results) (152 committed files: traces, metrics, ablations, figures) |
| Benchmark Extension | [`Baseline/benchmark/benchmark_reliability.json`](Baseline/benchmark/benchmark_reliability.json) (15 cases, 5 categories) |
| System Demonstration | `python -m src.scripts.demo` (replays committed traces — no setup) |

---

## Repository Structure

```
Adv.-Gen-AI/
│
├── Baseline/                          # Inherited from previous semester
│   ├── advanced_genAI-main/           # Prior team's Colab notebooks + scripts
│   └── benchmark/
│       ├── benchmark_qa_bilingual.json          # 25-question benchmark (EN/DE)
│       ├── benchmark_reliability.json           # 15-case reliability extension
│       └── reliability_labels.json             # Expected behaviour per question
│
├── src/
│   ├── baseline/                      # Locally-runnable wrapper over baseline artifacts
│   │   ├── config.py                  # All paths and model parameters
│   │   ├── retrievers.py              # BM25 / Dense / GraphRAG loader wrappers
│   │   ├── orchestration.py           # Waterfall / Voting / Confidence strategies
│   │   ├── evaluation.py              # pytrec_eval metric computation
│   │   └── failure_analysis.py        # Failure taxonomy classifier
│   │
│   ├── agentic/                       # Reliable & adaptive agentic system (Step 3)
│   │   ├── pipeline.py                # Main AgenticRAG class — wires all agents
│   │   ├── state.py                   # RunState / DecisionTrace / Signals dataclasses
│   │   ├── policy.py                  # PolicyController state machine
│   │   ├── profiler.py                # QueryProfiler (lang, type, ambiguity)
│   │   ├── signals.py                 # EvidenceAnalyzer (sufficiency, agreement)
│   │   ├── retrieval.py               # RetrievalCoordinator wrapper
│   │   ├── generator.py               # AnswerGenerator (Claude, grounded prompting)
│   │   ├── verifier.py                # Verifier/Critic (Claude judge)
│   │   └── llm.py                     # Anthropic Claude API client
│   │
│   └── scripts/
│       ├── demo.py                    # ← Quick demonstration (3 example queries)
│       ├── run_baseline.py            # Run all 3 baseline strategies on benchmark
│       ├── run_agentic.py             # Run full agentic pipeline on benchmark
│       ├── run_step4_suite.py         # Run 3 ablations + reliability extension
│       ├── evaluate_agentic.py        # Compute all evaluation metrics + LLM judge
│       ├── analyze_failures.py        # Generate baseline failure report
│       ├── calibration_plot.py        # Confidence calibration (ECE + plot)
│       └── make_reliability_labels.py # Generate reliability_labels.json
│
├── results/
│   ├── baseline/                      # Step 1 results
│   │   ├── metrics_summary.csv        # P@k, Recall@k, MRR, latency for all 3 strategies
│   │   ├── failure_report.md          # Structured failure taxonomy
│   │   └── per_query_*.json           # Per-query retrieval results
│   │
│   └── agentic/                       # Step 3–4 results
│       ├── answers.json               # Final answers for all 25 questions
│       ├── evaluation_metrics.json    # Full metrics (grounding, abstention, recovery, etc.)
│       ├── evaluation.md              # Human-readable evaluation summary
│       ├── confidence_calibration.png # ECE reliability diagram
│       ├── run_summary.json           # Models used, cost, latency
│       ├── traces/                    # Per-query DecisionTrace JSON files
│       ├── reliability/               # Benchmark extension run (15 cases)
│       ├── no_recovery/               # Ablation: recovery disabled
│       ├── no_abstain/                # Ablation: abstention disabled
│       └── no_clarify/                # Ablation: clarification disabled
│
├── docs/
│   ├── final_report.md                # ← Main report (all 5 steps)
│   ├── step2_design.md                # Architecture design doc (Step 2 detail)
│   ├── step4_evaluation.md            # Full evaluation tables and discussion
│   ├── step3_progress.md              # Implementation notes
│   └── step3_full_benchmark.md        # Benchmark run details
│
├── requirements.txt
├── .env.example                       # API key template — copy to .env and fill in
└── Adv GenAI Project_FS26.pdf         # Original project brief
```

---

## Quick Start

### 1. Environment

```bash
pip install -r requirements.txt
cp .env.example .env          # then set ANTHROPIC_API_KEY (and BASELINE_ROOT)
```

> **BASELINE_ROOT** must point to the `Baseline/` folder on your machine.  
> The prebuilt retriever artifacts (BM25 pickle, ChromaDB store, GraphRAG graph)
are not in this repo. Contact the project team or use the shared storage path.

### 2. System demonstration (fastest way to see the system work)

```bash
python -m src.scripts.demo
```

Replays three pre-computed DecisionTraces from `results/agentic/traces/` — one
grounded answer, one abstention, and one clarification — printing the full
step-by-step agent decisions and signals for each. **No API key or retriever
artifacts required.** The traces were produced by the full benchmark run
committed in this repo (`results/agentic/`).

### 3. Reproduce baseline (Step 1)

> ⚠️ **Requires retriever artifacts** — see note below before running steps 3–5.

```bash
python -m src.scripts.run_baseline        # → results/baseline/metrics_summary.csv
python -m src.scripts.analyze_failures    # → results/baseline/failure_report.md
```

### 4. Reproduce agentic system (Step 3)

```bash
python -m src.scripts.run_agentic         # → results/agentic/  (~12 min, ~$1 API cost)
```

### 5. Reproduce evaluation + ablations (Step 4)

```bash
python -m src.scripts.run_step4_suite     # ablations + reliability extension
python -m src.scripts.evaluate_agentic --judge          # main metrics + LLM correctness
python -m src.scripts.calibration_plot                  # ECE + calibration plot
```

All results are already committed in `results/` and can be inspected directly, without re-running.

> ### Retriever artifacts (required for steps 3-5)
>
> ⚠️ The prebuilt retriever artifacts are **not included in this repository** due to
> their size (~several GB). They must be obtained separately and placed at:
>
> ```
> Baseline/storage/full_corpus/retrieval/fixed_size_chunk/bm25_retriever_full.pkl
> Baseline/storage/full_corpus/vectordb_dense/fixed_e5/
> Baseline/storage/full_corpus/retrieval_graph/
> Baseline/storage/full_corpus/Lang_norm/fixed_size_chunk/docs_fixed_norm.pkl
> ```
>
> Contact the project team for access to the shared storage. The demo script
> (step 2) and all pre-committed results in `results/` are fully usable without them.

---

## Key Results

| Dimension | Baseline (Confidence) | Agentic (full) |
|---|---|---|
| Retrieval P@5 | 0.117 | **0.142** |
| Retrieval MRR | 0.205 | **0.218** |
| Grounded-answer rate | n/a | **1.00** |
| Unsupported claims / answer | n/a | **0.00** |
| Answer coverage (answerable Qs) | n/a | **0.81** |
| Latency avg | ~1 s | ~29 s |

See [`docs/final_report.md`](docs/final_report.md) for the full evaluation, ablation study, benchmark extension, and critical reflection.

---

## Regenerating the documents

The architecture diagram and report PDF are generated from source (pure-Python,
no system libraries needed):

```bash
python -m src.scripts.make_architecture_diagram   # → docs/architecture.png
python -m src.scripts.report_to_pdf               # → docs/final_report.pdf
```

---

## Dependencies and API Keys

- **Anthropic API key** (`ANTHROPIC_API_KEY`): required to run the agentic system. Used for answer generation (`claude-opus-4-7`), verification, query profiling, and rewriting (`claude-haiku-4-5`).
- **OpenAI API key** (`OPENAI_API_KEY`): only needed for the inherited Step 1 LLM metadata extraction scripts in `Baseline/advanced_genAI-main/` — not required for our system.

Estimated cost to reproduce the full benchmark: **~$1.00** (25 questions × ~$0.04/query).

---

## Acknowledgements

- Baseline retrievers, prebuilt indexes, and benchmark inherited from the previous semester's team (see `Baseline/`)
- LangChain, ChromaDB, sentence-transformers, HuggingFace Transformers (M2M100, FLAN-T5, MiniLM, e5), pytrec_eval, Anthropic SDK
- Claude Code (Anthropic) used for implementation scaffolding — see `docs/final_report.md §11` for full disclosure
