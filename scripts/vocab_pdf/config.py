import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SourceSpec:
    path: str
    parser: str
    label: str


@dataclass
class BookConfig:
    name: str
    output: str
    seed: int
    sources: list[SourceSpec]
    translate_missing: bool = False
    fetch_ipa: bool = False  # if true, also try online dictionary API for IPA


def load_book_config(config_path: Path) -> BookConfig:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    sources = [
        SourceSpec(
            path=s["path"],
            parser=s["parser"],
            label=s["label"],
        )
        for s in data["sources"]
    ]
    return BookConfig(
        name=data.get("name", config_path.parent.name),
        output=data.get("output", "auto"),
        seed=int(data.get("seed", 42)),
        sources=sources,
        translate_missing=bool(data.get("translate_missing", False)),
        fetch_ipa=bool(data.get("fetch_ipa", False)),
    )


def resolve_output_filename(config: BookConfig) -> str:
    """PDF name from all vocabulary .md stems, unless output is a fixed filename."""
    out = (config.output or "").strip()
    if out and out.lower() != "auto":
        return out
    stems = [Path(s.path).stem for s in config.sources]
    if not stems:
        return "词汇表.pdf"
    return "_".join(stems) + ".pdf"


def resolve_output_path(book_dir: Path, config: BookConfig) -> Path:
    return book_dir / resolve_output_filename(config)
