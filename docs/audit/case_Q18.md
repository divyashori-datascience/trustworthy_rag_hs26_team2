# Diagnostic case: Q18 "What connections does ETH have to Hong Kong?" (DRAFT)

**Expected behaviour:** a partial ANSWER that states its limits (our view). The benchmark gold lists institutional agreements (CUHK, HKUST) that do not appear in the corpus.
**Trace:** `reference/results/agentic/traces/18.json` (our run: `My Drive/AdvGenAI/runs/20261117_1540/traces/18.json`)

## What the system did

| Step | Signal / action | Reason in trace |
|---|---|---|
| Query as stored | "what conneczons does eth have to hong kong?" | PDF extraction typo |
| Profile | type=list, entities=[eth zurich, hong kong] | → voting |
| Retrieve × 3 | voting → GraphRAG → confidence; chunks about Singapore, Korea, Africa | |
| Generate × 3 | `evidence_found=false`: "Hong Kong is not referenced" | recover, then abstain |
| **Final** | **ABSTAIN**, confidence 0.00, 19.3 s | |

## Diagnosis

1. **Sufficient evidence?** Not in the retrieved chunks. 13 raw pages mention Hong Kong, but only **6 indexed chunks** do (4 spelled "Hong Kong", 2 German chunks spelled "Hongkong"; `fill_chunk_ids.py --find "Hong Kong"` and `--find "Hongkong"`). The useful ones:
    - Manu Kapur appointed professor at ETH from the Hong Kong Institute of Education (`ede695ab…_fixed_2`)
    - Works from an internship described in an ETH News article were shown in Pors & Rao's presentation at Art Basel Hong Kong 2018 (`77b9fa3b…_fixed_1`)
    - Two ETH architects co-curated the biennale in Shenzhen and Hong Kong (2015 annual review, German only: `edc6ab28…_fixed_14`)
    - Fixposition's tour including Hong Kong is in the raw corpus but **not in the index** (a coverage gap)
2. **Grounded?** n/a.
3. **Correct?** The gold answer (CUHK and HKUST agreements) can't be reached from this corpus.
4. **Right action?** ANSWER with the corpus-supported connections, stating that formal partnerships are not covered. Abstaining throws away real evidence.
5. **Failure modes:** retrieval failure across modes; query typo; relevant evidence only in German; gold answer from outside the corpus.
6. **Best metric:** false-abstention rate; benchmark validity (is every gold answer corpus-grounded?).

## Takeaway

The benchmark itself needs auditing. For our Step 2 contribution, every expected answer must cite a passage that actually exists in the corpus.

## Reproduced in our run (17 Nov 2026)

Same action (ABSTAIN) after voting → GraphRAG → confidence, 31.0 s; the stored query still contains the typo "conneczons". See [`reproduction_note.md`](reproduction_note.md).
