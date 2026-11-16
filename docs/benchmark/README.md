# Step 2: Benchmark contribution, group G02 (DRAFT)

> **Status: draft.** 14 candidate cases are in [`benchmark/G02_benchmark_draft.xlsx`](../../benchmark/G02_benchmark_draft.xlsx); we submit **10**. Every case is marked *Draft* and must be checked by a second group member before it can be marked *Self-validated*. **Deadline: Mon 23 Nov 2026, 09:00** (one Excel per group). Confirm our group ID; `G02` is assumed from the repo name.

## Coverage

| # | Case | Category | Expected action → outcome |
|---|---|---|---|
| 1 | Chemistry Olympiad 2023: participants and venue | Standard factual | ANSWER |
| 2 | Mechanism that makes tendons stiffer | Standard factual | ANSWER |
| 3 | Gene variant E756del and malaria | Difficult retrieval | ANSWER |
| 4 | Tuition fee from autumn 2020/21 (1,160 + 2 × 250) | Temporal | ANSWER |
| 5 | ETH President at ETH Day 2014 vs early 2015 | Temporal | ANSWER |
| 6 | Number of Nobel laureates (21 in 2013 vs 22 in 2023) | Conflicting evidence | ANSWER (flag conflict) |
| 7 | Acceptance rate, MSc Data Science 2023 | Insufficient evidence | ABSTAIN |
| 8 | International tuition fees from autumn 2025 | Insufficient evidence | ABSTAIN |
| 9 | "Why did Mesot propose raising fees?" (he opposed it) | Adversarial / false premise | ANSWER (correct the premise) |
| 10 | "2019 ETH study on 5G killing bees" (no such study) | Adversarial / false premise | ABSTAIN |
| 11 | District heating: buildings supplied, transfer date (DE-only evidence) | Multilingual | ANSWER |
| 12 | DE/EN code-switched question about Fixposition | Multilingual / code-switch | ANSWER |
| 13 | "What did the President say at ETH Day?" (several years and presidents) | Ambiguous | CLARIFY |
| 14 | "When was the SDSC founded?" (acronym mismatch) | Recovery-triggering | RECOVER → ANSWER |

All 9 categories are covered (the minimum is 4), with 2 standard factual cases (the minimum is 2).

## Design choices

- **Every gold answer is corpus-grounded.** Our audit found reference gold answers that aren't in the corpus (Q6, Q17, Q18) and a label derived from incomplete qrels (Q1). Each of our answerable cases cites the exact page and passage.
- **Abstention cases document a full-corpus search**, not a failed top-k retrieval (template requirement). The search terms and hit counts are in the evidence column.
- **Two kinds of false premise:** one *contradicted* by the corpus (correct behaviour: answer by correcting the premise) and one *unsupported* (correct behaviour: abstain without inventing a study).
- **Temporal cases need reasoning across dates** (a sum of dated increases; a role change between two documents), not a lookup.
- **Multilingual cases use evidence that exists only in German**, which exercises the bilingual retrieval path; one question is code-switched.
- **No overlap with the reference benchmark** (Q1–25, R1–R15): no "current president", "student numbers", "Hong Kong" or "research ETH is famous for" questions.
- **One family per underlying fact.** Cases 2 and 3 share a source article but test different facts, so they are separate families, linked via *Related case ID(s)*.

## Validation still to do (per case)

1. Re-read the source page in the corpus: does the passage support the expected answer exactly?
2. Fill the chunk ID: `python -m src.ours.benchmark.fill_chunk_ids --pkl <path>/docs_fixed_norm.pkl --xlsx benchmark/G02_benchmark_draft.xlsx`
3. For ABSTAIN cases, repeat the search with your own terms (`python -m src.ours.traces.search_corpus --zip <path>/HKNews.zip "<terms>"`).
4. Check that the question isn't trivial, a duplicate, or a paraphrase of another case.
5. Set *Group validation status* to **Self-validated** only after steps 1–4. Record who validated it in *Additional notes*.
6. Pick the final 10, keeping at least 2 standard factual and at least 4 categories.

Authoring method is recorded honestly as *LLM-assisted* in the workbook; the validation above has to be done by us.
