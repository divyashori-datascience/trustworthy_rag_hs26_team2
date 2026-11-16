# Step 4 — Agentic System Evaluation

Run: `results\agentic\no_abstain`  |  questions: 25

## Action distribution
| action | n |
|---|---|
| answer | 24 |
| clarify | 1 |

## Behaviour vs. expected (reliability ground truth)
Confusion — rows = expected, cols = actual:

| expected \ actual | answer | abstain | clarify |
|---|---|---|---|
| answer | 20 | 0 | 1 |
| abstain | 1 | 0 | 0 |
| clarify | 3 | 0 | 0 |

- **Answer coverage on answerable**: 20/21 (rate 0.952)
- **Abstention**: 0 total — correct 0, false 0 (false-abstention rate None)
- **Clarification**: 1 total — correct 0, false 1

## Groundedness (answered questions)
- grounded-answer rate: **1.0** (grounding ≥ 0.6)
- mean grounding score: 0.985
- mean unsupported claims per answer: 0.0

## Adaptive recovery
- queries that triggered recovery: 10 (Q1, Q12, Q13, Q17, Q18, Q19, Q20, Q4, Q5, Q6)
- recovery success (ended in grounded answer): 10 (rate 1.0)

## Confidence by action
| action | n | mean confidence |
|---|---|---|
| answer | 24 | 0.881 |
| clarify | 1 | 0.0 |

## Retrieval quality vs. Step 1 baseline
| system | P@5 | Recall@5 | MRR |
|---|---|---|---|
| Step 1 baseline (Confidence) | 0.1167 | 0.0046 | 0.2045 |
| Agentic (final top-5) | 0.1333 | 0.0268 | 0.1813 |

_computed on the agentic system's FINAL retrieved top-5 (post-recovery)._

## Efficiency
- latency avg/max: 18.05s / 32.27s
- approx. LLM cost (run): $0.9742

## Plots
![confidence_by_action.png](confidence_by_action.png)