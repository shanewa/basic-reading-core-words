from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Package `scripts` lives under src/scripts; ensure src/ is on sys.path.
_SRC_ROOT = Path(__file__).resolve().parents[1]
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from scripts.vocab_pdf.build import load_entries
from scripts.vocab_pdf.config import load_book_config
from scripts.vocab_pdf.examples import example_sentence
from scripts.vocab_pdf.phonics import phonics_display, prefetch_ipa, to_ipa
from scripts.vocab_pdf.translate import fill_chinese
from scripts.vocab_pdf.util import clean_headword


def slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "word"


def parse_source(raw: str) -> dict:
    parts = raw.split("·")
    label = parts[0] if parts else raw
    semester = parts[1] if len(parts) > 1 else None
    unit = parts[2] if len(parts) > 2 else None
    return {
        "label": label,
        "semester": semester,
        "unit": unit,
        "raw": raw,
    }


def infer_tags(source_labels: list[str]) -> list[str]:
    joined = " ".join(source_labels)
    tags: list[str] = []
    if "一年级" in joined:
        tags.append("grade1")
    if "二年级" in joined:
        tags.append("grade2")
    if "基础阅读400" in joined:
        tags.append("core400")
    return tags


def build_wordbank_for_book(book_dir: Path, *, offline: bool = True, fetch_ipa: bool | None = None) -> Path:
    cfg_path = book_dir / "book.json"
    config = load_book_config(cfg_path)
    effective_fetch = config.fetch_ipa if fetch_ipa is None else fetch_ipa

    entries = load_entries(book_dir, config)
    fill_chinese(
        entries,
        book_dir,
        translate_missing=config.translate_missing,
        offline=offline,
    )
    prefetch_ipa(entries, book_dir, use_network=(effective_fetch and not offline))

    words = []
    for idx, entry in enumerate(sorted(entries, key=lambda e: e.english.lower()), start=1):
        head = clean_headword(entry.english)
        if not head:
            continue
        source_objs = [parse_source(s) for s in entry.sources]
        source_labels = [s["label"] for s in source_objs]
        word_id = slugify(head)
        words.append(
            {
                "id": word_id,
                "headword": head,
                "display": entry.english,
                "normalized": head.lower(),
                "kind": "phrase" if " " in head else "word",
                "translation": {
                    "zhHans": entry.chinese or head,
                    "source": "book_or_cache",
                },
                "pronunciation": {
                    "phonics": phonics_display(head),
                    "ipa": to_ipa(head, allow_network=effective_fetch and not offline),
                    "source": "cache_or_generated",
                },
                "examples": [
                    {
                        "en": example_sentence(head, entry.chinese or head),
                        "zhHans": None,
                        "source": "generated",
                    }
                ],
                "sources": source_objs,
                "tags": infer_tags(source_labels),
                "assets": {
                    "image": None,
                    "audio": None,
                },
                "meta": {
                    "order": idx,
                    "isPhrase": " " in head,
                },
            }
        )

    payload = {
        "schemaVersion": 1,
        "book": {
            "id": slugify(config.name),
            "name": config.name,
            "outputPdf": config.output,
            "seed": config.seed,
            "sourceFiles": [
                {
                    "path": s.path,
                    "parser": s.parser,
                    "label": s.label,
                }
                for s in config.sources
            ],
        },
        "words": words,
    }

    out_path = book_dir / "wordbank.web.json"
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out_path


_LEGACY_BOOK_DIR_RENAMES: dict[str, str] = {
    "新交际一二年级": "新交际一二年级和基础阅读",
}


def resolve_book_directory(
    books_dir: Path,
    book_dir_name: str,
    *,
    known_books: list[dict] | None = None,
) -> str | None:
    """Return a ``book_dir`` that exists on disk (``book.json`` present).

    If the stored name is missing (e.g. folder was renamed), try known legacy
    mappings, then fall back to the first book from ``known_books`` / scan.
    """
    books = known_books if known_books is not None else list_books(books_dir)
    if not books:
        return None

    def is_valid(n: str) -> bool:
        if not n.strip():
            return False
        p = books_dir / n.strip()
        return p.is_dir() and (p / "book.json").is_file()

    name = (book_dir_name or "").strip()
    if not name:
        return books[0]["bookDir"]
    if is_valid(name):
        return name.strip()
    alt = _LEGACY_BOOK_DIR_RENAMES.get(name)
    if alt and is_valid(alt):
        return alt
    return books[0]["bookDir"]


def list_books(books_dir: Path) -> list[dict]:
    result = []
    for d in sorted(books_dir.iterdir()):
        if not d.is_dir():
            continue
        cfg = d / "book.json"
        if not cfg.is_file():
            continue
        data = json.loads(cfg.read_text(encoding="utf-8"))
        name = data.get("name", d.name)
        result.append(
            {
                "bookDir": d.name,
                "id": slugify(name),
                "name": name,
                "wordbankPath": str((d / "wordbank.web.json").relative_to(books_dir.parent)),
            }
        )
    return result


_WORDBANK_CACHE: dict[str, tuple[float, dict]] = {}


def load_wordbank(books_dir: Path, book_dir_name: str) -> dict:
    path = books_dir / book_dir_name / "wordbank.web.json"
    if not path.is_file():
        build_wordbank_for_book(books_dir / book_dir_name, offline=True)
    key = str(path.resolve())
    mtime = path.stat().st_mtime
    cached = _WORDBANK_CACHE.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    _WORDBANK_CACHE[key] = (mtime, data)
    return data
