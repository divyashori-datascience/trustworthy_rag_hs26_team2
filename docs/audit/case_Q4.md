# Diagnostic case: Q4 "When did the InSight get to Mars?" (DRAFT)

**Expected behaviour:** ANSWER. Gold: 26 November 2018.
**Trace:** `reference/results/agentic/traces/4.json` (our run: `My Drive/AdvGenAI/runs/20261117_1540/traces/4.json`)

## What the system did

| Step | Signal / action | Reason in trace |
|---|---|---|
| Profile | type=entity, ambiguous=false, entities=[insight, mars] | entity → BM25 first |
| Retrieve (BM25) | 8 chunks, sufficiency 0.52 | sufficiency ≥ 0.40 → generate |
| Generate | `evidence_found=false`, no citations | generator reports evidence does not contain the answer; recovering |
| Recover | rewritten: "when did the InSight lander arrive on Mars OR …"; BM25 → voting | |
| Retrieve (voting) | 8 chunks, sufficiency 0.84 | → generate |
| Generate | `evidence_found=true`, 2 chunks cited | → verify |
| Verify | grounded, score 1.00, 0 unsupported claims | grounded → answer |
| **Final** | **ANSWER**, confidence 0.94, 20.8 s | |

**Answer:** NASA's InSight spacecraft landed on Mars on 26 November 2018. Matches gold; judged *correct*.

## Diagnosis

1. **Sufficient evidence?** Not at first. The Step 1 failure report puts the 2 gold chunks at ranks 6 and 9 for the baseline, outside the top 5 the generator sees. After recovery, yes.
2. **Grounded?** Yes (1.00).
3. **Correct?** Yes.
4. **Right action?** RECOVER → ANSWER, which is what happened.
5. **Failure mode:** initial ranking failure, fixed by recovery (query rewrite + mode switch).
6. **Best metric:** recovery success rate; answer correctness.

## Takeaway

This is recovery working as designed. It also shows that sufficiency 0.52 was not a reliable sign the answer was present, and that evidence just outside the top 5 is common, which is an argument for reranking a larger candidate pool.

## Reproduced in our run (17 Nov 2026)

Same action (ANSWER) and same answer ("landed on the Martian surface in November 2018"), confidence 0.94, 27.9 s. Again BM25 first, then recovery to voting. See [`reproduction_note.md`](reproduction_note.md).
