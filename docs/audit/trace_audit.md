# Trace audit: 25 benchmark questions (DRAFT)

**Source:** reference team's run `reference/results/agentic/` (traces, `answers.json`, LLM-judged verdicts in `evaluation_metrics.json`). "Expected" is their label from `reference/Baseline/benchmark/reliability_labels.json`. Regenerate with `python -m src.ours.traces.audit_traces`.

**Headline:** the system is faithful but not reliable. All 20 answers passed the verifier (mean grounding 0.985), but only 3 are fully correct (11 partial, 6 incorrect). Confidence averages about 0.9 for right and wrong answers alike (ECE 0.47), and 6 of 25 questions end in the wrong action (Q1, Q3, Q5, Q7, Q18, Q23).

| Q | Question (short) | Expected | Actual | Verdict | Conf. | Recoveries | Latency (s) |
|---|---|---|---|---|---|---|---|
| 1 | ETH president in 2003 | abstain (should be answer) | abstain | — | 0.00 | 2 | 252 |
| 2 | Rectors 2017–2022 | answer | answer | partial | 0.89 | 0 | 25 |
| 3 | ERC grant recipients | clarify | answer | partial | 0.86 | 0 | 17 |
| 4 | InSight on Mars | answer | answer | correct | 0.94 | 1 | 21 |
| 5 | Prof. Schubert on flying | answer | clarify | — | 0.00 | 0 | 5 |
| 6 | What is e-Sling | abstain (label says answer) | abstain | — | 0.00 | 2 | 22 |
| 7 | Famous ETH alumni | clarify | answer | partial | 0.92 | 0 | 14 |
| 8 | Climate-change researchers | answer | answer | partial | 0.90 | 0 | 19 |
| 9 | Alpine plants & climate | answer | answer | partial | 0.95 | 0 | 15 |
| 10 | Fertilizer without CO₂ * | answer | answer | incorrect | 0.84 | 1 | 29 |
| 11 | What ETH is famous for | answer | answer | incorrect | 0.92 | 0 | 20 |
| 12 | Electricity used by computing * | answer | answer | incorrect | 0.88 | 2 | 41 |
| 13 | Pseudocereals | answer | answer | partial | 0.91 | 1 | 23 |
| 14 | Targeted cancer treatment | answer | answer | incorrect | 0.78 | 0 | 14 |
| 15 | Avoiding diarrhea * | answer | answer | partial | 0.85 | 0 | 16 |
| 16 | What is ETH Plus | answer | answer | partial | 0.90 | 0 | 12 |
| 17 | Birds learning songs | abstain (label says answer) | abstain | — | 0.00 | 2 | 21 |
| 18 | Connections to Hong Kong * | answer | abstain | — | 0.00 | 2 | 19 |
| 19 | Years of quantum research | answer | answer | incorrect | 0.89 | 1 | 23 |
| 20 | Student number projections | answer | answer | incorrect | 0.91 | 1 | 22 |
| 21 | Why study at ETH | answer | answer | partial | 0.93 | 0 | 17 |
| 22 | Tibet 2016 events * | answer | answer | correct | 0.87 | 0 | 17 |
| 23 | Why more ETH funding | clarify | answer | partial | 0.91 | 1 | 28 |
| 24 | Work for people with disabilities | answer | answer | correct | 0.89 | 0 | 17 |
| 25 | ETH competitions | answer | answer | partial | 0.86 | 0 | 9 |

\* The stored question contains a PDF-extraction typo: "ti" became "z" ("ferzlizer", "consumpzon", "inveszgazng", "conneczons", "inveszgated").

## Observations

- **Confidence is uninformative.** Correct answers average 0.90, incorrect 0.87. Confidence is computed after the action is chosen and drives no decision.
- **Abstentions must be judged against the indexed chunks.** All four abstentions (Q1, Q6, Q17, Q18) came from the generator reporting "not in the evidence" three times. Checked against `docs_fixed_norm.pkl`: **Q1 is a false abstention** (the answer is in chunk `8a6b1a87…_fixed_1`), **Q18 is a partial one** (4 chunks mention Hong Kong, e.g. a professor appointed from the Hong Kong Institute of Education), and **Q6 and Q17 are correct abstentions**: no chunk (and no raw page) mentions e-Sling or bird song learning, so their gold labels are wrong.
- **The index is missing much of the corpus:** 37% of pages are not indexed and 92% of indexed pages lose their lead paragraph. See [`index_coverage.md`](index_coverage.md).
- **Clarification misfires both ways.** Q5 asked "which Schubert?" although the answer exists. Q3, Q7 and Q23 were labelled clarify but answered.
- **Some "answers" are non-answers.** Q10, Q12 and Q20 count as grounded answers but mostly say the evidence doesn't cover the question. For Q12 and Q20 that is true: the gold facts (13,500 t CO₂ / 40 GWh; ~3.5 % more students per year) are in no indexed chunk and no raw page, so the right action was to abstain and the gold answers are unreachable (benchmark issue). Either way, a non-answer filed as ANSWER at confidence 0.88–0.91 inflates answer coverage.
- **The verifier never rejected a draft**, so the critique-and-revise path was never exercised.
- **Latency spikes in recovery:** Q1's second retrieval step alone took about 227 s (average 29 s).
- **Only English questions were run;** the German versions (`question_de`) are unused.
- **The sufficiency gate barely acts:** sufficiency fell below 0.40 once (Q5, 0.37), and every abstention came from the generator flag instead. The sufficiency embedding model (MiniLM) is English-only.
