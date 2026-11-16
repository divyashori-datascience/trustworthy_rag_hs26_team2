# Initial failure taxonomy (DRAFT)

Counts are from the reference team's 25 traces; a question can show more than one failure mode. To be updated with our own run.

| Failure mode | Questions | Count | How we know | Points to track |
|---|---|---|---|---|
| False abstention (evidence exists, system declines) | 1, 18 (6, 17 disputed) | 2 (+2 disputed) | `evidence_found=false` × 3; corpus has evidence for Q1 and Q18, none found for Q6 and Q17 | B, F |
| Ranking / retrieval failure | 1, 4, 6, 17, 18 + most partials | 5+ | Step 1 report: gold usually in top 100, not top 5 | F, B |
| Non-answer ("evidence is silent") counted as ANSWER | 10, 12, 20 | 3 | Draft says the evidence doesn't cover it; gold shows it does | B, A |
| Incomplete / partial answer | 2, 3, 7, 8, 9, 13, 15, 16, 21, 23, 25 | 11 | LLM judge: partially correct | F |
| Weak confidence calibration | all answered | 20 | Mean confidence 0.89 vs mean correctness 0.42; ECE 0.47 | A |
| Missed clarification | 3, 7, 23 | 3 | Labelled clarify; system answered | E |
| Unnecessary clarification | 5 | 1 | Answer exists; asked "which Schubert?" | E |
| Benchmark text corruption | 10, 12, 15, 18, 22 | 5 | "ti" → "z" in stored questions | Step 2 |
| Wrong or unreachable gold label | 1, 6, 17, 18 | 4 | Label from qrels count (Q1); gold answer not in the raw corpus (Q6, Q17, Q18) | Step 2 |
| Temporal reasoning needed | 1, 2, 20 | 3 | Answer depends on dates or periods | C, Step 2 |
| Contradiction never detected | — | 0 | No conflicting chunks surfaced together | D |
| Critique loop never fired | — | 0 | Verifier approved every draft first time | D, H |
| High latency in recovery | 1, 12 | 2 | 252 s and 41 s vs 29 s average | I |

## Motivation for our improvement focus (to decide at Q&A 3, 26 Nov)

- **Track A, confidence calibration.** The clearest measurable gap: ECE 0.47, and confidence drives no decision. Idea: make confidence predict correctness (retrieval and rerank scores, agreement across modes, an answer-completeness check), then use it for the answer/abstain threshold.
- **Track B / F, false abstention and retrieval.** The biggest correctness gap. Idea: cross-encoder rerank of a larger candidate pool (top 50–100) before generation, plus a check before final abstention.
- **Track E, clarification.** Only 4 cases, so a measurable improvement is hard to show on this benchmark alone.

All tracks depend on a clean benchmark, so our Step 2 cases should avoid the label problems above.
