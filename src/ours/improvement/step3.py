"""Step 3 analysis: calibrated confidence + abstention gate, with ablation.

Layout of one run directory (written by notebooks/02_step3_runs.ipynb):
    <run>/<bench>/traces/<qid>.json      decision traces (bench = dev | original)
    <run>/<bench>/judgments.json         {qid: {verdict, reason}}  (evaluation only)
    <run>/<bench>/selfcheck.json         {qid: {answers_question, reason}}  (mechanism, G4)

Every confidence and threshold is out-of-fold (leave-one-question-out). Uncertainty is
shown with 95% bootstrap intervals over QUESTIONS (all runs of a question move together),
and each method is compared with the baseline on the same resampled questions (paired).

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
N_BOOT = 1000


def _read(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def load_rows(run_dirs, benches=("dev", "original")) -> list[dict]:
    rows = []
    for run in map(pathlib.Path, run_dirs):
        for b in benches:
            bdir = run / b
            if not (bdir / "traces").exists():
                continue
            judg, sc = _read(bdir / "judgments.json"), _read(bdir / "selfcheck.json")
            for it in BENCHES[b]():
                tp = bdir / "traces" / f"{it['id']}.json"
                if not tp.exists():
                    continue
                t = json.loads(tp.read_text(encoding="utf-8"))
                o = outcome(it, t, judg.get(it["id"]))
                rows.append({"run": run.name, "bench": b, "qid": f"{b}:{it['id']}", "item": it,
                             "category": it["category"], "feats": features(t, sc.get(it["id"])),
                             "out": o, "y": o["y"], "has_selfcheck": bool(sc)})
    return rows


# ---------------------------------------------------------------- per-row results
def row_results(rows, method):
    """Per row: final action/score after the gate, and (p, y) for graded answers."""
    if method == "as_is":
        pred = {}
    else:
        pred = calibrate.loqo(rows, method)
    res = []
    for i, r in enumerate(rows):
        o, acc = r["out"], r["item"]["acceptable"]
        if i in pred:
            p, tau = pred[i]
            keep = p >= tau
            final = "answer" if keep else "abstain"
            score = o["score_answer"] if keep else o["score_abstain"]
            withheld_good = (not keep) and acc == {"answer"} and (r["y"] or 0) >= 0.5
        else:
            p, final, score, withheld_good = None, o["action"], o["score_as_is"], False
        res.append({"p": p, "y": r["y"] if i in pred else None, "final": final, "score": score,
                    "ok": final in acc, "unsafe": final == "answer" and "answer" not in acc,
                    "withheld_good": withheld_good})
    return res


def _stats(rr, idx, n_runs):
    g = [i for i in idx if rr[i]["p"] is not None and rr[i]["y"] is not None]
    p, y = [rr[i]["p"] for i in g], [rr[i]["y"] for i in g]
    return {
        "ece": metrics.ece(p, y) if g else float("nan"),
        "auroc": metrics.auroc(p, y) if g else float("nan"),
        "aurc": metrics.aurc(p, y) if g else float("nan"),
        "brier": metrics.brier(p, y) if g else float("nan"),
        "reliability_score": float(np.mean([rr[i]["score"] for i in idx])),
        "action_accuracy": float(np.mean([rr[i]["ok"] for i in idx])),
        "answered_share": float(np.mean([rr[i]["final"] == "answer" for i in idx])),
        "unsafe_per_run": sum(rr[i]["unsafe"] for i in idx) / n_runs,
        "withheld_good_per_run": sum(rr[i]["withheld_good"] for i in idx) / n_runs,
        "n_graded": len(g),
    }


def _bootstrap(rows, rr, rr_bases, idx, n_runs, rng):
    """95% CIs over questions, and paired differences to the reference configurations."""
    by_q = defaultdict(list)
    for i in idx:
        by_q[rows[i]["qid"]].append(i)
    qs = list(by_q)
    keys = ("ece", "auroc", "aurc", "reliability_score", "unsafe_per_run")
    samples = defaultdict(list)
    diffs = {b: defaultdict(list) for b in rr_bases}
    for _ in range(N_BOOT):
        pick = [i for q in rng.choice(qs, len(qs)) for i in by_q[q]]
        s = _stats(rr, pick, n_runs)
        for k in keys:
            samples[k].append(s[k])
        for b, rb in rr_bases.items():
            sb = _stats(rb, pick, n_runs)
            for k in keys:
                diffs[b][k].append(s[k] - sb[k])
    pct = lambda v: [round(float(np.nanpercentile(v, 2.5)), 3), round(float(np.nanpercentile(v, 97.5)), 3)]
    ci = {k: pct(v) for k, v in samples.items()}
    dci = {b: {k: pct(v) for k, v in d.items()} for b, d in diffs.items()}
    return ci, dci


def evaluate(rows, methods=None, seed=0) -> dict:
    methods = methods or (["as_is"] + calibrate.METHODS)
    if not any(r["has_selfcheck"] for r in rows):
        methods = [m for m in methods if m not in ("lr_G4", "lr_noHedge")]
    n_runs = len({r["run"] for r in rows})
    rr_all = {m: row_results(rows, m) for m in methods}
    out = {}
    for b in sorted({r["bench"] for r in rows}):
        idx = [i for i, r in enumerate(rows) if r["bench"] == b]
        out[b] = {}
        for m in methods:
            s = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in _stats(rr_all[m], idx, n_runs).items()}
            bases = {k: rr_all[k] for k in ("as_is", "baseline") if k in rr_all and k != m}
            ci, dci = _bootstrap(rows, rr_all[m], bases, idx, n_runs, np.random.default_rng(seed))
            out[b][m] = {**s, "ci95": ci, "diff_ci95": dci}
    return {"methods": methods, "n_runs": n_runs, "by_bench": out,
            "by_category": by_category(rows, rr_all)}


def by_category(rows, rr_all, best=None):
    best = best or ("lr_G4" if "lr_G4" in rr_all else "lr_G3")
    out = {}
    for b in sorted({r["bench"] for r in rows}):
        cats = sorted({rows[i]["category"] for i in range(len(rows)) if rows[i]["bench"] == b})
        out[b] = {}
        n_runs = len({r["run"] for r in rows if r["bench"] == b})
        for c in cats:
            idx = [i for i, r in enumerate(rows) if r["bench"] == b and r["category"] == c]
            a, f = _stats(rr_all["as_is"], idx, n_runs), _stats(rr_all[best], idx, n_runs)
            out[b][c] = {"questions": len(idx) // n_runs, "method": best,
                         "score_as_is": round(a["reliability_score"], 3), "score_gated": round(f["reliability_score"], 3),
                         "unsafe_as_is": round(a["unsafe_per_run"], 2), "unsafe_gated": round(f["unsafe_per_run"], 2),
                         "withheld_good": round(f["withheld_good_per_run"], 2)}
    return out


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


# ---------------------------------------------------------------- reporting
def _f(v, ci=None):
    s = "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.3g}" if isinstance(v, float) else str(v)
    return f"{s} [{ci[0]:.2g}, {ci[1]:.2g}]" if ci and not any(np.isnan(ci)) else s


LABEL = {"as_is": "A0 · as is (no gate)", "baseline": "A1 · reference confidence + gate",
         "platt": "A2 · Platt + gate", "isotonic": "A2 · isotonic + gate", "lr_G1": "A3 · LR existing signals + gate",
         "lr_G2": "A4 · + process signals", "lr_G3": "A5 · + answer-text (hedge list)",
         "lr_G4": "A6 · + LLM self-check (full)", "lr_noHedge": "A7 · full without hedge list"}


def to_markdown(res: dict, agreement: dict) -> str:
    L = [f"# Step 3 results ({res['n_runs']} run(s), leave-one-question-out, 95% bootstrap CIs over questions)", ""]
    for b in [b for b in ("dev", "original") if b in res["by_bench"]]:
        R = res["by_bench"][b]
        L += [f"## {b} benchmark" + (" (original labels, unchanged)" if b == "original" else ""), "",
              "| Configuration | ECE ↓ | AUROC ↑ | AURC ↓ | Reliability score ↑ | Unsafe answers / run ↓ | Good answers withheld / run | Answered |",
              "|---|---|---|---|---|---|---|---|"]
        for m in res["methods"]:
            r = R[m]; c = r["ci95"]
            if m == "as_is":
                L.append(f"| {LABEL[m]} | – | – | – | {_f(r['reliability_score'], c['reliability_score'])} | {_f(r['unsafe_per_run'])} | – | {_f(r['answered_share'])} |")
            else:
                L.append(f"| {LABEL[m]} | {_f(r['ece'], c['ece'])} | {_f(r['auroc'], c['auroc'])} | {_f(r['aurc'], c['aurc'])} | "
                         f"{_f(r['reliability_score'], c['reliability_score'])} | {_f(r['unsafe_per_run'])} | {_f(r['withheld_good_per_run'])} | {_f(r['answered_share'])} |")
        best = "lr_G4" if "lr_G4" in R else "lr_G3"
        d1, d0 = R[best]["diff_ci95"]["baseline"], R[best]["diff_ci95"]["as_is"]
        L += ["", f"**Paired differences, {LABEL[best]}** (95% CI; an interval that excludes 0 is a clear effect):",
              f"- vs A1 (same gate, reference confidence): ECE {d1['ece']}, AUROC {d1['auroc']}, AURC {d1['aurc']}, reliability score {d1['reliability_score']}",
              f"- vs A0 (system as is): reliability score {d0['reliability_score']}, unsafe answers / run {d0['unsafe_per_run']}", ""]
        cat = res["by_category"].get(b, {})
        if b == "dev" and cat:
            L += [f"### By category ({LABEL[best]} vs as is)", "",
                  "| Category | Questions | Score as is | Score gated | Unsafe as is | Unsafe gated | Good answers withheld |",
                  "|---|---|---|---|---|---|---|"]
            for c, v in cat.items():
                L.append(f"| {c} | {v['questions']} | {v['score_as_is']} | {v['score_gated']} | {v['unsafe_as_is']} | {v['unsafe_gated']} | {v['withheld_good']} |")
            L.append("")
    L.append(f"Run-to-run action agreement: {agreement}")
    return "\n".join(L)


def plots(rows, out_dir: pathlib.Path, methods=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    have_sc = any(r["has_selfcheck"] for r in rows)
    methods = methods or (["baseline", "lr_G1", "lr_G4" if have_sc else "lr_G3"])
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for m in methods:
        pred = calibrate.loqo(rows, m)
        g = [i for i in pred if rows[i]["y"] is not None]
        p = np.array([pred[i][0] for i in g]); y = np.array([rows[i]["y"] for i in g])
        bins = np.minimum((p * 10).astype(int), 9)
        xs = [p[bins == b].mean() for b in range(10) if (bins == b).any()]
        ys = [y[bins == b].mean() for b in range(10) if (bins == b).any()]
        ax[0].plot(xs, ys, "o-", label=f"{LABEL[m]} (ECE {metrics.ece(p, y):.2f})")
        cov, risk = metrics.risk_coverage(p, y)
        ax[1].plot(cov, risk, label=f"{LABEL[m]} (AURC {metrics.aurc(p, y):.2f})")
    ax[0].plot([0, 1], [0, 1], "k--", lw=1)
    ax[0].set(xlabel="confidence", ylabel="mean correctness", title="Reliability diagram", xlim=(0, 1), ylim=(0, 1))
    ax[1].set(xlabel="coverage (share of answers kept)", ylabel="risk (1 − correctness)",
              title="Coverage–risk curve", xlim=(0, 1), ylim=(0, 1))
    for a in ax:
        a.legend(fontsize=7)
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
    md = to_markdown(res, agr)
    (out / "step3_results.md").write_text(md)
    plots(rows, out)
    print(md)


if __name__ == "__main__":
    main()
