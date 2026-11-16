# Reproduction note (TO FILL after the Colab run)

**Notebook:** `notebooks/00_setup_reference_system.ipynb`
**Artifacts:** shared `RAG_Project_Artifact/storage/full_corpus` (course Drive)
**Run folder:** `My Drive/AdvGenAI/runs/<YYYYMMDD_HHMM>/` → copy `run_meta.json`, `setup_issues.md` and the traces to `results/<run_id>/`

## Environment
- Colab runtime / GPU:
- Package versions (from `run_meta.json`):
- Models (generation / verifier / utility):

## What ran
- [ ] Smoke test (imports, paths, QA, qrels)
- [ ] Replay demo
- [ ] Live system loaded (`AgenticRAG.from_pretrained()`)
- [ ] Test queries: Q4, Q1, Q18, Q1 (DE)
- [ ] Full 25-question run (optional)

## Comparison with the reference team's traces

| Q | Their action | Our action | Same? | Notes |
|---|---|---|---|---|
| 4 | answer | | | |
| 1 | abstain | | | |
| 18 | abstain | | | |
| 1-DE | — | | | |

## Issues encountered
(Paste from `setup_issues.md`: what broke, the error, the fix or workaround.)

## Cost and latency
- LLM cost of this run:
- Average / max latency:
