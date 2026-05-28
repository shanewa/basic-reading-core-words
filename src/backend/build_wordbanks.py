from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.backend.wordbank import build_wordbank_for_book, list_books


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    books_dir = repo_root / "books"

    books = list_books(books_dir)
    if not books:
        print("No books found under books/.")
        return 1

    print(f"Found {len(books)} book(s). Building wordbank.web.json ...")
    for book in books:
        book_dir_name = book["bookDir"]
        out = build_wordbank_for_book(books_dir / book_dir_name, offline=True)
        print(f"  OK: {out.relative_to(repo_root)}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
