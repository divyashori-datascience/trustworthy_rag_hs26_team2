"""Render the reliability-aware multi-agent architecture to docs/architecture.png.

A clean matplotlib diagram (no graphviz/system deps) used in §4 of the report.
Renders crisply both on GitHub and in the PDF, unlike the ASCII fallback.

Usage (from repo root):
    python -m src.scripts.make_architecture_diagram
"""
from __future__ import annotations

import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

_REPO = pathlib.Path(__file__).resolve().parents[2]
_OUT = _REPO / "docs" / "architecture.png"

# role -> (fill, edge)
COLORS = {
    "control":    ("#fde8c0", "#d99a1c"),   # PolicyController
    "support":    ("#d8e6f3", "#3a6ea5"),   # profiler / retrieval / evidence
    "production": ("#d6efdc", "#3a8a55"),   # AnswerGenerator
    "checking":   ("#e7daf2", "#7a52a5"),   # Verifier
}


def _box(ax, x, y, w, h, title, sub, role, title_size=11, sub_size=8.5):
    fill, edge = COLORS[role]
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.02,rounding_size=0.12",
            linewidth=1.6, edgecolor=edge, facecolor=fill, zorder=2,
        )
    )
    cx, cy = x + w / 2, y + h / 2
    ax.text(cx, cy + 0.20, title, ha="center", va="center",
            fontsize=title_size, fontweight="bold", color="#1a1a1a", zorder=3)
    ax.text(cx, cy - 0.28, sub, ha="center", va="center",
            fontsize=sub_size, color="#333333", zorder=3)


def _arrow(ax, p0, p1, color="#444", lw=1.8, style="-|>", ls="-", rad=0.0):
    ax.add_patch(
        FancyArrowPatch(
            p0, p1, arrowstyle=style, mutation_scale=14,
            linewidth=lw, color=color, linestyle=ls, zorder=1,
            connectionstyle=f"arc3,rad={rad}",
        )
    )


def main() -> int:
    fig, ax = plt.subplots(figsize=(12.4, 6.1))
    ax.set_xlim(0, 12.4)
    ax.set_ylim(0, 6.0)
    ax.axis("off")

    # --- pipeline boxes (left -> right) -----------------------------------
    bw, bh, y0 = 2.0, 1.3, 2.6
    lefts = [0.7, 3.05, 5.4, 7.75, 10.1]
    specs = [
        ("QueryProfiler", "lang / type /\nambiguity", "support"),
        ("RetrievalCoordinator", "bm25 / dense / graph\n+ 3 orch. modes", "support"),
        ("EvidenceAnalyzer", "sufficiency,\nagreement", "support"),
        ("AnswerGenerator", "grounded,\ncited draft", "production"),
        ("Verifier / Critic", "groundedness,\ncontradiction", "checking"),
    ]
    centers = []
    for x, (title, sub, role) in zip(lefts, specs):
        _box(ax, x, y0, bw, bh, title, sub, role,
             title_size=10 if len(title) < 16 else 9)
        centers.append((x + bw / 2, y0 + bh / 2))

    ycen = y0 + bh / 2

    # query input
    _arrow(ax, (0.0, ycen), (0.68, ycen), color="#222", lw=2.0)
    ax.text(0.33, ycen + 0.28, "query", ha="center", fontsize=8.5, color="#222")

    # between-stage arrows
    labels = ["mode", "chunks", "evidence", "draft"]
    for (lx,), (rx,), lab in zip(
        [(lefts[i] + bw,) for i in range(4)],
        [(lefts[i + 1],) for i in range(4)],
        labels,
    ):
        _arrow(ax, (lx, ycen), (rx, ycen), color="#444", lw=1.8)
        ax.text((lx + rx) / 2, ycen + 0.26, lab, ha="center",
                fontsize=8, color="#444")

    # --- PolicyController band (top) --------------------------------------
    pc_x, pc_y, pc_w, pc_h = 0.7, 4.65, 11.4, 0.95
    _box(ax, pc_x, pc_y, pc_w, pc_h,
         "PolicyController",
         "reads signals  ->  decides the next action  ->  logs a per-query DecisionTrace",
         "control", title_size=12, sub_size=9.5)

    # signals up / actions down (dashed)
    _arrow(ax, (3.0, y0 + bh), (3.0, pc_y), color="#3a6ea5", lw=1.6,
           style="-|>", ls=(0, (4, 3)))
    ax.text(3.15, (y0 + bh + pc_y) / 2, "signals", ha="left", va="center",
            fontsize=8.5, color="#3a6ea5", rotation=90)

    _arrow(ax, (9.4, pc_y), (9.4, y0 + bh), color="#d99a1c", lw=1.6,
           style="-|>", ls=(0, (4, 3)))
    ax.text(9.25, (y0 + bh + pc_y) / 2, "actions", ha="right", va="center",
            fontsize=8.5, color="#b5800f", rotation=90)

    # --- recovery loop (Verifier -> RetrievalCoordinator) -----------------
    _arrow(ax, centers[4][:1] + (y0,), centers[1][:1] + (y0,),
           color="#b23a48", lw=2.0, style="-|>", rad=-0.32)
    ax.text((centers[1][0] + centers[4][0]) / 2, 1.25,
            "recovery:  rewrite query  +  switch to an untried retrieval mode",
            ha="center", fontsize=9, color="#b23a48", style="italic")

    # --- legend -----------------------------------------------------------
    leg = [
        ("control", "Decision control"),
        ("support", "Retrieval & evidence"),
        ("production", "Answer production"),
        ("checking", "Answer checking"),
    ]
    lx = 0.7
    for role, lab in leg:
        fill, edge = COLORS[role]
        ax.add_patch(FancyBboxPatch((lx, 0.2), 0.32, 0.32,
                     boxstyle="round,pad=0.01,rounding_size=0.05",
                     linewidth=1.2, edgecolor=edge, facecolor=fill))
        ax.text(lx + 0.42, 0.36, lab, ha="left", va="center", fontsize=8.5,
                color="#333")
        lx += 0.42 + 0.06 * len(lab) + 1.1

    fig.tight_layout(pad=0.4)
    fig.savefig(_OUT, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {_OUT}  ({_OUT.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
