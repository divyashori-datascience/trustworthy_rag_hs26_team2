"""Calibration and selective-answering metrics.

All functions take arrays over ANSWERED rows: p = predicted confidence, y = graded
correctness (1 / 0.5 / 0).
"""
from __future__ import annotations

import numpy as np


def ece(p, y, n_bins: int = 10) -> float:
    """Expected calibration error, equal-width bins, graded correctness."""
    p, y = np.asarray(p, float), np.asarray(y, float)
    if len(p) == 0:
        return float("nan")
    bins = np.minimum((p * n_bins).astype(int), n_bins - 1)
    err = 0.0
    for b in range(n_bins):
        m = bins == b
        if m.any():
            err += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(err)


def brier(p, y) -> float:
    p, y = np.asarray(p, float), np.asarray(y, float)
    return float(np.mean((p - y) ** 2)) if len(p) else float("nan")


def auroc(p, y) -> float:
    """Can confidence separate fully correct answers (y == 1) from the rest?"""
    p, y = np.asarray(p, float), np.asarray(y, float)
    pos, neg = p[y == 1.0], p[y < 1.0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    wins = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(wins / (len(pos) * len(neg)))


def risk_coverage(p, y):
    """Answer only the k most confident rows, k = 1..n. Returns (coverage, risk) arrays."""
    p, y = np.asarray(p, float), np.asarray(y, float)
    order = np.argsort(-p, kind="stable")
    loss = 1.0 - y[order]
    k = np.arange(1, len(p) + 1)
    return k / len(p), np.cumsum(loss) / k


def aurc(p, y) -> float:
    """Area under the risk-coverage curve (lower = confidence ranks answers better)."""
    if len(p) == 0:
        return float("nan")
    _, risk = risk_coverage(p, y)
    return float(risk.mean())


def summary(p, y) -> dict:
    return {
        "n": int(len(p)),
        "mean_conf": round(float(np.mean(p)), 3) if len(p) else None,
        "mean_correct": round(float(np.mean(y)), 3) if len(p) else None,
        "ece": round(ece(p, y), 3),
        "brier": round(brier(p, y), 3),
        "auroc": round(auroc(p, y), 3),
        "aurc": round(aurc(p, y), 3),
    }
