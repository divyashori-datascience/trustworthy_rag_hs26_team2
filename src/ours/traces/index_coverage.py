"""Measure how much of the raw corpus actually made it into the shared index.

Compares the raw HTML pages (HKNews.zip) with the indexed chunks (docs_fixed_norm.pkl):
- how many pages are indexed at all
- for indexed pages, the share of sentences (>= 6 words) whose text appears in the chunks
- how often the first sentence (the article lead) is missing

Matching is approximate: text is lower-cased, umlauts transliterated, punctuation removed,
and a sentence counts as present if its first 60 normalised characters occur in the page's chunks.

Usage (from the repo root; needs langchain-core):
    python -m src.ours.traces.index_coverage --zip <path>/HKNews.zip --pkl <path>/docs_fixed_norm.pkl
"""
from __future__ import annotations

import argparse
import collections
import pickle
import re
import statistics
import zipfile

from src.ours.benchmark.fill_chunk_ids import norm
from src.ours.traces.search_corpus import page_text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True)
    ap.add_argument("--pkl", required=True)
    args = ap.parse_args()

    with open(args.pkl, "rb") as fh:
        docs = pickle.load(fh)
    by_page = collections.defaultdict(list)
    for d in docs:
        m = d.metadata
        by_page[(m["filename"], int(m["year"]), int(m["month"]), m["language"])].append(
            norm(m.get("original_text") or d.page_content))

    raw = {}
    with zipfile.ZipFile(args.zip) as zf:
        for name in zf.namelist():
            if not name.endswith(".html") or name.startswith("__MACOSX"):
                continue
            p = name.split("/")
            raw[(p[-1], int(p[2]), int(p[3]), p[1][:2])] = page_text(zf.read(name))

    covered, lead_missing, n = [], 0, 0
    for key, chunk_texts in by_page.items():
        if key not in raw:
            continue
        joined = " ".join(chunk_texts)
        sents = [s for s in re.split(r"(?<=[.!?])\s+", raw[key]) if len(s.split()) >= 6]
        if not sents:
            continue
        n += 1
        found = [norm(s)[:60] in joined for s in sents]
        covered.append(sum(found) / len(found))
        lead_missing += not found[0]

    print(f"raw pages: {len(raw)} | indexed pages: {len(by_page)} | chunks: {len(docs)}")
    print(f"pages not indexed: {len(raw) - len(by_page)} ({(len(raw) - len(by_page)) / len(raw):.0%})")
    print(f"indexed pages compared: {n}")
    print(f"sentence coverage per page: mean {statistics.mean(covered):.2f}, median {statistics.median(covered):.2f}")
    print(f"pages with < 80% of sentences indexed: {sum(c < 0.8 for c in covered) / n:.0%}")
    print(f"pages whose first sentence (lead) is missing: {lead_missing / n:.0%}")


if __name__ == "__main__":
    main()
