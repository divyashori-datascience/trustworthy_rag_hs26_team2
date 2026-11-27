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
   | G3 | answer text: hand-written hedge / non-answer phrases, answer length, number of citations |
   | G4 | **LLM self-check**: one Haiku call per answer, *"does this answer actually answer the question?"* (yes / partly / no). It sees only the question and the answer, never a gold answer, so it is a legitimate part of the mechanism at answer time |

   G2 also includes retrieval stability (overlap of the retrieved chunks between the first and last round) and the share of the final chunks the answer cites.

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
| A5 | + G3 answer-text signals (hand-written hedge list) | does detecting non-answers help? |
| A6 | + G4 LLM self-check (full mechanism) | does a learned "is this an answer?" check add to that? |
| A7 | full mechanism **without** the hand-written hedge list | does the result depend on phrases we picked after seeing Step 1? |

Calibration metrics (ECE, AUROC, AURC) of A2–A7 are the calibrator *without* the gate; the reliability score and unsafe answers show the effect *with* the gate. All numbers carry **95% bootstrap intervals over questions**, with all runs of a question resampled together. A6 is compared **pairwise** with A1 (same gate, reference confidence) and with A0 (system as is); an interval that excludes 0 counts as a clear effect. On the dev set we also break results down **by category**, to show where the gate helps (false premise, insufficient evidence) and what it costs (good answers withheld).

Each configuration is evaluated over 3 runs.

## 6. Progress (27 Nov)

- **Done:** feature extraction (G0–G4), calibrators, leave-one-question-out evaluation with in-fold τ, all metrics with bootstrap intervals, paired comparisons and the per-category breakdown, development-benchmark loader, LLM self-check, and a resume-safe Colab notebook for 3 × (80 + 25) runs plus self-check and grading. The pipeline was tested end to end on the reference run, and with a mock system for the dev path.
- **Preliminary result** (reference team's single judged run, 20 answers, original labels; [`results/step3_preliminary/`](../../results/step3_preliminary/step3_results.md)):

  | Method | ECE [95% CI] | AUROC [95% CI] | AURC [95% CI] |
  |---|---|---|---|
  | reference confidence | 0.54 [0.39, 0.68] | 0.53 [0.17, 1.0] | 0.59 [0.40, 0.80] |
  | LR on existing signals (G0+G1) | 0.19 [0.09, 0.34] | 0.45 [0.15, 0.78] | 0.68 [0.50, 0.84] |
  | + process + answer text (G0–G3) | **0.13 [0.07, 0.26]** | **0.94 [0.81, 1.0]** | **0.51 [0.25, 0.75]** |

  In this run all 3 fully correct answers contain no hedge phrase, and every incorrect one has at least two. The drop in ECE is clear (paired interval −0.56 to −0.19). The AUROC gain is not yet: its paired interval still includes 0 with only 20 answers. The self-check (G4) needs the new runs.
- **Caveat:** these are 20 answers, and the hedge list was written after seeing the Step 1 failures. This is why we added A7 (without the hedge list). The dev runs are the real test.
- **Next:** 3 runs on dev + original in Colab (about $11 plus well under $1 for the self-check, about 70 min), then the results and ablation table.

## 7. Trade-offs and risks

- **Coverage vs risk:** every unsafe answer the gate removes can cost a good answer. We report both (*unsafe answers*, *good answers withheld*) and the full coverage–risk curve.
- **Original labels:** on the original 25 questions any extra abstention scores as wrong. We report them separately and don't tune for them.
- **Small data:** about 80 questions × 3 runs, and runs of the same question are not independent, hence grouped folds. We keep the model small: logistic regression, about 19 features.
- **Judge noise:** correctness comes from the reference LLM judge prompt. We hand-check a sample of verdicts.
- **Hedge features can be gamed, and are tuned to what we saw:** an answer can be wrong without hedging. That is why G3 is one rung of the ablation, and A7 tests the mechanism without it.
- **Self-check cost and latency:** one extra Haiku call per answer, roughly $0.001 and about 1 s. We report it in the efficiency numbers.
- **The gate abstains; it does not repair:** answer quality itself doesn't improve.
