# Initial failure taxonomy (DRAFT)

Counts are from the reference team's 25 traces; a question can show more than one failure mode. To be updated with our own run.

| Failure mode | Questions | Count | How we know | Points to track |
|---|---|---|---|---|
| False abstention (evidence is in the index, system declines) | 1, 18 | 2 | `evidence_found=false` × 3; supporting chunks exist (Q1: `8a6b1a87…_fixed_1`; Q18: 4 Hong Kong chunks) | B, F |
| Indexing loses content (answer in raw page, not in any chunk) | e.g. Olympiad, tuition amounts, QS 7th (EN) | 37% of pages not indexed; lead missing on 92% of indexed pages | `index_coverage.py` | Out of agent scope; ask Guang |
| Ranking / retrieval failure | 1, 4, 18 + most partials | 3+ | Step 1 report: gold usually in top 100, not top 5 | F, B |
| Non-answer ("evidence is silent") counted as ANSWER | 10, 12, 20 | 3 | Draft says the evidence doesn't cover it; gold shows it does | B, A |
| Incomplete / partial answer | 2, 3, 7, 8, 9, 13, 15, 16, 21, 23, 25 | 11 | LLM judge: partially correct | F |
| Weak confidence calibration | all answered | 20 | Mean confidence 0.89 vs mean correctness 0.42; ECE 0.47 | A |
| Missed clarification | 3, 7, 23 | 3 | Labelled clarify; system answered | E |
| Unnecessary clarification | 5 | 1 | Answer exists; asked "which Schubert?" | E |
| Benchmark text corruption | 10, 12, 15, 18, 22 | 5 | "ti" → "z" in stored questions | Step 2 |
| Wrong or unreachable gold label | 1, 6, 17, 18 | 4 | Q1 labelled abstain but answerable; Q6, Q17 labelled answer but no supporting chunk; Q18 gold not in corpus | Step 2 |
| Temporal reasoning needed | 1, 2, 20 | 3 | Answer depends on dates or periods | C, Step 2 |
| Contradiction never detected | — | 0 | No conflicting chunks surfaced together | D |
| Critique loop never fired | — | 0 | Verifier approved every draft first time | D, H |
| High latency in recovery | 1, 12 | 2 | 252 s and 41 s vs 29 s average | I |

## Motivation for our improvement focus (to decide at Q&A 3, 26 Nov)

- **Track A, confidence calibration.** The clearest measurable gap: ECE 0.47, and confidence drives no decision. Idea: make confidence predict correctness (retrieval and rerank scores, agreement across modes, an answer-completeness check), then use it for the answer/abstain threshold.
- **Track B / F, false abstention and retrieval.** The biggest correctness gap. Idea: cross-encoder rerank of a larger candidate pool (top 50–100) before generation, plus a check before final abstention.
- **Track E, clarification.** Only 4 cases, so a measurable improvement is hard to show on this benchmark alone.

All tracks depend on a clean benchmark, so our Step 2 cases should avoid the label problems above.
