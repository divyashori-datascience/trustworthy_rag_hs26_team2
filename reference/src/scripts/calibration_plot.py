"""Confidence-calibration analysis (Extra Challenge #2).

Reads the LLM-judged correctness verdicts produced by ``evaluate_agentic.py
--judge`` (in ``evaluation_metrics.json`` under ``correctness.per_query``) and
asks: do the system's confidence scores align with actual correctness?

Verdicts are mapped to a graded correctness score (correct=1.0,
partially_correct=0.5, incorrect=0.0). We produce a reliability diagram
(mean confidence per bin vs. mean correctness per bin, against the y=x ideal),
report the Expected Calibration Error (ECE), and a per-verdict confidence panel.

Output: ``confidence_calibration.png`` + printed ECE/summary in the run dir.

Usage:
    python -m src.scripts.calibration_plot                 # results/agentic
    python -m src.scripts.calibration_plot --run results/agentic
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[1]))

from baseline import config  # noqa: E402

_SCORE = {"correct": 1.0, "partially_correct": 0.5, "incorrect": 0.0}


def expected_calibration_error(confs, scores, n_bins: int = 10) -> float:
    """ECE over equal-width confidence bins."""
    n = len(confs)
    if n == 0:
        return float("nan")
    ece = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        idx = [i for i, c in enumerate(confs) if (lo < c <= hi) or (b == 0 and c == 0)]
        if not idx:
            continue
        conf_b = sum(confs[i] for i in idx) / len(idx)
        acc_b = sum(scores[i] for i in idx) / len(idx)
        ece += (len(idx) / n) * abs(acc_b - conf_b)
    return ece


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(config.PATH_AGENTIC_RESULTS))
    ap.add_argument("--bins", type=int, default=10)
    args = ap.parse_args()

    run_dir = pathlib.Path(args.run)
    metrics = json.loads((run_dir / "evaluation_metrics.json").read_text(encoding="utf-8"))
    per_query = metrics.get("correctness", {}).get("per_query")
    if not per_query:
        print("No judged correctness found. Run evaluate_agentic.py --judge first.")
        return 1

    confs, scores, verdicts = [], [], []
    for v in per_query.values():
        if v.get("confidence") is None:
            continue
        confs.append(float(v["confidence"]))
        scores.append(_SCORE.get(v["verdict"], 0.0))
        verdicts.append(v["verdict"])

    n = len(confs)
    mean_conf = sum(confs) / n
    mean_acc = sum(scores) / n
    strict_acc = sum(1 for s in scores if s == 1.0) / n
    ece = expected_calibration_error(confs, scores, args.bins)

    print(f"n judged: {n}")
    print(f"mean confidence: {mean_conf:.3f}")
    print(f"mean correctness (graded, partial=0.5): {mean_acc:.3f}")
    print(f"strict accuracy (correct only): {strict_acc:.3f}")
    print(f"ECE ({args.bins} bins): {ece:.3f}")
    print(f"overconfidence gap (conf - acc): {mean_conf - mean_acc:+.3f}")

    # --- plot
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as e:  # noqa: BLE001
        print(f"(plot skipped: {e})")
        return 0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    # reliability diagram (bin means)
    nb = args.bins
    bx, by, bn = [], [], []
    for b in range(nb):
        lo, hi = b / nb, (b + 1) / nb
        idx = [i for i, c in enumerate(confs) if (lo < c <= hi) or (b == 0 and c == 0)]
        if not idx:
            continue
        bx.append(sum(confs[i] for i in idx) / len(idx))
        by.append(sum(scores[i] for i in idx) / len(idx))
        bn.append(len(idx))
    ax1.plot([0, 1], [0, 1], "k--", lw=1, label="perfect calibration")
    ax1.scatter(bx, by, s=[40 + 30 * k for k in bn], color="tab:red", zorder=3,
                label="binned (size ~ n)")
    ax1.scatter(confs, scores, s=18, color="tab:blue", alpha=0.4, zorder=2,
                label="per answer")
    ax1.axhline(mean_acc, color="tab:green", ls=":", lw=1, label=f"mean correctness {mean_acc:.2f}")
    ax1.axvline(mean_conf, color="tab:orange", ls=":", lw=1, label=f"mean confidence {mean_conf:.2f}")
    ax1.set_xlabel("reported confidence")
    ax1.set_ylabel("correctness (correct=1, partial=0.5, wrong=0)")
    ax1.set_xlim(0, 1.02)
    ax1.set_ylim(-0.05, 1.05)
    ax1.set_title(f"Reliability diagram (ECE={ece:.2f})")
    ax1.legend(fontsize=7, loc="upper left")

    # confidence by verdict
    order = ["correct", "partially_correct", "incorrect"]
    data = [[confs[i] for i in range(n) if verdicts[i] == v] for v in order]
    data_present = [(v, d) for v, d in zip(order, data) if d]
    if data_present:
        ax2.boxplot([d for _, d in data_present],
                    labels=[v.replace("_", "\n") for v, _ in data_present])
        for j, (_, d) in enumerate(data_present, start=1):
            ax2.scatter([j] * len(d), d, color="tab:blue", alpha=0.5, s=18)
    ax2.set_ylabel("reported confidence")
    ax2.set_title("Confidence by correctness verdict")

    fig.suptitle("Confidence calibration — agentic system (LLM-judged)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = run_dir / "confidence_calibration.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"Wrote {out}")

    # persist the numbers
    calib = {
        "n": n,
        "mean_confidence": round(mean_conf, 4),
        "mean_correctness_graded": round(mean_acc, 4),
        "strict_accuracy": round(strict_acc, 4),
        "ece": round(ece, 4),
        "overconfidence_gap": round(mean_conf - mean_acc, 4),
    }
    (run_dir / "calibration.json").write_text(json.dumps(calib, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
