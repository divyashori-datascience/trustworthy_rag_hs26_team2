# Step 3 results (1 run(s), leave-one-question-out)

## original benchmark (original labels, unchanged)

| Method | ECE ↓ | Brier ↓ | AUROC ↑ | AURC ↓ | Reliability score ↑ | Action accuracy ↑ | Answered | Unsafe answers / run ↓ | Good answers withheld |
|---|---|---|---|---|---|---|---|---|---|
| as is (no gate) | – | – | – | – | 0.32 | 0.72 | 0.8 | 3.0 | – |
| baseline + gate | 0.54 | 0.415 | 0.529 | 0.593 | 0.32 | 0.72 | 0.8 | 3.0 | 0 |
| platt + gate | 0.153 | 0.144 | 0.196 | 0.73 | 0.32 | 0.72 | 0.8 | 3.0 | 0 |
| isotonic + gate | 0.224 | 0.144 | 0.402 | 0.655 | 0.32 | 0.72 | 0.8 | 3.0 | 0 |
| lr_G1 + gate | 0.193 | 0.163 | 0.451 | 0.684 | 0.32 | 0.72 | 0.8 | 3.0 | 0 |
| lr_G2 + gate | 0.229 | 0.168 | 0.451 | 0.646 | 0.32 | 0.72 | 0.8 | 3.0 | 0 |
| lr_G3 + gate | 0.117 | 0.086 | 0.961 | 0.459 | 0.32 | 0.72 | 0.8 | 3.0 | 0 |

Run-to-run action agreement: {'original': 1.0}