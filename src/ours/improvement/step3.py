"""Step 3 analysis: calibrated confidence + abstention gate, with ablation.

Layout of one run directory (written by notebooks/02_step3_runs.ipynb):
    <run>/<bench>/traces/<qid>.json      decision traces (bench = dev | original)
    <run>/<bench>/judgments.json         {qid: {verdict, reason}} for graded answers

Usage:
    python -m src.ours.improvement.step3 RUN_DIR [RUN_DIR ...] --out results/step3
"""
from __future__ import annotations

import argparse
import json
import pathlib
from collections import defaultdict

import numpy as np

from . import benchmarks, calibrate, metrics
from .features import features
from .outcomes import outcome

BENCHES = {"dev": benchmarks.load_dev, "original": benchmarks.load_original}


def load_rows(run_dirs, benches=("dev", "original")) -> list[dict]:
    rows = []
    for run in map(pathlib.Path, run_dirs):
        for b in benches:
            bdir = run / b
            if not (bdir / "traces").exists():
                continue
            items = BENCHES[b]()
            judg_path = bdir / "judgments.json"
            judg = json.loads(judg_path.read_text(encoding="utf-8")) if judg_path.exists() else {}
            for it in items:
                tp = bdir / "traces" / f"{it['id']}.json"
                if not tp.exists():
                    continue
                t = json.loads(tp.read_text(encoding="utf-8"))
                o = outcome(it, t, judg.get(it["id"]))
                rows.append({"run": run.name, "bench": b, "qid": f"{b}:{it['id']}", "item": it,
                             "category": it["category"], "feats": features(t), "out": o, "y": o["y"]})
    return rows


def evaluate(rows: list[dict], methods=calibrate.METHODS) -> dict:
    results = {}
    for m in methods:
        pred = calibrate.loqo(rows, m)
        per_bench = {}
        for b in sorted({r["bench"] for r in rows}):
            idx = [i for i, r in enumerate(rows) if r["bench"] == b]
            graded = [i for i in idx if i in pred and rows[i]["y"] is not None]
            cal = metrics.summary([pred[i][0] for i in graded], [rows[i]["y"] for i in graded])
            score, act_ok, answered, unsafe, false_abst, gated = [], [], 0, 0, 0, 0
            for i in idx:
                r, o = rows[i], rows[i]["out"]
                if i in pred:
                    p, tau = pred[i]
                    keep = p >= tau
                    gated += not keep
                    final = "answer" if keep else "abstain"
                    s = o["score_answer"] if keep else o["score_abstain"]
                    if not keep and r["item"]["acceptable"] == {"answer"} and (r["y"] or 0) >= 0.5:
                        false_abst += 1
                else:
                    final, s = o["action"], o["score_as_is"]
                answered += final == "answer"
                unsafe += final == "answer" and "answer" not in r["item"]["acceptable"]
                score.append(s)
                act_ok.append(final in r["item"]["acceptable"])
            n = len(idx)
            per_bench[b] = {
                **cal,
                "rows": n,
                "reliability_score": round(float(np.mean(score)), 3),
                "action_accuracy": round(float(np.mean(act_ok)), 3),
                "answered_share": round(answered / n, 3),
                "unsafe_answers_per_run": round(unsafe / len({r['run'] for r in rows}), 2),
                "gated": gated,
                "gated_good_answers": false_abst,
            }
        results[m] = per_bench
    # reference point: the system exactly as it is (no gate)
    results["as_is"] = {}
    for b in sorted({r["bench"] for r in rows}):
        idx = [i for i, r in enumerate(rows) if r["bench"] == b]
        runs = len({rows[i]["run"] for i in idx})
        results["as_is"][b] = {
            "rows": len(idx),
            "reliability_score": round(float(np.mean([rows[i]["out"]["score_as_is"] for i in idx])), 3),
            "action_accuracy": round(float(np.mean([rows[i]["out"]["action_ok"] for i in idx])), 3),
            "answered_share": round(float(np.mean([rows[i]["out"]["action"] == "answer" for i in idx])), 3),
            "unsafe_answers_per_run": round(sum(rows[i]["out"]["action"] == "answer"
                                                and "answer" not in rows[i]["item"]["acceptable"]
                                                for i in idx) / runs, 2),
        }
    return results


