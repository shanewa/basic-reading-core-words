from dataclasses import dataclass, field

from .util import clean_headword


@dataclass
class WordEntry:
    english: str
    chinese: str = ""
    sources: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return clean_headword(self.english).lower()


def merge_entries(all_lists: list[list[WordEntry]]) -> list[WordEntry]:
    merged: dict[str, WordEntry] = {}
    for group in all_lists:
        for e in group:
            k = e.key
            if not k:
                continue
            if k not in merged:
                merged[k] = WordEntry(
                    english=clean_headword(e.english) or e.english,
                    chinese=e.chinese,
                    sources=list(e.sources),
                )
            else:
                cur = merged[k]
                if e.chinese and (not cur.chinese or len(e.chinese) > len(cur.chinese)):
                    cur.chinese = e.chinese
                for s in e.sources:
                    if s not in cur.sources:
                        cur.sources.append(s)
    return list(merged.values())
