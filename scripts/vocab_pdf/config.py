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
        output=data.get("output", "词汇表（打印版）.pdf"),
        seed=int(data.get("seed", 42)),
        sources=sources,
    )
