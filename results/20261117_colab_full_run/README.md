# Colab full run, 17 Nov 2026

Full 25-question run of the reference system (`run_benchmark(rag, qa, out_dir, 'full')`) on the shared `full_corpus` artifacts, from `notebooks/00_setup_reference_system.ipynb`.

| File | Content |
|---|---|
| `run_summary.json` | Action counts, latency, LLM usage and cost |
| `actions.csv` | Per question: final action, confidence, final retrieval mode, latency |

The full answers (`answers.json`) and per-question traces (`traces/<id>.json`) are in the team Drive under `My Drive/AdvGenAI/runs/20261117_1540/benchmark/`.

Compare with the reference team's run:

```
python src/ours/eval/compare_runs.py results/20261117_colab_full_run/actions.csv
```

Results and interpretation: [`docs/audit/reproduction_note.md`](../../docs/audit/reproduction_note.md).
