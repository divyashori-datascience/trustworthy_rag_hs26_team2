"""Calibrators and the abstention gate, evaluated leave-one-question-out.

Every prediction for a question comes from a model that never saw that question,
in any run (folds are grouped by question id across runs). The gate threshold is
also chosen inside each training fold, so no number is tuned on the row it scores.

Methods (the ablation ladder):
    baseline   the reference system's own confidence, unchanged
    platt      logistic regression on the baseline confidence only
    isotonic   isotonic regression on the baseline confidence only
    lr_G1      logistic regression on G0+G1 (existing signals)
    lr_G2      + G2 (process signals)
    lr_G3      + G3 (answer-text signals, hand-written hedge list)
    lr_G4      + G4 (LLM self-check)                      <- full mechanism
    lr_noHedge G0+G1+G2+G4, i.e. full mechanism WITHOUT the hand-written hedge list
"""
from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import columns

METHODS = ["baseline", "platt", "isotonic", "lr_G1", "lr_G2", "lr_G3", "lr_G4", "lr_noHedge"]
TAU_GRID = np.round(np.linspace(0.0, 1.0, 41), 3)


def _X(rows, cols):
    return np.array([[r["feats"][c] for c in cols] for r in rows], float)


def _fit_predict(method, train, test):
    if method == "baseline":
        return np.array([r["feats"]["base_conf"] for r in test], float)
    ytr = np.array([r["y"] for r in train], float)
    if method == "isotonic":
        iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        iso.fit([r["feats"]["base_conf"] for r in train], ytr)
        return iso.predict([r["feats"]["base_conf"] for r in test])
    cols = ["base_conf"] if method == "platt" else columns(method.split("_", 1)[1])
    Xtr = _X(train, cols)
    # graded labels: each row becomes a positive (weight y) and a negative (weight 1-y)
    X2 = np.vstack([Xtr, Xtr])
    y2 = np.r_[np.ones(len(ytr)), np.zeros(len(ytr))]
    w2 = np.r_[ytr, 1.0 - ytr]
    keep = w2 > 0
    if len(set(y2[keep])) < 2:          # degenerate fold: predict the base rate
        return np.full(len(test), float(ytr.mean()))
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))
    model.fit(X2[keep], y2[keep], logisticregression__sample_weight=w2[keep])
    return model.predict_proba(_X(test, cols))[:, 1]


def _best_tau(rows, p):
    """Threshold that maximises the mean end-to-end score on these answered rows."""
    sa = np.array([r["out"]["score_answer"] for r in rows])
    sb = np.array([r["out"]["score_abstain"] for r in rows])
    best, best_val = 0.0, -1.0
    for tau in TAU_GRID:
        val = np.where(p >= tau, sa, sb).mean()
        if val > best_val + 1e-12:
            best, best_val = float(tau), val
    return best


def loqo(rows: list[dict], method: str) -> dict:
    """Out-of-fold confidence and gate threshold for every ANSWERED row.

    rows: dicts with keys qid, feats, out (from outcomes.outcome), y (graded or None).
    Returns {row_index: (p, tau)}.
    """
    answered = [i for i, r in enumerate(rows) if r["out"]["action"] == "answer"]
    qids = sorted({rows[i]["qid"] for i in answered})
    res = {}
    for q in qids:
        test_idx = [i for i in answered if rows[i]["qid"] == q]
        train_all = [i for i in answered if rows[i]["qid"] != q]
        train_fit = [rows[i] for i in train_all if rows[i]["y"] is not None]
        test = [rows[i] for i in test_idx]
        p_test = _fit_predict(method, train_fit, test)
        # threshold chosen on the training fold's own (in-sample) predictions
        p_train = _fit_predict(method, train_fit, [rows[i] for i in train_all])
        tau = _best_tau([rows[i] for i in train_all], p_train)
        for i, p in zip(test_idx, p_test):
            res[i] = (float(p), tau)
    return res
