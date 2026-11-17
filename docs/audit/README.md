# Step 1: Reference system audit (DRAFT)

> **Status: draft for Q&A 1 (Thu 19 Nov 2026).** The findings are based on the reference team's committed run (`reference/results/agentic/`). They still have to be re-checked against our own live run on the shared `full_corpus` artifacts, and the team should agree on and rewrite them before final submission.

| File | Step 1 deliverable | Status |
|---|---|---|
| [`reproduction_note.md`](reproduction_note.md) | Short reproduction note | To fill after the Colab run |
| [`trace_audit.md`](trace_audit.md) | Diagnostic analysis of all 25 traces | Draft |
| [`case_Q4.md`](case_Q4.md) | Trace-based example: success after recovery | Draft |
| [`case_Q1.md`](case_Q1.md) | Trace-based example: false abstention + wrong label | Draft |
| [`case_Q18.md`](case_Q18.md) | Trace-based example: gold answer not in the corpus | Draft |
| [`index_coverage.md`](index_coverage.md) | Finding: what the shared index is missing | Draft |
| [`failure_taxonomy.md`](failure_taxonomy.md) | Initial failure taxonomy + motivation for the improvement focus | Draft |
| [`open_questions.md`](open_questions.md) | Questions for the course instructor | Draft |
| [`case_template.md`](case_template.md) | Template for further cases | — |

## Reproducing the numbers

```bash
# Per-question table from a run's traces (default: the reference team's run)
python -m src.ours.traces.audit_traces --out docs/audit/trace_audit.csv
python -m src.ours.traces.audit_traces --run results/<our_run_id>/benchmark

# Does an answer exist in the corpus, independent of retrieval?
python -m src.ours.traces.search_corpus --zip /path/to/HKNews.zip "Kübler"
python -m src.ours.traces.search_corpus --zip /path/to/HKNews.zip --all "Hong Kong" "ETH"

# What the index contains (the system can only answer from these chunks)
python -m src.ours.benchmark.fill_chunk_ids --pkl /path/to/docs_fixed_norm.pkl --find "Olaf Kübler"
python -m src.ours.traces.index_coverage --zip /path/to/HKNews.zip --pkl /path/to/docs_fixed_norm.pkl
```
