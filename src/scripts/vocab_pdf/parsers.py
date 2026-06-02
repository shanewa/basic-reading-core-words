import re
from pathlib import Path

from .entries import WordEntry


def parse_grade_table(path: Path, label: str) -> list[WordEntry]:
    """Markdown with ## semester and ### Unit N tables."""
    text = path.read_text(encoding="utf-8")
    entries: list[WordEntry] = []
    semester = ""
    unit = ""

    for line in text.splitlines():
        if line.startswith("## ") and not line.startswith("###"):
            semester = line.replace("##", "").strip()
            continue
        m_unit = re.match(r"^### Unit (\d+)", line)
        if m_unit:
            unit = f"U{m_unit.group(1)}"
            continue
        m_row = re.match(r"^\| ([^|]+) \| ([^|]+) \|$", line.strip())
        if not m_row or m_row.group(1) in ("英文", "------"):
            continue
        en = m_row.group(1).strip()
        zh = m_row.group(2).strip()
        src = f"{label}·{semester}·{unit}"
        entries.append(WordEntry(english=en, chinese=zh, sources=[src]))
    return entries


def parse_word_list(path: Path, label: str) -> list[WordEntry]:
    """One English word or phrase per line."""
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^\s*\d+\|(.+)$", line)
        word = m.group(1).strip() if m else line
        if re.match(r"^\d+$", word):
            continue
        entries.append(WordEntry(english=word, chinese="", sources=[label]))
    return entries


PARSERS = {
    "grade_table": parse_grade_table,
    "word_list": parse_word_list,
}


def parse_source(path: Path, parser: str, label: str) -> list[WordEntry]:
    if parser not in PARSERS:
        raise ValueError(f"Unknown parser {parser!r}; use one of {list(PARSERS)}")
    return PARSERS[parser](path, label)
