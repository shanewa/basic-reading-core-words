from pathlib import Path

from .config import BookConfig, load_book_config, resolve_output_path
from .entries import merge_entries
from .log import log
from .parsers import parse_source
from .pdf_build import build_pdf
from .phonics import prefetch_ipa
from .translate import fill_chinese


def load_entries(book_dir: Path, config: BookConfig):
    groups = []
    for spec in config.sources:
        path = book_dir / spec.path
        if not path.is_file():
            raise FileNotFoundError(f"Missing vocabulary file: {path}")
        groups.append(parse_source(path, spec.parser, spec.label))
    return merge_entries(groups)


def build_book(
    book_dir: Path,
    config_path: Path | None = None,
    *,
    offline: bool = False,
) -> Path:
    book_dir = book_dir.resolve()
    cfg_path = config_path or (book_dir / "book.json")
    config = load_book_config(cfg_path)

    log(f"Book: {config.name}")
    if offline:
        log("Offline mode enabled (no translation / IPA network requests).")
    entries = load_entries(book_dir, config)
    log(f"Merged {len(entries)} unique entries.")

    fill_chinese(
        entries,
        book_dir,
        translate_missing=config.translate_missing,
        offline=offline,
    )
    use_ipa_network = config.fetch_ipa and not offline
    prefetch_ipa(entries, book_dir, use_network=use_ipa_network)

    out = resolve_output_path(book_dir, config)
    log(f"[pdf] start: {out.name}")
    build_pdf(entries, out, seed=config.seed, include_ipa=True)
    log("All done.")
    return out
