#!/usr/bin/env python3
"""Build books/<book>/ipa.json for offline PDF builds. Run once when network works."""

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

from vocab_pdf.build import load_entries
from vocab_pdf.config import load_book_config
from vocab_pdf.phonics import lookup_ipa_word, save_ipa_cache
from vocab_pdf.util import clean_headword
import re


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--book-dir", type=Path, required=True)
    p.add_argument("--online", action="store_true", help="Also query dictionary API")
    args = p.parse_args()

    book_dir = args.book_dir.resolve()
    config = load_book_config(book_dir / "book.json")
    entries = load_entries(book_dir, config)

    words: set[str] = set()
    for e in entries:
        head = clean_headword(e.english)
        for piece in head.split():
            if re.search(r"[a-zA-Z]", piece):
                words.add(piece)

    for w in sorted(words):
        lookup_ipa_word(w, allow_network=args.online)

    out = book_dir / "ipa.json"
    save_ipa_cache(book_dir)
    cache = book_dir / ".cache/ipa.json"
    if cache.is_file():
        out.write_text(cache.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
