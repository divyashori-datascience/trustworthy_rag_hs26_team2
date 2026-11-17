# Finding: the shared index is missing a large part of the corpus (DRAFT)

**The reference system can only answer from the indexed chunks (`docs_fixed_norm.pkl`), and those chunks miss a large part of the raw corpus.** This is a root cause behind several false abstentions and partial answers, and it matters for how benchmark answers are labelled.

Reproduce: `python -m src.ours.traces.index_coverage --zip <path>/HKNews.zip --pkl <path>/docs_fixed_norm.pkl`

| Measure | Value |
|---|---|
| Raw pages in `HKNews.zip` (EN + DE) | 4,389 |
| Pages in the index | 2,761 (7,531 chunks) |
| Pages not indexed at all | 1,628 (37%) |
| Sentence coverage per indexed page | median 75%, mean 67% |
| Indexed pages with < 80% of their sentences in the chunks | 64% |
| Indexed pages whose **first sentence (the lead) is missing** | 92% |

Matching is approximate: lower-cased, umlauts transliterated, punctuation removed, and a sentence counts as present if its first 60 characters appear in the page's chunks.

## What goes missing

The chunks start at the page title followed by the **first sub-heading**. The lead paragraph(s) before it are dropped. On a news page, the lead usually holds the key facts, so the loss hurts more than the percentages suggest.

Examples checked by eye:

- **Tuition fees (2017-09):** the raw page's opening paragraph says "With 1160 Swiss francs per year … The ETH Board has now decided to raise the fees by CHF 500 per year", in two steps of CHF 250 (autumn 2019/2020 and 2020/2021). The only indexed chunk starts at "Top training at a still favourable price", so none of the amounts are retrievable.
- **55th Chemistry Olympiad (2023-07):** "around 350 talented young chemists from some 90 countries … Hönggerberg campus" is in the lead and not indexed.
- **QS ranking (2023-06, EN):** the lead says ETH "has moved up two positions to take seventh place". That sentence is not indexed. It only survives in a German article from September 2023.
- **Interview with Joël Mesot on tuition fees and reserves (2024-04, DE):** the page is not indexed at all.

## Consequences

1. **Some "false abstentions" are really indexing failures.** The answer exists in the corpus but not in any chunk, so no retriever or agent change can find it.
2. **Gold labels must be defined against the chunks.** Q6 (e-Sling) and Q17 (bird song learning) have no supporting chunk (and no supporting raw page), so their abstentions are *correct*. Q1 (Olaf Kübler) does have a supporting chunk (`8a6b1a87620aeaf61ffe85717e3aa380c6c66cfc_fixed_1`), so its abstention is a genuine false abstention.
3. **Our benchmark cases cite chunk IDs** and were checked against the chunks, not only the raw pages.
4. **Possible improvement direction** (not chosen yet): re-chunk with the lead included. This would change the shared artifacts, so we'd need to check with Guang whether it's in scope.
