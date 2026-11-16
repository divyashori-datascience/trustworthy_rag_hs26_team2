"""Fill the 'Evidence chunk ID' column of our benchmark workbook from the indexed chunks.

For each case, looks up every chunk in ``docs_fixed_norm.pkl`` (the exact chunks the
reference system retrieves from) that contains the case's key phrase, and writes the
matching chunk IDs into column J. Also prints the chunk text so a human can confirm it.

Usage (from the repo root; needs langchain-core to unpickle the Documents):
    python -m src.ours.benchmark.fill_chunk_ids \
        --pkl /path/to/docs_fixed_norm.pkl \
        --xlsx benchmark/G02_benchmark_draft.xlsx

    # just look up phrases, no workbook changes:
    python -m src.ours.benchmark.fill_chunk_ids --pkl ... --find "Olaf Kübler" "e-Sling"
"""
from __future__ import annotations

import argparse
import pickle
import re

# Key phrase per case: short, distinctive text copied from the evidence passage.
KEY_PHRASES = {
    "G02-001": ["around 350 talented young chemists"],
    "G02-002": ["molecular force sensor in the tendon cells"],
    "G02-003": ["variant called E756del", "tropical disease malaria"],
    "G02-004": ["With 1160 Swiss francs per year", "CHF 250 for the autumn semester 2020/2021"],
    "G02-005": ["Ralph Eichler, President of ETH Zurich", "under ETH President Lino Guzzella"],
    "G02-006": ["21 Nobel Laureates", "22 Nobel Prize laureates"],
    "G02-009": ["dass dies der falsche Weg wäre"],
    "G02-011": ["142 private und kommunale Bauten", "1. Januar 2025"],
    "G02-012": ["Founded in August 2017, the start-up Fixposition", "Lukas Meier und Zhenzhong Su"],
    "G02-013": ["engaged critically with the ever-increasing pace", "has been ETH President since 1 January 2019"],
    "G02-014": ["founding of the Swiss Data Science Center in February"],
}


def load_chunks(pkl_path: str) -> dict[str, str]:
    with open(pkl_path, "rb") as fh:
        docs = pickle.load(fh)
    out = {}
    for d in docs:
        text = d.metadata.get("original_text") or d.page_content
        out[d.metadata["chunk_id"]] = re.sub(r"\s+", " ", text)
    return out


def find(chunks: dict[str, str], phrase: str) -> list[str]:
    p = re.compile(re.escape(phrase), re.I)
    return [cid for cid, text in chunks.items() if p.search(text)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkl", required=True)
    ap.add_argument("--xlsx", default=None)
    ap.add_argument("--find", nargs="*", default=None, help="ad-hoc phrases to look up")
    args = ap.parse_args()

    chunks = load_chunks(args.pkl)
    print(f"{len(chunks)} chunks loaded")

    if args.find:
        for ph in args.find:
            ids = find(chunks, ph)
            print(f"\n'{ph}': {len(ids)} chunk(s)")
            for cid in ids[:10]:
                t = chunks[cid]
                i = t.lower().find(ph.lower())
                print(f"  {cid}: …{t[max(0, i - 150): i + 150]}…")
        return

    import openpyxl
    wb = openpyxl.load_workbook(args.xlsx)
    ws = wb["Cases"]
    for row in range(2, ws.max_row + 1):
        case_id = ws.cell(row, 1).value
        if case_id not in KEY_PHRASES:
            continue
        found = []
        for ph in KEY_PHRASES[case_id]:
            ids = find(chunks, ph)
            print(f"{case_id} '{ph}': {ids or 'NOT FOUND'}")
            found += [i for i in ids if i not in found]
        ws.cell(row, 10).value = " ; ".join(found) if found else "NOT FOUND in indexed chunks: check"
    wb.save(args.xlsx)
    print(f"\nupdated {args.xlsx}. Open the chunks above and confirm each one by eye.")


if __name__ == "__main__":
    main()
