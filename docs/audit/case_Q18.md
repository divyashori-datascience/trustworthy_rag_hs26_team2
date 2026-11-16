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

1. **Sufficient evidence?** Not in the retrieved chunks. 13 corpus pages mention Hong Kong (`search_corpus.py "Hong Kong" "Hongkong"`), and a few show real but weak links:
    - ETH architects co-curated the Shenzhen–Hong Kong Bi-City Biennale (2015 annual review, German page only)
    - A professor appointed from the Hong Kong Institute of Education (2016)
    - An ETH spin-off's tour of China, including Hong Kong (2018)
2. **Grounded?** n/a.
3. **Correct?** The gold answer (CUHK and HKUST agreements) can't be reached from this corpus.
4. **Right action?** ANSWER with the corpus-supported connections, stating that formal partnerships are not covered. Abstaining throws away real evidence.
5. **Failure modes:** retrieval failure across modes; query typo; relevant evidence only in German; gold answer from outside the corpus.
6. **Best metric:** false-abstention rate; benchmark validity (is every gold answer corpus-grounded?).

## Takeaway

The benchmark itself needs auditing. For our Step 2 contribution, every expected answer must cite a passage that actually exists in the corpus.
