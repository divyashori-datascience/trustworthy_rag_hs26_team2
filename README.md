# Evaluating and Improving Trustworthy Agentic RAG Systems

**Advanced Generative AI · HSLU HS26 · Team 2** · Divya Shori, Faranak Rahimi, Hanieh Jebeli

We start from Cyriel & Vincent's reliable agentic RAG reference system (FS26), audit it, extend the reliability benchmark, implement one focused improvement and evaluate the tradeoffs.

## Layout

| Path | What | Rule |
|---|---|---|
| `reference/` | Reference implementation, unchanged (from `Baseline.zip`) | **Never edit.** It's our baseline. |
| `src/ours/` | Everything we add: `traces/` (audit scripts), `benchmark/` (chunk-ID lookup), `eval/` (run comparison), `improvement/` (Step 3) | Reusable code lives here, not in notebooks. |
| `notebooks/` | Numbered Colab notebooks, **one owner each** | Don't edit someone else's notebook (avoids merge conflicts). |
| `benchmark/` | Our group's benchmark submission + the shared dev set once released | |
| `results/<run_id>/` | Traces, metrics, `run_meta.json` per run | Never overwrite; one folder per run. |
| `docs/` | Audit notes (`audit/`), benchmark notes (`benchmark/`), report PDFs (`reports/`) | |

Indexes, API keys and large files are **not** in git. Indexes come from the shared course Drive (`RAG_Project_Artifact/storage/full_corpus`); keys go in Colab Secrets.

## Where things are

| Step | Status | Start here |
|---|---|---|
| 1 · Reference system audit | Done (draft for team review) | [`docs/reports/G02_Step1_report.pdf`](docs/reports/G02_Step1_report.pdf), [`docs/audit/`](docs/audit/README.md) |
| 1 · Failure demo (Q&A 1) | Ready: replay + index check + live run for 5 cases | [`notebooks/01_failure_demo.ipynb`](notebooks/01_failure_demo.ipynb) |
| 1 · Reproduction run | Done: 25 questions, 21/25 actions match | [`docs/audit/reproduction_note.md`](docs/audit/reproduction_note.md), [`results/20261117_colab_full_run/`](results/20261117_colab_full_run/README.md) |
| 2 · Benchmark | Final: 10 self-validated cases, emailed to the instructor by Mon 23 Nov | [`benchmark/G02_benchmark.xlsx`](benchmark/G02_benchmark.xlsx), [`docs/benchmark/`](docs/benchmark/README.md) |
| 2 · Coverage gaps | Documented separately | [`docs/benchmark/coverage_gaps.md`](docs/benchmark/coverage_gaps.md) |
| 3 · Improvement | Track to choose at Q&A 3 | [`docs/audit/failure_taxonomy.md`](docs/audit/failure_taxonomy.md) |

## Getting started (Colab)
1. In Drive, add a shortcut to `RAG_Project_Artifact` in **My Drive**.
2. Colab → 🔑 Secrets → `ANTHROPIC_API_KEY` (notebook access on).
3. Runtime → T4 GPU.
4. Open `notebooks/00_setup_reference_system.ipynb` and run all the cells.

## Owners

| Work | Owner | Status |
|---|---|---|
| Repository setup, structure and contribution workflow | Divya Shori | Done |
| Colab setup notebook and reproduction of the reference system (test queries + full 25-question run) | Divya Shori | Done |
| Step 1 audit: trace audit, diagnostic cases (Q4, Q1, Q18), failure taxonomy, index coverage analysis | Divya Shori | Done, team review pending |
| Step 1 report (`docs/reports/G02_Step1_report.pdf`) | Divya Shori | Done |
| Step 2 benchmark draft (14 cases with chunk IDs) and coverage gaps | Divya Shori | Done |
| Validation of benchmark cases (draft 006–014) | Hanieh Jebeli | Done |
| Validation of benchmark cases (draft 001–005), final selection of 10 | Divya Shori | Done |
| Improvement track one-pager (Track A vs B) for Q&A 3 | Hanieh Jebeli | Hanieh Jebeli | Done,review pending |

## Milestones
- [x] **Thu 19 Nov · Q&A 1:** reference system running; ≥3 trace-based cases; initial failure modes
- [x] **Mon 23 Nov 09:00:** benchmark Excel by email (10 validated cases, ≥4 categories, ≥2 standard factual)
- [ ] **Wed 26 Nov · Q&A 3:** metrics aligned, improvement track chosen
- [ ] **Wed 23 Dec · Final submission (ILIAS):** final report + link to this repo (shared with the course instructor's GitHub account)

## Submission requirements (course instructor, Nov 2026)
- One notebook per step (1–5) is fine, plus a **separate concise final report** (analyses, results, limitations, reflections).
- Benchmark Excel: **by email** to the course instructor by 23 Nov, 09:00.
- Final submission on **ILIAS** with the report and a link to this repo (code, notebooks, benchmark, supporting artifacts).
- Evaluate the 25 original questions on their **original labels**, wrong ones included; describe the label problems in the report, don't fix them (Q&A 1, 19 Nov).
- Must include **decision traces**, **individual contributions** (see Owners) and **AI-tool-use statements** (`docs/ai_use_log.md`).

## How we work
Branch → pull request → review by a teammate → merge to `main`. See [CONTRIBUTING.md](CONTRIBUTING.md).

## AI tool use
We log AI assistance as we go in `docs/ai_use_log.md` (tool, what it was used for, how we checked it), because the final report requires it.
