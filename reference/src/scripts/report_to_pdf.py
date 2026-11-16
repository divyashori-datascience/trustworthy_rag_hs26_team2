"""Render docs/final_report.md to a styled PDF (docs/final_report.pdf).

Pure-Python pipeline (no system libraries needed):
    markdown  -> HTML (tables, fenced code, table of contents)
    xhtml2pdf -> PDF  (cover page, print CSS, embedded figures)

PDF-only layout (the markdown stays clean for GitHub):
    page 1 : title / cover page (built from the report's front matter)
    page 2 : abstract only
    page 3+: introduction onward
Tables are kept whole (never split across a page break).

Usage (from repo root):
    python -m src.scripts.report_to_pdf
"""
from __future__ import annotations

import pathlib
import re
import sys

import markdown
from xhtml2pdf import pisa

_REPO = pathlib.Path(__file__).resolve().parents[2]
_DOCS = _REPO / "docs"
_MD = _DOCS / "final_report.md"
_PDF = _DOCS / "final_report.pdf"

_PAGEBREAK = '<div style="page-break-before: always;"></div>'

# xhtml2pdf's built-in fonts cover only WinAnsi/Latin-1, so em/en dashes render
# fine but arrows, math symbols, the bonus star, and box-drawing characters show
# as blank gaps. Map them to ASCII equivalents *for the PDF only* — the source
# markdown on GitHub keeps its original Unicode.
_GLYPH_MAP = {
    "→": "->", "↔": "<->", "≥": ">=", "≠": "!=", "−": "-", "⭐": "*",
    "─": "-", "│": "|",
    "┌": "+", "┐": "+", "└": "+", "┘": "+",
    "┬": "+", "┴": "+", "├": "+", "┤": "+", "┼": "+",
    "▼": "v", "▲": "^", "▶": ">", "◀": "<",
}
_GLYPH_TABLE = {ord(k): v for k, v in _GLYPH_MAP.items()}

# Static cover-page header (institution / course context).
_COVER_HEADER = (
    "Lucerne University of Applied Sciences and Arts (HSLU)<br/>"
    "MSc in Applied Information and Data Science<br/>"
    "Advanced Generative AI — Capstone Project, FS26"
)

_CSS = """
@page {
    size: a4 portrait;
    margin: 2cm 2cm 2.2cm 2cm;
    @frame footer {
        -pdf-frame-content: footer_content;
        bottom: 1cm; margin-left: 2cm; margin-right: 2cm; height: 1cm;
    }
}
body { font-family: "Helvetica", "Arial", sans-serif; font-size: 10pt;
       line-height: 1.4; color: #1a1a1a; }
h1 { font-size: 20pt; color: #111; margin: 0 0 4pt 0; }
h2 { font-size: 14pt; color: #1a3a5c; border-bottom: 1pt solid #ccc;
     padding-bottom: 2pt; margin: 16pt 0 6pt 0; -pdf-keep-with-next: true; }
h3 { font-size: 11.5pt; color: #1a3a5c; margin: 12pt 0 4pt 0;
     -pdf-keep-with-next: true; }
p { margin: 4pt 0; }
a { color: #1a5cad; text-decoration: none; }
code { font-family: "Courier New", monospace; font-size: 9pt; background: #f2f2f2; }
pre { font-family: "Courier New", monospace; font-size: 8pt; background: #f5f5f5;
      border: 1pt solid #ddd; padding: 6pt; margin: 6pt 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; }
.keep { page-break-inside: avoid; }
th { background: #1a3a5c; color: #fff; font-weight: bold; font-size: 8.5pt;
     border: 0.5pt solid #1a3a5c; padding: 3pt 5pt; text-align: left; }
td { border: 0.5pt solid #bbb; padding: 3pt 5pt; font-size: 8.5pt;
     vertical-align: top; }
blockquote { color: #555; border-left: 3pt solid #ccc; margin: 6pt 0;
             padding: 2pt 10pt; }
img { max-width: 480px; }
hr { border: none; border-top: 0.5pt solid #ddd; margin: 10pt 0; }
ul, ol { margin: 4pt 0 4pt 0; }
li { margin: 1pt 0; }

/* ---- cover page ---- */
.cover { text-align: center; page-break-after: always; }
.cover-top { margin-top: 28pt; font-size: 11.5pt; color: #444; line-height: 1.7; }
.cover-titlewrap { margin-top: 80pt; }
.cover-title { font-size: 24pt; font-weight: bold; color: #111; line-height: 1.3;
               padding: 0 24pt; }
.cover-subtitle { font-size: 13pt; color: #1a3a5c; margin-top: 10pt; }
.cover-rule { border: none; border-top: 1.5pt solid #1a3a5c; margin: 16pt 70pt; }
.cover-meta { margin-top: 80pt; font-size: 11.5pt; color: #222; line-height: 1.7; }
.cover-meta strong { color: #1a3a5c; }
"""

