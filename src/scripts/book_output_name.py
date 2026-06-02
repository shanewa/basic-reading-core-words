#!/usr/bin/env python3
"""Print the PDF output filename for a book (used by Makefile)."""

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from vocab_pdf.config import load_book_config, resolve_output_filename


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: book_output_name.py <book-dir>", file=sys.stderr)
        return 1
    book_dir = Path(sys.argv[1]).resolve()
    config = load_book_config(book_dir / "book.json")
    print(resolve_output_filename(config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
