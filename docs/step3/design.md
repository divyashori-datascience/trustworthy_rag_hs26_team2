# Step 3: Calibrated confidence + abstention gate (Track A)

Group 2 · prepared for Q&A on 3 December 2026 · code: [`src/ours/improvement/`](../../src/ours/improvement) · runs: [`notebooks/02_step3_runs.ipynb`](../../notebooks/02_step3_runs.ipynb)

## 1. Bottleneck

The reference system's confidence doesn't tell good answers from bad ones (Step 1, reference run): mean confidence 0.89 against graded correctness 0.425 (ECE 0.47); correct answers average 0.90 and incorrect ones 0.87. The score is `0.4·sufficiency + 0.4·grounding + 0.2·(1 − contradiction)`. Grounding is about 1.0 for almost every answer, and no decision ever uses the score. Answers that say *"the evidence does not contain …"* still go out as ANSWER with confidence 0.91 (Q20).

## 2. Mechanism

A **post-hoc calibrator** on top of the unchanged reference system (same index, retrievers, prompts and policy), plus an **abstention gate**:

1. **Features from the decision trace** ([`features.py`](../../src/ours/improvement/features.py)). No extra model calls.

   | Group | Features |
   |---|---|
   | G0 | the reference confidence |
   | G1 | existing signals: sufficiency, chunk agreement, grounding, contradiction, number of unsupported claims |
   | G2 | process: retrieval rounds, recoveries, mode changes, generator "no evidence" rounds, sufficiency first and gain, ambiguity flag, language, latency |
   | G3 | answer text: hedge / non-answer phrases, answer length, number of citations |

2. **Calibrator** ([`calibrate.py`](../../src/ours/improvement/calibrate.py)): logistic regression on standardised features. It predicts *P(the answer is acceptable and correct)*, trained on graded outcomes (correct 1, partial 0.5, incorrect 0). An answer the benchmark does not accept at all, e.g. one given to an abstain or clarify case, counts as 0. Simple baselines for comparison: Platt and isotonic on the reference confidence alone.

3. **Gate**: if the calibrated confidence is below τ, return ABSTAIN instead of the answer. τ is chosen to maximise the end-to-end reliability score on the training fold.

4. **Validation**: leave-one-question-out, with folds grouped by question across all runs. Every number on a question comes from a model and a τ fitted without that question.

## 3. Data and tuning rule

| Set | Use |
|---|---|
| Development benchmark, 80 questions (instructor, 27 Nov) | fit, tune and evaluate, leave-one-question-out. 16 ABSTAIN cases, 7 ABSTAIN-or-ANSWER, 7 CLARIFY |
| Original 25 questions, **original labels unchanged** | fit, and report separately. 21/25 expect ANSWER, so the gate can only lose here |
| Held-out test set, 43 questions | not used until the final evaluation |

The system only receives the question text, with no labels or notes. 5 of the 80 dev questions are ours (G02-001, 002, 006, 007, 009): we report results with and without them and disclose the author exposure.

## 4. Target metrics

| Metric | What it shows | Baseline (reference run) | Target |
|---|---|---|---|
| ECE ↓ | is the score honest? | 0.47 (0.54 counting answered clarify cases as wrong) | < 0.15 |
| AUROC ↑ | does a higher score mean a better answer? | 0.53 | > 0.75 |
| AURC ↓ | risk across all coverage levels | 0.59 (0.51 with the reference team's scoring) | clearly lower |
| Unsafe answers / run ↓ | answers where the benchmark expects ABSTAIN / CLARIFY | dev: to measure | fewer |
| Good answers withheld | cost of the gate | — | small |
| Reliability score ↑ | end-to-end value per question | dev: to measure | higher than as-is |
| Run-to-run agreement | stability (Step 1: 21/25) | — | report |

## 5. Ablation

| Step | Configuration | Question it answers |
|---|---|---|
| A0 | reference system as is | baseline |
| A1 | reference confidence + gate | does a threshold alone help? |
| A2 | Platt / isotonic on the reference confidence | is re-scaling enough? |
| A3 | LR on G0+G1 | do the existing signals carry more? |
| A4 | + G2 process signals | does *how* the system got there help? |
| A5 | + G3 answer-text signals (full) | does detecting non-answers help? |
| A6 | full calibrator, no gate | calibration benefit without changing actions |

Each configuration is evaluated over 3 runs.

## 6. Progress (27 Nov)

- **Done:** feature extraction, calibrators, leave-one-question-out evaluation with in-fold τ, all metrics and plots, development-benchmark loader, and a resume-safe Colab notebook for 3 × (80 + 25) runs plus grading. The pipeline was tested end to end, and with a mock system for the dev path.
- **Preliminary result** (reference team's single judged run, 20 answers, original labels; [`results/step3_preliminary/`](../../results/step3_preliminary/step3_results.md)):

  | Method | ECE | Brier | AUROC | AURC |
  |---|---|---|---|---|
  | reference confidence | 0.54 | 0.415 | 0.53 | 0.59 |
  | LR on existing signals (G0+G1) | 0.19 | 0.163 | 0.45 | 0.68 |
  | full calibrator (G0–G3) | **0.12** | **0.086** | **0.96** | **0.46** |

  In this run all 3 fully correct answers contain no hedge phrase, and every incorrect one has at least two.
- **Caveat:** these are 20 answers, and the hedge list was written after seeing the Step 1 failures. The dev runs are the real test.
- **Next:** 3 runs on dev + original in Colab (about $11, about 70 min), then the results and ablation table.

## 7. Trade-offs and risks

- **Coverage vs risk:** every unsafe answer the gate removes can cost a good answer. We report both (*unsafe answers*, *good answers withheld*) and the full coverage–risk curve.
- **Original labels:** on the original 25 questions any extra abstention scores as wrong. We report them separately and don't tune for them.
- **Small data:** about 80 questions × 3 runs, and runs of the same question are not independent, hence grouped folds. We keep the model small: logistic regression, about 19 features.
- **Judge noise:** correctness comes from the reference LLM judge prompt. We hand-check a sample of verdicts.
- **Hedge features can be gamed:** an answer can be wrong without hedging. That is why G3 is one group in the ablation, not the whole mechanism.
- **The gate abstains; it does not repair:** answer quality itself doesn't improve.
