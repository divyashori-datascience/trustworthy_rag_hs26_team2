# Diagnostic case: Q<id>, <short title>

**Query:** …
**Expected behaviour (gold / our judgement):** ANSWER / ABSTAIN / CLARIFY / RECOVER, plus the gold answer if any
**Trace file:** `results/<run_id>/traces/<id>.json` (and/or the reference team's `reference/results/agentic/traces/<id>.json`)

## What the system did
| Step | Signal / action | Reason given in trace |
|---|---|---|
| Profile | type=…, ambiguous=… | |
| Retrieve (mode) | n chunks, sufficiency=… | |
| Decide | → … | |
| … | | |
| **Final** | **action**, confidence=… | |

**Final answer / clarification / abstain reason:** …

## Diagnosis (the six questions from the brief)
1. **Was the retrieved evidence sufficient?** Check the top chunks: does any of them contain the answer? Search the corpus to see whether it exists anywhere.
2. **Was the answer grounded in the evidence?**
3. **Was the answer factually correct?** Compare with the gold answer.
4. **Should the system have answered, abstained, clarified, or recovered?**
5. **Which failure mode occurred?** Use the taxonomy: retrieval failure · ranking failure · incomplete evidence · unsupported answer · false abstention · unnecessary/missed clarification · query-rewriting drift · weak calibration · failed recovery · contradiction not detected · poor trace interpretability · high latency/cost
6. **Which metric would best capture this behaviour?**

## Takeaway for our improvement focus
One or two sentences on which bottleneck this case points to.
