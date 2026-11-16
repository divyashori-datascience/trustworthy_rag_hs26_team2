# Trace audit: 25 benchmark questions (DRAFT)

**Source:** reference team's run `reference/results/agentic/` (traces, `answers.json`, LLM-judged verdicts in `evaluation_metrics.json`). "Expected" is their label from `reference/Baseline/benchmark/reliability_labels.json`. Regenerate with `python -m src.ours.traces.audit_traces`.

**Headline:** the system is faithful but not reliable. All 20 answers passed the verifier (mean grounding 0.985), but only 3 are fully correct (11 partial, 6 incorrect). Confidence averages about 0.9 for right and wrong answers alike (ECE 0.47), and 7–9 of 25 questions end in the wrong action, depending on two disputed labels.

| Q | Question (short) | Expected | Actual | Verdict | Conf. | Recoveries | Latency (s) |
|---|---|---|---|---|---|---|---|
| 1 | ETH president in 2003 | abstain (should be answer) | abstain | — | 0.00 | 2 | 252 |
| 2 | Rectors 2017–2022 | answer | answer | partial | 0.89 | 0 | 25 |
| 3 | ERC grant recipients | clarify | answer | partial | 0.86 | 0 | 17 |
| 4 | InSight on Mars | answer | answer | correct | 0.94 | 1 | 21 |
| 5 | Prof. Schubert on flying | answer | clarify | — | 0.00 | 0 | 5 |
| 6 | What is e-Sling | answer (disputed) | abstain | — | 0.00 | 2 | 22 |
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
| 17 | Birds learning songs | answer (disputed) | abstain | — | 0.00 | 2 | 21 |
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
- **Abstentions need a corpus check, not a qrels check.** All four abstentions (Q1, Q6, Q17, Q18) came from the generator reporting "not in the evidence" three times. Q1 is a confirmed false abstention (see `case_Q1.md`) and Q18 a partial one (`case_Q18.md`). For Q6 (e-Sling) and Q17 (bird song learning), a keyword search of the raw HTML finds no supporting text, so those abstentions may be *correct*. **To verify** in the indexed chunks (`Lang_norm/fixed_size_chunk/docs_fixed_norm.pkl`).
- **Clarification misfires both ways.** Q5 asked "which Schubert?" although the answer exists. Q3, Q7 and Q23 were labelled clarify but answered.
- **Some "answers" are non-answers.** Q10, Q12 and Q20 count as grounded answers but mostly say the evidence doesn't cover the question, while the gold answers show it does. This inflates answer coverage.
- **The verifier never rejected a draft**, so the critique-and-revise path was never exercised.
- **Latency spikes in recovery:** Q1's second retrieval step alone took about 227 s (average 29 s).
- **Only English questions were run;** the German versions (`question_de`) are unused.
- **The sufficiency gate barely acts:** sufficiency fell below 0.40 once (Q5, 0.37), and every abstention came from the generator flag instead. The sufficiency embedding model (MiniLM) is English-only.
