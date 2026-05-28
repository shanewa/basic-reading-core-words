import argparse
import sys
from pathlib import Path

from .build import build_book


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a shuffled printable vocabulary PDF from a book folder."
    )
    parser.add_argument(
        "--book-dir",
        type=Path,
        required=True,
        help="Folder containing book.json and *.md vocabulary files",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to book.json (default: <book-dir>/book.json)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Do not call translation or IPA APIs (use translations.json only)",
    )
    args = parser.parse_args(argv)

    book_dir = args.book_dir.resolve()
    if not book_dir.is_dir():
        print(f"Not a directory: {book_dir}", file=sys.stderr)
        return 1

    config_path = args.config or (book_dir / "book.json")
    if not config_path.is_file():
        print(f"Missing config: {config_path}", file=sys.stderr)
        return 1

    build_book(book_dir, config_path, offline=args.offline)
    return 0
