# Diagnostic case: Q1 "Who was president of ETH in 2003?" (DRAFT)

**Expected behaviour:** ANSWER (Olaf Kübler). The reference labels say ABSTAIN; we think that label is wrong.
**Trace:** `reference/results/agentic/traces/1.json` (our run: `My Drive/AdvGenAI/runs/20261117_1540/traces/1.json`)

## What the system did

| Step | Signal / action | Reason in trace |
|---|---|---|
| Profile | type=entity, entities=[eth, president, 2003] | → BM25 |
| Retrieve (BM25) | sufficiency 0.60 | → generate |
| Generate | `evidence_found=false` | recovering |
| Recover | "president of ETH Zurich 2003 OR president of Swiss Federal Institute of …"; → voting | |
| Retrieve (voting) | sufficiency 0.83; this step took about 227 s | → generate |
| Generate | `evidence_found=false` | recovering |
| Recover | → GraphRAG | |
| Retrieve (GraphRAG) | sufficiency 0.74 | → generate |
| Generate | `evidence_found=false` | generator found no supporting evidence → abstain |
| **Final** | **ABSTAIN**, confidence 0.00, 251.9 s | |

## Diagnosis

1. **Sufficient evidence?** The retrieved chunks were not enough, but the corpus contains the answer. `en_news_events/2021/07/lord-of-the-flies-data-and-seven-bycicles.html` says ETH was looking for a successor to Olaf Kübler, "due to step down as ETH President at the end of 2004", and that Ernst Hafen took office on 1 January 2005. The sentence is in the **indexed** chunk `8a6b1a87620aeaf61ffe85717e3aa380c6c66cfc_fixed_1`, so the system could have retrieved it. Check with `fill_chunk_ids.py --find "Olaf Kübler"`.
2. **Grounded?** n/a (no answer).
3. **Correct?** No. The gold answer is Olaf Kübler.
4. **Right action?** ANSWER, with a short note that it is inferred from the date he stepped down.
5. **Failure modes:** false abstention; retrieval failure across all three modes; **temporal reasoning** needed (2003 is inside his term but never stated); high latency in recovery; **benchmark label error**.
6. **Best metric:** false-abstention rate; benchmark label validity.

## Why the label is wrong

`reliability_labels.json` marks a question unanswerable when it has 0 gold chunks in the qrels. The qrels are relevance scores from gpt-4o-mini (≥ 0.5), produced by `2_1_2_relevance_score.py` in the original pipeline. They missed this chunk, so the reference evaluation counted a false abstention as a correct one.

## Takeaway

Abstentions must be checked against the corpus, not against what retrieval or the qrels found. This affects both the evaluation (Step 4) and how we build our benchmark (Step 2).

## Reproduced in our run (17 Nov 2026)

Same action (ABSTAIN) after BM25 → voting → GraphRAG, 63.3 s (the earlier 252 s spike did not recur). The German version ("Wer war 2003 Präsident der ETH Zürich?") also abstains (11.3 s). The false abstention is therefore stable, not run-to-run noise. See [`reproduction_note.md`](reproduction_note.md).
