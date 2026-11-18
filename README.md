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
| 1 · Reproduction run | Done: 25 questions, 21/25 actions match | [`docs/audit/reproduction_note.md`](docs/audit/reproduction_note.md), [`results/20261117_colab_full_run/`](results/20261117_colab_full_run/README.md) |
| 2 · Benchmark | 14 candidate cases, team validation in progress | [`benchmark/G02_benchmark_draft.xlsx`](benchmark/G02_benchmark_draft.xlsx), [`docs/benchmark/`](docs/benchmark/README.md) |
| 2 · Coverage gaps | Documented separately | [`docs/benchmark/coverage_gaps.md`](docs/benchmark/coverage_gaps.md) |
| 3 · Improvement | Track to choose at Q&A 3 | [`docs/audit/failure_taxonomy.md`](docs/audit/failure_taxonomy.md) |

## Getting started (Colab)
1. In Drive, add a shortcut to `RAG_Project_Artifact` in **My Drive**.
2. Colab → 🔑 Secrets → `ANTHROPIC_API_KEY` (notebook access on).
3. Runtime → T4 GPU.
4. Open `notebooks/00_setup_reference_system.ipynb` and run all the cells.

## Owners
To be agreed within the team.

## Milestones
- [x] **Thu 19 Nov · Q&A 1:** reference system running; ≥3 trace-based cases; initial failure modes
- [ ] **Mon 23 Nov 09:00:** benchmark Excel (10 validated cases, ≥4 categories, ≥2 standard factual)
- [ ] **Wed 26 Nov · Q&A 3:** metrics aligned, improvement track chosen

## How we work
Branch → pull request → review by a teammate → merge to `main`. See [CONTRIBUTING.md](CONTRIBUTING.md).

## AI tool use
We log AI assistance as we go in `docs/ai_use_log.md` (tool, what it was used for, how we checked it), because the final report requires it.
