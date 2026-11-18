# Step 2: Benchmark contribution, group G02 (DRAFT)

**Benchmark draft and coverage gaps:** Divya Shori · **Validation:** Hanieh Jebeli (G02-006 to G02-014), Faranak Rahimi (G02-001 to G02-005)

> **Status: draft.** 14 candidate cases are in [`benchmark/G02_benchmark_draft.xlsx`](../../benchmark/G02_benchmark_draft.xlsx); we submit **10**. Every case is marked *Draft* and must be checked by a second group member before it can be marked *Self-validated*. **Deadline: Mon 23 Nov 2026, 09:00** (one Excel per group). Confirm our group ID; `G02` is assumed from the repo name.

## Coverage

| # | Case | Category | Expected action → outcome | Evidence chunk |
|---|---|---|---|---|
| 1 | EPFL President successor: start date, who appoints | Standard factual | ANSWER | `06fcc05a…_fixed_0` |
| 2 | Who runs the Swiss Data Science Center, since when | Standard factual | ANSWER | `8adacd9a…_fixed_0`, `f41da84c…_fixed_1` |
| 3 | Gene variant E756del and malaria | Difficult retrieval | ANSWER | `084aa327…_fixed_0` |
| 4 | When tuition fees were last adjusted before 2017 (2004) | Temporal | ANSWER | `6df21a18…_fixed_0` |
| 5 | ETH President in mid-2013 vs 2016 | Temporal | ANSWER | `dd06ade4…_fixed_0`, `e38adeed…_fixed_0` |
| 6 | QS rank: 12th (2013) vs 7th (2018, QS 2024) | Conflicting evidence | ANSWER (flag conflict) | `add82cd3…_fixed_7`, `2685b452…_fixed_0`, `a39f97e3…_fixed_1` |
| 7 | Acceptance rate, MSc Data Science 2023 | Insufficient evidence | ABSTAIN | none (search log) |
| 8 | International tuition fees from autumn 2025 | Insufficient evidence | ABSTAIN | none (search log) |
| 9 | "Why did Fixposition focus on driverless cars first?" (it chose drones) | Adversarial / false premise | ANSWER (correct the premise) | `953665ea…_fixed_0` |
| 10 | "2019 ETH study on 5G killing bees" (no such study) | Adversarial / false premise | ABSTAIN | none (search log) |
| 11 | District heating sale: price and transfer date (DE-only evidence) | Multilingual | ANSWER | `909f5028…_fixed_0` |
| 12 | DE/EN code-switched question: Fixposition's market estimate | Multilingual / code-switch | ANSWER | `953665ea…_fixed_0` |
| 13 | "What did the President say at ETH Day?" (6 years, 3 presidents) | Ambiguous | CLARIFY | 4 chunks |
| 14 | "Who won the Rossler Prize in 2013?" (umlaut missing) | Recovery-triggering | RECOVER → ANSWER | `dd06ade4…_fixed_0` |

All 9 categories are covered (the minimum is 4), with 2 standard factual cases (the minimum is 2).

## Course guidelines (17 Nov) and how we meet them

| Guideline | Our cases |
|---|---|
| Answerable questions: evidence must exist in the shared indexed chunks | Every answerable case cites chunk IDs that contain the answer (checked with `fill_chunk_ids.py --verify`) |
| Difficult retrieval: evidence in the index but hard to retrieve | G02-003: the answer is a side detail in an indexed chunk |
| Insufficient evidence: abstention justified by the indexed corpus, not a failed retrieval | G02-007, G02-008, G02-010: searched all 7,531 chunks (and the raw HTML); search logs in the workbook |
| Facts only in the original HTML: document separately, not in the 10 | Listed in [`coverage_gaps.md`](coverage_gaps.md) (7 gaps) |

## Design choices

- **Grounded in the shared index, not only the raw pages.** The system can only answer from `docs_fixed_norm.pkl`, which misses 37% of pages and the lead paragraph of 92% of indexed pages ([audit finding](../audit/index_coverage.md)). Every answerable case cites a chunk ID that contains the answer, checked automatically and by eye. Our first draft used facts from article leads that turned out not to be indexed, so those cases were replaced.
- **Abstention cases document a search of all chunks and all raw pages**, not a failed top-k retrieval (template requirement). The search terms and hit counts are in the evidence column.
- **Two kinds of false premise:** one *contradicted* by the corpus (correct behaviour: answer by correcting the premise) and one *unsupported* (correct behaviour: abstain without inventing a study).
- **Temporal cases need reasoning across dates** (a relative span anchored to a year; the office holder changing between documents), not a plain lookup.
- **Multilingual cases:** one English question whose only evidence is a German chunk, and one code-switched DE/EN question with English evidence.
- **No overlap with the reference benchmark** (Q1–25, R1–R15): no "current president", "president in 2003", "student numbers" or "Hong Kong" questions.
- **One family per underlying fact.** Cases sharing a source chunk but testing different facts (9 and 12; 5 and 14) are separate families, linked via *Related case ID(s)*.

## Validation still to do (per case)

1. Re-read the evidence chunk: `python -m src.ours.benchmark.fill_chunk_ids --pkl <path>/docs_fixed_norm.pkl --verify benchmark/G02_benchmark_draft.xlsx`. Does it support the expected answer exactly?
2. For ABSTAIN cases, repeat the search with your own terms: `--find "<term>"` on the chunks and `python -m src.ours.traces.search_corpus --zip <path>/HKNews.zip "<term>"` on the raw pages.
3. Check that the question isn't trivial, a duplicate, or a paraphrase of another case.
4. Set *Group validation status* to **Self-validated** only after steps 1–3. Record who validated it in *Additional notes*.
5. Pick the final 10, keeping at least 2 standard factual and at least 4 categories.

Authoring method is recorded honestly as *LLM-assisted* in the workbook; the validation above has to be done by us.
