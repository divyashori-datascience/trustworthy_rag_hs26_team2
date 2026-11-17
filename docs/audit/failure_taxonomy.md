# Initial failure taxonomy (DRAFT)

Counts are from the reference team's 25 traces; a question can show more than one failure mode. To be updated with our own run.

Each failure is tagged with the **stage** where it originates, so that the final report can separate data-preparation issues from retrieval, generation and decision failures (as requested by the course instructor, 17 Nov):

- **Data preparation:** HTML extraction, chunking, indexing. The shared artifacts stay fixed, so these are documented, not fixed.
- **Retrieval:** finding and ranking the right chunks.
- **Generation:** drafting and verifying the answer.
- **Decision policy:** choosing answer / abstain / clarify / recover, and the confidence score.
- **Benchmark:** the test data itself (questions, labels).

| Stage | Failure mode | Questions | Count | How we know | Points to track |
|---|---|---|---|---|---|
| Data preparation | Content lost during extraction / indexing (answer in raw page, not in any chunk) | see [`index_coverage.md`](index_coverage.md) | 37% of pages not indexed; lead missing on 92% of indexed pages | `index_coverage.py` | Documented only (artifacts fixed) |
| Retrieval | False abstention (evidence is in the index, system declines) | 1, 18 | 2 | `evidence_found=false` × 3; supporting chunks exist (Q1: `8a6b1a87…_fixed_1`; Q18: 6 Hong Kong chunks) | B, F |
| Retrieval | Ranking failure (gold chunk outside the generator's top-5) | 1, 4, 18 + most partials | 3+ | Step 1 report: gold usually in top 100, not top 5 | F, B |
| Generation | Incomplete / partial answer | 2, 3, 7, 8, 9, 13, 15, 16, 21, 23, 25 | 11 | LLM judge: partially correct | F |
| Generation | Critique loop never fired | — | 0 | Verifier approved every draft first time | D, H |
| Decision policy | Non-answer ("evidence is silent") counted as ANSWER | 10, 12, 20 | 3 | Draft says the evidence doesn't cover it; gold shows it does | B, A |
| Decision policy | Weak confidence calibration | all answered | 20 | Mean confidence 0.89 vs mean correctness 0.42; ECE 0.47 | A |
| Decision policy | Missed clarification | 3, 7, 23 | 3 | Labelled clarify; system answered | E |
| Decision policy | Unnecessary clarification | 5 | 1 | Answer exists; asked "which Schubert?" | E |
| Decision policy | Contradiction never detected | — | 0 | No conflicting chunks surfaced together | D |
| Decision policy | High latency in recovery | 1, 12 | 2 | 252 s and 41 s vs 29 s average | I |
| Benchmark | Text corruption in stored questions | 10, 12, 15, 18, 22 | 5 | "ti" → "z" (PDF extraction) | Step 2 |
| Benchmark | Wrong or unreachable gold label | 1, 6, 17, 18 | 4 | Q1 labelled abstain but answerable; Q6, Q17 labelled answer but no supporting chunk; Q18 gold not in corpus | Step 2 |
| (cross-cutting) | Temporal reasoning needed | 1, 2, 20 | 3 | Answer depends on dates or periods | C, Step 2 |

## Motivation for our improvement focus (to decide at Q&A 3, 26 Nov)

The shared retrieval artifacts stay unchanged for all groups, so re-chunking is out of scope. Improvements target retrieval, generation or the decision policy.

- **Track A, confidence calibration.** The clearest measurable gap: ECE 0.47, and confidence drives no decision. Idea: make confidence predict correctness (retrieval and rerank scores, agreement across modes, an answer-completeness check), then use it for the answer/abstain threshold.
- **Track B / F, false abstention and retrieval.** The biggest correctness gap. Idea: cross-encoder rerank of a larger candidate pool (top 50–100) before generation, plus a check before final abstention.
- **Track E, clarification.** Only 4 cases, so a measurable improvement is hard to show on this benchmark alone.

All tracks depend on a clean benchmark, so our Step 2 cases avoid the label problems above.
