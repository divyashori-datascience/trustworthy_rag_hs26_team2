# Reproduction note (17 Nov 2026)

**Result:** the reference system loaded and ran in Colab on the shared `full_corpus` artifacts with **no setup or compatibility issues**. All 4 test queries reproduced the reference team's final actions. In the full 25-question run, **21 of 25 actions matched** the reference run; the 4 that changed all sit at the clarify/abstain decision boundary.

**Notebook:** `notebooks/00_setup_reference_system.ipynb` (opened in Colab from this repo)
**Artifacts:** shared `RAG_Project_Artifact/storage/full_corpus` (course Drive, via a My Drive shortcut; copied to the Colab disk, 364 MB)
**Run folder:** `My Drive/AdvGenAI/runs/20261117_1540/` (`run_meta.json`, `setup_issues.md`, `traces/`, `benchmark/answers.json`, `benchmark/run_summary.json`)

## Environment
- Colab Pro, T4 GPU (High RAM), Python 3.13, CUDA available
- Packages: langchain 0.3.30, langchain-community 0.3.31, langchain-core 0.3.86, langchain-huggingface 0.3.1, chromadb 1.5.9, sentence-transformers 5.7.0, transformers 5.22.1, torch 2.14.1+cu130, anthropic 2.9.0, numpy 2.4.6
- Models: generation and verifier `claude-opus-4-7`, utility `claude-haiku-4-5` (the reference defaults)

## What ran
- [x] Smoke test (imports, paths, 25 QA questions, qrels for 24 questions)
- [x] Replay demo (pre-computed traces)
- [x] Live system loaded (`AgenticRAG.from_pretrained()`) with BM25, dense (Chroma/e5), GraphRAG and all agents
- [x] Test queries: Q4, Q1, Q18, Q1 in German
- [x] Full 25-question run (`run_benchmark(..., 'full')`)

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

## Full 25-question run

| | Reference run | Our run |
|---|---|---|
| Actions (answer / abstain / clarify) | 20 / 4 / 1 | 18 / 5 / 2 |
| Same action as reference | | **21 / 25** |
| Matches `expected_behavior` in `reliability_labels.json` | 18 / 25 | 16 / 25 |
| Mean latency | 28.7 s | 12.2 s |
| Max latency | 251.9 s (Q1) | 20.7 s (Q23) |
| LLM calls | 102 | 99 |
| Cost | $0.95 | $0.87 |

**The 4 questions whose action changed** (all labelled `answer` in the reference labels):

| Q | Question | Reference | Ours | Comment |
|---|---|---|---|---|
| 5 | Prof. Schubert on flying | clarify | answer | Our answer matches the gold (air fares too cheap, surcharges). The reference's clarify was a wrong action. |
| 10 | Fertilizer without carbon emissions | answer (judged incorrect) | clarify | Unnecessary clarification ("which fertilizer?") on a clear question. |
| 12 | ETH electricity used by computing | answer (judged incorrect) | abstain | Abstained although 26 gold chunks are listed. The gold itself says data is limited. |
| 20 | Student number projections | answer (judged incorrect) | clarify | Unnecessary clarification ("which time period?"); the gold is a single projection (3.5 % per year). |

### What this tells us
- **The final action is not stable between runs.** 4 of 25 decisions (16 %) flipped with the same code, data and models. All 4 flips involve clarify or abstain, which are driven by the Haiku query profiler's ambiguity flag and the sufficiency/grounding thresholds. Answer-to-answer cases were stable.
- **The flips mostly swap one failure for another.** In three cases an incorrect answer became a non-answer (clarify or abstain). That lowers risk but also lowers coverage. Q5 went the other way (wrong clarify → correct answer).
- **Consequence for our evaluation:** a single run is not enough to compare the baseline with our improved system. In Step 3 we will run each configuration at least 3 times and report the action agreement across runs next to accuracy.
- **Retrieval modes were stable.** The final retrieval mode matched the reference on every question where the action matched.
- **Latency is much lower and flatter** (mean 12 s, max 21 s). This confirms that the reference's 252 s on Q1 was an environment effect, not a property of the query.

## Issues encountered
None. `setup_issues.md` reports 0 issues.

## Cost
About $0.16 for the 4 test queries plus $0.87 for the full 25-question run.