def run_agreement(rows) -> dict:
    """Share of questions whose action is identical in every run (Step 1: 21/25)."""
    by_q = defaultdict(set)
    for r in rows:
        by_q[(r["bench"], r["item"]["id"])].add(r["out"]["action"])
    out = {}
    for b in sorted({k[0] for k in by_q}):
        qs = [v for k, v in by_q.items() if k[0] == b]
        out[b] = round(sum(len(v) == 1 for v in qs) / len(qs), 3)
    return out


def to_markdown(res: dict, agreement: dict, n_runs: int) -> str:
    L = [f"# Step 3 results ({n_runs} run(s), leave-one-question-out)", ""]
    for b in [b for b in ("dev", "original") if b in res["as_is"]]:
        L += [f"## {b} benchmark" + (" (original labels, unchanged)" if b == "original" else ""), "",
              "| Method | ECE ↓ | Brier ↓ | AUROC ↑ | AURC ↓ | Reliability score ↑ | Action accuracy ↑ | Answered | Unsafe answers / run ↓ | Good answers withheld |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        a = res["as_is"][b]
        L.append(f"| as is (no gate) | – | – | – | – | {a['reliability_score']} | {a['action_accuracy']} | {a['answered_share']} | {a['unsafe_answers_per_run']} | – |")
        for m in calibrate.METHODS:
            r = res[m][b]
            L.append(f"| {m} + gate | {r['ece']} | {r['brier']} | {r['auroc']} | {r['aurc']} | {r['reliability_score']} | {r['action_accuracy']} | {r['answered_share']} | {r['unsafe_answers_per_run']} | {r['gated_good_answers']} |")
        L.append("")
    L.append(f"Run-to-run action agreement: {agreement}")
    return "\n".join(L)


def plots(rows, out_dir: pathlib.Path, methods=("baseline", "lr_G3")):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for m in methods:
        pred = calibrate.loqo(rows, m)
        g = [i for i in pred if rows[i]["y"] is not None]
        p = np.array([pred[i][0] for i in g]); y = np.array([rows[i]["y"] for i in g])
        bins = np.minimum((p * 10).astype(int), 9)
        xs = [p[bins == b].mean() for b in range(10) if (bins == b).any()]
        ys = [y[bins == b].mean() for b in range(10) if (bins == b).any()]
        ax[0].plot(xs, ys, "o-", label=f"{m} (ECE {metrics.ece(p, y):.2f})")
        cov, risk = metrics.risk_coverage(p, y)
        ax[1].plot(cov, risk, label=f"{m} (AURC {metrics.aurc(p, y):.2f})")
    ax[0].plot([0, 1], [0, 1], "k--", lw=1); ax[0].set(xlabel="confidence", ylabel="mean correctness",
                                                    title="Reliability diagram", xlim=(0, 1), ylim=(0, 1))
    ax[1].set(xlabel="coverage (share of answers kept)", ylabel="risk (1 − correctness)",
              title="Coverage–risk curve", xlim=(0, 1), ylim=(0, 1))
    for a in ax:
        a.legend(fontsize=8)
    plt.tight_layout()
    path = out_dir / "calibration_plots.png"
    plt.savefig(path, dpi=110)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--out", default="results/step3")
    args = ap.parse_args()
    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)
    rows = load_rows(args.runs)
    res = evaluate(rows)
    agr = run_agreement(rows)
    (out / "step3_metrics.json").write_text(json.dumps({"results": res, "agreement": agr}, indent=1))
    md = to_markdown(res, agr, len(args.runs))
    (out / "step3_results.md").write_text(md)
    plots(rows, out)
    print(md)


if __name__ == "__main__":
    main()
