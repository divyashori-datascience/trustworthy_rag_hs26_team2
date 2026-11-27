# Step 3 results (1 run(s), leave-one-question-out, 95% bootstrap CIs over questions)

## original benchmark (original labels, unchanged)

| Configuration | ECE ↓ | AUROC ↑ | AURC ↓ | Reliability score ↑ | Unsafe answers / run ↓ | Good answers withheld / run | Answered |
|---|---|---|---|---|---|---|---|
| A0 · as is (no gate) | – | – | – | 0.32 [0.18, 0.46] | 3 | – | 0.8 |
| A1 · reference confidence + gate | 0.54 [0.39, 0.68] | 0.529 [0.17, 1] | 0.593 [0.4, 0.8] | 0.32 [0.18, 0.46] | 3 | 0 | 0.8 |
| A2 · Platt + gate | 0.153 [0.072, 0.3] | 0.196 [0, 0.5] | 0.73 [0.57, 0.88] | 0.32 [0.18, 0.46] | 3 | 0 | 0.8 |
| A2 · isotonic + gate | 0.224 [0.11, 0.36] | 0.402 [0.056, 0.94] | 0.655 [0.48, 0.86] | 0.32 [0.18, 0.46] | 3 | 0 | 0.8 |
| A3 · LR existing signals + gate | 0.193 [0.093, 0.34] | 0.451 [0.15, 0.78] | 0.684 [0.5, 0.84] | 0.32 [0.18, 0.46] | 3 | 0 | 0.8 |
| A4 · + process signals | 0.236 [0.15, 0.4] | 0.431 [0.1, 0.72] | 0.656 [0.5, 0.83] | 0.32 [0.18, 0.46] | 3 | 0 | 0.8 |
| A5 · + answer-text (hedge list) | 0.126 [0.072, 0.26] | 0.941 [0.81, 1] | 0.509 [0.25, 0.75] | 0.32 [0.18, 0.46] | 3 | 0 | 0.8 |

**Paired differences, A5 · + answer-text (hedge list)** (95% CI; an interval that excludes 0 is a clear effect):
- vs A1 (same gate, reference confidence): ECE [-0.555, -0.186], AUROC [-0.053, 0.813], AURC [-0.326, 0.124], reliability score [0.0, 0.0]
- vs A0 (system as is): reliability score [0.0, 0.0], unsafe answers / run [0.0, 0.0]

Run-to-run action agreement: {'original': 1.0}