# Diagnostic case: Q18 "What connections does ETH have to Hong Kong?" (DRAFT)

**Expected behaviour:** a partial ANSWER that states its limits (our view). The benchmark gold lists institutional agreements (CUHK, HKUST) that do not appear in the corpus.
**Trace:** `reference/results/agentic/traces/18.json` (re-check: `results/<our_run>/traces/18.json`)

## What the system did

| Step | Signal / action | Reason in trace |
|---|---|---|
| Query as stored | "what conneczons does eth have to hong kong?" | PDF extraction typo |
| Profile | type=list, entities=[eth zurich, hong kong] | → voting |
| Retrieve × 3 | voting → GraphRAG → confidence; chunks about Singapore, Korea, Africa | |
| Generate × 3 | `evidence_found=false`: "Hong Kong is not referenced" | recover, then abstain |
| **Final** | **ABSTAIN**, confidence 0.00, 19.3 s | |

## Diagnosis

1. **Sufficient evidence?** Not in the retrieved chunks. 13 raw pages mention Hong Kong, but only **4 indexed chunks** do (`fill_chunk_ids.py --find "Hong Kong"`). The useful ones:
    - Manu Kapur appointed professor at ETH from the Hong Kong Institute of Education (`ede695ab…_fixed_2`)
    - Works from an internship described in an ETH News article were shown in Pors & Rao's presentation at Art Basel Hong Kong 2018 (`77b9fa3b…_fixed_1`)
    - The Bi-City Biennale and Fixposition's Hong Kong tour are in the raw corpus but **not in the index**.
2. **Grounded?** n/a.
3. **Correct?** The gold answer (CUHK and HKUST agreements) can't be reached from this corpus.
4. **Right action?** ANSWER with the corpus-supported connections, stating that formal partnerships are not covered. Abstaining throws away real evidence.
5. **Failure modes:** retrieval failure across modes; query typo; relevant evidence only in German; gold answer from outside the corpus.
6. **Best metric:** false-abstention rate; benchmark validity (is every gold answer corpus-grounded?).

## Takeaway

The benchmark itself needs auditing. For our Step 2 contribution, every expected answer must cite a passage that actually exists in the corpus.