_FOOTER = (
    '<div id="footer_content" style="text-align:center; font-size:8pt; color:#888;">'
    'Reliable and Adaptive Agentic RAG — FS26 &nbsp;|&nbsp; page '
    '<pdf:pagenumber> of <pdf:pagecount>'
    "</div>"
)


def _parse_front_matter(text: str) -> dict:
    """Pull title / subtitle / authors / date from the top of the markdown."""
    meta = {"title": "", "subtitle": "", "authors": "", "date": ""}
    for line in text.splitlines():
        s = line.strip()
        if not meta["title"] and s.startswith("# ") and not s.startswith("##"):
            meta["title"] = s[2:].strip()
        elif not meta["subtitle"] and s.startswith("### "):
            meta["subtitle"] = s[4:].strip()
        elif s.startswith("**Authors:**"):
            meta["authors"] = s.split("**Authors:**", 1)[1].strip()
        elif s.startswith("**Author:**"):
            meta["authors"] = s.split("**Author:**", 1)[1].strip()
        elif s.startswith("**Date:**"):
            meta["date"] = s.split("**Date:**", 1)[1].strip()
        if all(meta.values()):
            break
    return meta


def _cover_html(meta: dict) -> str:
    subtitle = meta["subtitle"]
    if subtitle.lower().startswith("final report"):
        # avoid duplicating "Advanced Generative AI" already in the header
        subtitle = "Final Report"
    return f"""
<div class="cover">
  <div class="cover-top">{_COVER_HEADER}</div>
  <div class="cover-titlewrap">
    <hr class="cover-rule"/>
    <div class="cover-title">{meta['title']}</div>
    <div class="cover-subtitle">{subtitle}</div>
    <hr class="cover-rule"/>
  </div>
  <div class="cover-meta">
    <strong>Authors</strong><br/>
    {meta['authors']}<br/><br/>
    <strong>Date</strong><br/>
    {meta['date']}<br/><br/>
    <strong>Code</strong><br/>
    This repository (see &sect;11 for full reproduction)
  </div>
</div>
"""


def _link_callback(uri: str, rel: str) -> str:
    """Resolve relative image/resource paths (markdown lives in docs/)."""
    if uri.startswith(("http://", "https://", "data:")):
        return uri
    candidate = (_DOCS / uri).resolve()
    if candidate.exists():
        return str(candidate)
    return str((_REPO / uri).resolve())  # try repo-root relative


def main() -> int:
    if not _MD.exists():
        print(f"ERROR: {_MD} not found")
        return 1

    raw = _MD.read_text(encoding="utf-8")
    meta = _parse_front_matter(raw)

    # body = everything after the front-matter rule (drops title/author block)
    idx = raw.find("\n---\n")
    body = raw[idx + len("\n---\n"):] if idx != -1 else raw

    # abstract alone on page 2: page-break before the introduction (drop the hr)
    body = body.replace(
        "---\n\n## 1. Introduction and objective",
        f"{_PAGEBREAK}\n\n## 1. Introduction and objective",
        1,
    )

    # xhtml2pdf has no working keep-together for tables, so a table landing near
    # a page bottom can split. Start the few subsections whose (tall) tables
    # would otherwise split on a fresh page. Revisit if the content shifts.
    for marker in ("### 8d. Correct abstention",):
        body = body.replace(marker, f"{_PAGEBREAK}\n\n{marker}", 1)

    body = body.translate(_GLYPH_TABLE)
    body_html = markdown.markdown(
        body,
        extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"],
    )

    # xhtml2pdf has no descendant selectors, so inline <code> in a header would
    # render as invisible light-on-white. Strip <code> inside header cells.
    body_html = re.sub(
        r"(<th[^>]*>)(.*?)(</th>)",
        lambda m: m.group(1) + m.group(2).replace("<code>", "").replace("</code>", "") + m.group(3),
        body_html,
        flags=re.S,
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{_CSS}</style></head>
<body>{_FOOTER}{_cover_html(meta)}{body_html}</body></html>"""

    with open(_PDF, "wb") as out:
        result = pisa.CreatePDF(
            src=html, dest=out, encoding="utf-8", link_callback=_link_callback
        )

    if result.err:
        print(f"ERROR: PDF generation reported {result.err} error(s)")
        return 1
    print(f"Wrote {_PDF}  ({_PDF.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
