#!/usr/bin/env python3
"""Extract headwords from Cambridge KET Schools vocabulary PDF -> KET词汇.md (word_list format)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from pypdf import PdfReader

REPO = Path(__file__).resolve().parents[2]
DEFAULT_PDF = REPO / "books/KET-Key_English_Test/23387-ket-schools-vocabulary-list.pdf"
OUT_MD = REPO / "books/KET-Key_English_Test/KET词汇.md"

# Trailing part-of-speech block, e.g. (n), (v & n), (phr v), (adj, det, pron & adv)
_POS_TAIL = re.compile(r"\s+\(([a-z,\s/&0-9]+)\)\s*$", re.IGNORECASE)

# Section heading: single capital letter (column marker in PDF)
_SECTION_LETTER = re.compile(r"^[A-Z]\s*$")


def _join_continuation(prev: str, nxt: str) -> str:
    """Join PDF lines; glue split syllables like assista + nt (n) -> assistant (n)."""
    a, b = prev.rstrip(), nxt.strip()
    if a and b and re.match(r"^[a-z]{1,4}\s+\(", b) and a[-1].islower():
        return a + b
    return a + " " + b


def _plausible_headword(head: str) -> bool:
    h = head.strip()
    if not h or len(h) > 70:
        return False
    if "©" in h or "UCLES" in h or "Vocabulary List" in h or "VOCABULARY" in h:
        return False
    # Intro / title noise (whole-page text accidentally matched)
    if re.search(r"\b(?:June|January|February)\s+\d{4}\b", h) and "KET" in h:
        return False
    if h.count(" ") > 10:
        return False
    if len(h.split()) >= 5:
        return False
    if not re.match(r"^[A-Za-z0-9]", h):
        return False
    return True


def _split_headword(line: str) -> str | None:
    line = line.strip()
    if not line:
        return None
    m = _POS_TAIL.search(line)
    if not m:
        return None
    head = line[: m.start()].strip()
    if not head:
        return None
    return head


def extract_headwords(pdf_path: Path) -> list[str]:
    reader = PdfReader(str(pdf_path))
    words: list[str] = []
    seen: set[str] = set()

    for page in reader.pages:
        text = page.extract_text() or ""
        if re.search(r"^\s*Appendix\s+1\s*$", text, re.MULTILINE):
            break

        buf = ""
        for raw in text.splitlines():
            s = raw.strip()
            if not s:
                continue
            if s.startswith("\uf0b7") or s.startswith("•"):
                continue
            if _SECTION_LETTER.match(s):
                continue
            if re.match(r"^Appendix\b", s, re.I):
                buf = ""
                break

            if not buf:
                buf = s
            else:
                buf = _join_continuation(buf, s)

            if _POS_TAIL.search(buf):
                head = _split_headword(buf)
                buf = ""
                if not head or not _plausible_headword(head):
                    continue
                low = head.lower()
                if low in seen:
                    continue
                seen.add(low)
                words.append(head)

        if buf.strip() and _POS_TAIL.search(buf):
            head = _split_headword(buf)
            if head and _plausible_headword(head):
                low = head.lower()
                if low not in seen:
                    seen.add(low)
                    words.append(head)

    # Fix rare PDF glue errors; dedupe case-insensitive
    fixed: list[str] = []
    for w in words:
        if w == "wisheswith":
            fixed.extend(["wishes", "with"])
            continue
        fixed.append(w)
    out: list[str] = []
    seen2: set[str] = set()
    for w in fixed:
        k = w.lower()
        if k in seen2:
            continue
        seen2.add(k)
        out.append(w)
    return out


def main() -> int:
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT_MD
    if not pdf.is_file():
        print(f"PDF not found: {pdf}", file=sys.stderr)
        return 1
    words = extract_headwords(pdf)
    if len(words) < 800:
        print(f"Warning: only {len(words)} headwords extracted (expected ~1400+).", file=sys.stderr)
    header = (
        "# KET 词汇表\n"
        "# 来源：Cambridge English KET / KET for Schools vocabulary list (PDF)\n"
        "# 每行一词，供 word_list 解析器使用\n\n"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(header + "\n".join(words) + "\n", encoding="utf-8")
    print(f"Wrote {len(words)} words -> {out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
