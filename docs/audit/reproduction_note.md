# Reproduction note (17 Nov 2026)

**Result:** the reference system loaded and ran in Colab on the shared `full_corpus` artifacts with **no setup or compatibility issues**. All 4 test queries reproduced the reference team's final actions.

**Notebook:** `notebooks/00_setup_reference_system.ipynb` (opened in Colab from this repo)
**Artifacts:** shared `RAG_Project_Artifact/storage/full_corpus` (course Drive, via a My Drive shortcut; copied to the Colab disk, 364 MB)
**Run folder:** `My Drive/AdvGenAI/runs/20261117_1540/` (`run_meta.json`, `setup_issues.md`, `traces/`)

## Environment
- Colab Pro, T4 GPU (High RAM), Python 3.13, CUDA available
- Packages: langchain 0.3.30, langchain-community 0.3.31, langchain-core 0.3.86, langchain-huggingface 0.3.1, chromadb 1.5.9, sentence-transformers 5.7.0, transformers 5.22.1, torch 2.14.1+cu130, anthropic 2.9.0, numpy 2.4.6
- Models: generation and verifier `claude-opus-4-7`, utility `claude-haiku-4-5` (the reference defaults)

## What ran
- [x] Smoke test (imports, paths, 25 QA questions, qrels for 24 questions)
- [x] Replay demo (pre-computed traces)
- [x] Live system loaded (`AgenticRAG.from_pretrained()`) with BM25, dense (Chroma/e5), GraphRAG and all agents
- [x] Test queries: Q4, Q1, Q18, Q1 in German
- [ ] Full 25-question run (next step)

## Comparison with the reference team's traces

| Q | Their action | Our action | Same? | Retrieval modes (ours) | Confidence | Latency: theirs → ours |
|---|---|---|---|---|---|---|
| 4 (InSight) | answer | answer | ✓ | BM25 → voting | 0.94 | 20.8 s → 27.9 s |
| 1 (ETH president 2003) | abstain | abstain | ✓ | BM25 → voting → GraphRAG | 0.00 | 251.9 s → 63.3 s |
| 18 (Hong Kong) | abstain | abstain | ✓ | voting → GraphRAG → confidence | 0.00 | 19.3 s → 31.0 s |
| 1-DE ("Wer war 2003 Präsident der ETH Zürich?") | — | abstain | — | BM25 → voting → GraphRAG | 0.00 | — → 11.3 s |

Q4 answer: "The InSight stationary lander safely landed on the Martian surface in November 2018" (matches gold).

## Observations
- **Same decisions, same failure modes.** Q1 and Q18 abstain again after three generator "not found" results, although supporting chunks exist in the index (Q1: `8a6b1a87…_fixed_1`). So the false abstentions in our audit are reproducible, not run-to-run noise.
- **The German query fails the same way**, even though the evidence is an English chunk; neither the rewrite nor the mode switch recovered it.
- **Q1's extreme latency did not recur** (63 s vs 252 s), so the earlier spike looks environment-related (e.g. first-time model loading), not inherent to the query.

## Issues encountered
None. `setup_issues.md` reports 0 issues.

## Cost
About $0.16 of API usage for the 4 queries.
