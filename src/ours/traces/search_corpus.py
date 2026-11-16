"""Search the raw ETH news corpus (HKNews.zip) for terms, with context snippets.

Used to check whether an answer exists in the corpus *independently of
retrieval*. Needed for (a) judging abstentions as correct or false and
(b) validating benchmark cases in Step 2.

Usage (from the repo root; HKNews.zip lives on Drive / locally, never in git):
    python -m src.ours.traces.search_corpus --zip /path/to/HKNews.zip "Kübler" "Olaf"
    python -m src.ours.traces.search_corpus --zip HKNews.zip --all "Hong Kong" "Biennale"

By default a page matches if it contains ANY term; --all requires every term.
Matching is case-insensitive. Both EN and DE pages are searched.
"""
from __future__ import annotations

import argparse
import html
import re
import zipfile


def page_text(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="ignore")
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("terms", nargs="+")
    ap.add_argument("--zip", required=True, help="path to HKNews.zip")
    ap.add_argument("--all", action="store_true", help="require every term on the page")
    ap.add_argument("--context", type=int, default=160, help="characters of context per hit")
    ap.add_argument("--max-hits", type=int, default=2, help="snippets per page")
    args = ap.parse_args()

    pats = [re.compile(re.escape(t), re.I) for t in args.terms]
    n_pages = 0
    with zipfile.ZipFile(args.zip) as zf:
        for name in sorted(zf.namelist()):
            if not name.endswith(".html") or name.startswith("__MACOSX"):
                continue
            text = page_text(zf.read(name))
            found = [p for p in pats if p.search(text)]
            if not found or (args.all and len(found) < len(pats)):
                continue
            n_pages += 1
            print(f"\n=== {name}")
            for p in found:
                for m in list(p.finditer(text))[: args.max_hits]:
                    a, b = max(0, m.start() - args.context), m.end() + args.context
                    print(f"  [{p.pattern}] …{text[a:b]}…")
    print(f"\n{n_pages} page(s) matched {'all' if args.all else 'any'} of {args.terms}")


if __name__ == "__main__":
    main()
