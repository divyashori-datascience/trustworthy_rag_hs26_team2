"""Build notebooks/02_step3_runs.ipynb.

The notebook embeds our Step 3 package (src/ours/improvement) and the development
benchmark, so Colab needs no GitHub access. Re-run this script after changing the
package:  python tools/build_step3_notebook.py
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
setup = json.loads((ROOT / "notebooks" / "01_failure_demo.ipynb").read_text())["cells"][2:9]

PKG = ["__init__.py", "benchmarks.py", "features.py", "outcomes.py", "metrics.py", "calibrate.py", "step3.py"]
files = {f"g02step3/{n}": (ROOT / "src/ours/improvement" / n).read_text() for n in PKG}
files["benchmark/dev/Development_Benchmark_v1.0.jsonl"] = (ROOT / "benchmark/dev/Development_Benchmark_v1.0.jsonl").read_text()


def md(t):
    return {"cell_type": "markdown", "metadata": {}, "source": t}


def code(t):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": t}


for c in setup:
    c["outputs"], c["execution_count"] = [], None

cells = [
    md("""# 02 · Step 3 runs: calibrated confidence (Track A)
**Advanced GenAI HS26 · Trustworthy Agentic RAG · Group 2: Divya Shori, Faranak Rahimi, Hanieh Jebeli**

What this notebook does:
1. runs the **unchanged reference system** on the instructor's **development benchmark (80 questions)** and the **original 25 questions**, `N_RUNS` times;
2. grades every answer with the **reference team's own judge prompt** (Haiku);
3. trains and evaluates our **calibrator + abstention gate** leave-one-question-out, with the ablation ladder, and saves tables and plots to Drive.

Everything is saved to `My Drive/AdvGenAI/step3/` as it goes. If Colab disconnects, run all again: finished questions are skipped.
Cost estimate (Opus generation, as in Step 1): about **$3–4 per run of 105 questions**, about 20–25 min per run.

**The held-out test set is not used anywhere.** The system only receives the question text (no labels or notes)."""),
    md("## 1 · Setup (same as notebooks 00 and 01)"),
    *setup,
    code("from baseline import config\nfrom agentic import AgenticRAG\nwith step(\"AgenticRAG.from_pretrained()\"):\n    print(\"  models:\", config.AGENT_MODEL_GENERATION, config.AGENT_MODEL_VERIFIER, config.AGENT_MODEL_UTILITY)\n    rag = AgenticRAG.from_pretrained()\n"),
    md("## 2 · Our Step 3 code (embedded from the repo, `src/ours/improvement`)"),
    code("FILES = " + json.dumps(files, ensure_ascii=False) + """
OURS = pathlib.Path("/content/ours")
for rel, text in FILES.items():
    p = OURS / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8")
# original labels, unchanged, from the reference benchmark folder
lab = OURS / "reference" / "Baseline" / "benchmark"; lab.mkdir(parents=True, exist_ok=True)
shutil.copy(BASELINE_ROOT / "benchmark" / "reliability_labels.json", lab / "reliability_labels.json")
os.environ["G02_ROOT"] = str(OURS)
if str(OURS) not in sys.path: sys.path.insert(0, str(OURS))
from g02step3 import benchmarks, outcomes, step3   # our package, named so it can't clash with the reference "src"
BENCH = {"dev": benchmarks.load_dev(), "original": benchmarks.load_original()}
print({k: len(v) for k, v in BENCH.items()})
"""),
    md("## 3 · Runs (resume-safe)\nSet `N_RUNS` (3 for the final numbers; start with 1 to check everything works)."),
    code("""N_RUNS = 3
OUT = WORK / "step3"
OUT.mkdir(parents=True, exist_ok=True)

