"""Look up and verify evidence chunks in the shared index (docs_fixed_norm.pkl).

The reference system can only answer from the indexed chunks, not from the raw HTML pages,
and the index does not contain every page or every paragraph (see docs/audit/index_coverage.md).
So benchmark evidence must be checked against the chunks.

Usage (from the repo root; needs langchain-core to unpickle the Documents):

    # find chunks containing all given phrases (case-, accent- and punctuation-insensitive)
    python -m src.ours.benchmark.fill_chunk_ids --pkl <path>/docs_fixed_norm.pkl --find "Olaf Kübler"
    python -m src.ours.benchmark.fill_chunk_ids --pkl <path>/docs_fixed_norm.pkl --find "QS" "Platz sieben"

    # verify every chunk ID listed in the benchmark workbook exists, and print its text for a human check
    python -m src.ours.benchmark.fill_chunk_ids --pkl <path>/docs_fixed_norm.pkl --verify benchmark/G02_benchmark_draft.xlsx
"""
from __future__ import annotations

import argparse
import pickle
import re


def norm(text: str) -> str:
    """Lower-case, transliterate German umlauts (the index stores ä as ae), strip punctuation."""
    text = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("é", "e"), ("è", "e")):
        text = text.replace(a, b)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def load_chunks(pkl_path: str) -> dict[str, dict]:
    with open(pkl_path, "rb") as fh:
        docs = pickle.load(fh)
    out = {}
    for d in docs:
        m = d.metadata
        text = m.get("original_text") or d.page_content
        out[m["chunk_id"]] = {"text": text, "norm": norm(text), "file": m.get("filename"),
                              "date": f"{m.get('year')}-{m.get('month'):02d}" if m.get("month") else str(m.get("year")),
                              "lang": m.get("language")}
    return out


def find(chunks: dict[str, dict], phrases: list[str], show: int = 10) -> list[str]:
    keys = [norm(p) for p in phrases]
    hits = [cid for cid, c in chunks.items() if all(k in c["norm"] for k in keys)]
    print(f"\n{phrases}: {len(hits)} chunk(s)")
    for cid in hits[:show]:
        c = chunks[cid]
        i = c["norm"].find(keys[0])
        print(f"  {cid} | {c['date']} {c['lang']} {c['file']}\n    …{c['norm'][max(0, i - 160): i + 160]}…")
    return hits


def verify(chunks: dict[str, dict], xlsx: str) -> None:
    import openpyxl
    ws = openpyxl.load_workbook(xlsx)["Cases"]
    for row in range(2, ws.max_row + 1):
        case_id, cell = ws.cell(row, 1).value, ws.cell(row, 10).value
        if not case_id:
            continue
        ids = [x.strip() for x in str(cell or "").split(";") if x.strip() and x.strip().lower() != "n/a"]
        if not ids:
            print(f"\n{case_id}: no chunk (abstention case: check the search log instead)")
            continue
        for cid in ids:
            c = chunks.get(cid)
            if c is None:
                print(f"\n{case_id}: {cid} NOT IN INDEX")
                continue
            print(f"\n{case_id}: {cid} | {c['date']} {c['lang']} {c['file']}\n  {c['text'][:700]}…")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkl", required=True)
    ap.add_argument("--find", nargs="*", default=None, help="phrases that must all appear in a chunk")
    ap.add_argument("--verify", default=None, help="benchmark workbook to verify")
    args = ap.parse_args()
    chunks = load_chunks(args.pkl)
    print(f"{len(chunks)} chunks loaded")
    if args.find:
        find(chunks, args.find)
    if args.verify:
        verify(chunks, args.verify)


if __name__ == "__main__":
    main()