def run_one(run_idx, bench):
    tdir = OUT / f"run{run_idx}" / bench / "traces"; tdir.mkdir(parents=True, exist_ok=True)
    todo = [it for it in BENCH[bench] if not (tdir / f"{it['id']}.json").exists()]
    print(f"run{run_idx}/{bench}: {len(todo)} to do")
    for k, it in enumerate(todo, 1):
        t0 = time.perf_counter()
        try:
            tr = rag.answer(it["id"], it["question"], {"id": it["id"], "question": it["question"]})
        except Exception as e:
            log_issue(f"run{run_idx}/{bench}/{it['id']}", e); continue
        (tdir / f"{it['id']}.json").write_text(json.dumps(tr.to_dict(), indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"  {k}/{len(todo)} {it['id']}: {tr.final.get('action')} ({time.perf_counter()-t0:.0f}s)")

for r in range(1, N_RUNS + 1):
    for b in ("dev", "original"):
        run_one(r, b)
print("usage so far:", rag.llm.usage.as_dict())
"""),
    md("## 4 · Answer self-check (part of our mechanism, feature group G4)\nOne Haiku call per answer: *does this answer actually answer the question?* It sees only the question and the system's answer, never a gold answer, so it can run at answer time."),
    code("""def check(question, answer):
    return rag.llm.complete_json(system=outcomes.SELFCHECK_SYSTEM,
        user=f"Question: {question}\\nSystem answer: {answer}",
        schema=outcomes.SELFCHECK_SCHEMA, model=config.AGENT_MODEL_UTILITY, max_tokens=200)

for r in range(1, N_RUNS + 1):
    for b in ("dev", "original"):
        bdir = OUT / f"run{r}" / b
        if not (bdir / "traces").exists(): continue
        sp = bdir / "selfcheck.json"
        cache = json.loads(sp.read_text()) if sp.exists() else {}
        traces = {p.stem: json.loads(p.read_text()) for p in (bdir / "traces").glob("*.json")}
        sc = outcomes.selfcheck_run(BENCH[b], traces, check, cache)
        sp.write_text(json.dumps(sc, indent=1, ensure_ascii=False))
        print(f"run{r}/{b}: {len(sc)} self-checked")
"""),
    md("## 5 · Grade the answers (evaluation only: reference judge prompt, resume-safe)"),
    code("""def grade(question, gold, candidate):
    return rag.llm.complete_json(system=outcomes.JUDGE_SYSTEM,
        user=f"Question: {question}\\nGold answer: {gold}\\nCandidate answer: {candidate}",
        schema=outcomes.JUDGE_SCHEMA, model=config.AGENT_MODEL_UTILITY, max_tokens=300)

for r in range(1, N_RUNS + 1):
    for b in ("dev", "original"):
        bdir = OUT / f"run{r}" / b
        if not (bdir / "traces").exists(): continue
        jp = bdir / "judgments.json"
        cache = json.loads(jp.read_text()) if jp.exists() else {}
        traces = {p.stem: json.loads(p.read_text()) for p in (bdir / "traces").glob("*.json")}
        judg = outcomes.judge_run(BENCH[b], traces, grade, cache)
        jp.write_text(json.dumps(judg, indent=1, ensure_ascii=False))
        print(f"run{r}/{b}: {len(judg)} graded")
"""),
    md("## 6 · Calibrator + gate, leave-one-question-out, with ablation and 95% intervals"),
    code("""from IPython.display import Markdown, Image, display
runs = sorted(str(p) for p in OUT.glob("run*") if p.is_dir())
rows = step3.load_rows(runs)
res = step3.evaluate(rows)
agr = step3.run_agreement(rows)
md_text = step3.to_markdown(res, agr)
RES = OUT / "results"; RES.mkdir(exist_ok=True)
(RES / "step3_results.md").write_text(md_text)
(RES / "step3_metrics.json").write_text(json.dumps({"results": res, "agreement": agr}, indent=1))
display(Markdown(md_text))
display(Image(str(step3.plots(rows, RES))))
"""),
    md("""**How to read the table**
- *ECE / Brier*: is the confidence honest? Lower is better.
- *AUROC / AURC*: does a higher confidence mean a better answer? AUROC higher, AURC lower is better.
- *Reliability score*: mean value per question after the gate (correct answer 1, partial 0.5, acceptable abstain/clarify 1, wrong action 0).
- *Unsafe answers / run*: answers given where the benchmark says the system should not answer.
- *Good answers withheld*: the cost of the gate (correct or partial answers it blocked).
- *[a, b]*: 95% bootstrap interval over questions. The paired differences under each table show whether the full mechanism beats the reference confidence (interval excludes 0).
- *A7 (without hedge list)* checks that the result does not depend on the hand-written phrase list.
- On the **original** benchmark the labels are used unchanged (instructor decision): 21 of 25 expect ANSWER, so the gate can only lose there; the dev set (16 abstain cases) is where it can help."""),
]

nb = {"cells": cells, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"},
                                    "language_info": {"name": "python"}, "colab": {"provenance": []},
                                    "accelerator": "GPU"}, "nbformat": 4, "nbformat_minor": 5}
(ROOT / "notebooks" / "02_step3_runs.ipynb").write_text(json.dumps(nb, indent=1, ensure_ascii=False))
print("written notebooks/02_step3_runs.ipynb", len(cells), "cells")
