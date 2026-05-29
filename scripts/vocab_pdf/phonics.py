import json
import re
import urllib.error
import urllib.parse
from pathlib import Path

from .net import urlopen
from .util import clean_headword

VOWEL_TEAMS = sorted(
    [
        "eigh", "igh", "ough", "augh", "air", "ear", "eer", "ere", "are", "ore", "ure",
        "tion", "sion", "ai", "ay", "ea", "ee", "ei", "ey", "ie", "oa", "oe", "oi", "oy",
        "oo", "ou", "ow", "ue", "au", "aw", "ew", "ui", "ar", "er", "ir", "or", "ur",
        "ch", "sh", "th", "wh", "ph", "ck", "ng", "nk", "all", "alk", "old", "ost", "ind",
        "ight", "str", "spl", "spr", "scr", "squ", "bl", "br", "cl", "cr", "dr", "fl", "fr",
        "gl", "gr", "pl", "pr", "sc", "sk", "sl", "sm", "sn", "sp", "st", "sw", "tr", "tw",
    ],
    key=len,
    reverse=True,
)

MANUAL_IPA: dict[str, str] = {
    "I": "/aɪ/",
    "a": "/ə/",
    "PE": "/ˌpiːˈiː/",
    "OK": "/ˌəʊˈkeɪ/",
    "Mr": "/ˈmɪstə(r)/",
    "o'clock": "/əˈklɒk/",
    "Chinese": "/ˌtʃaɪˈniːz/",
    "maths": "/mæθs/",
}

_IPA_CACHE: dict[str, str] = {}


def load_ipa_cache(book_dir: Path) -> None:
    for rel in ("ipa.json", ".cache/ipa.json"):
        path = book_dir / rel
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for k, v in data.items():
            if v:
                _IPA_CACHE[k.lower()] = v


def save_ipa_cache(book_dir: Path) -> None:
    cache_dir = book_dir / ".cache"
    cache_dir.mkdir(exist_ok=True)
    path = cache_dir / "ipa.json"
    path.write_text(
        json.dumps(_IPA_CACHE, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def segment_graphemes(word: str) -> list[str]:
    w = re.sub(r"[^a-zA-Z'-]", "", word)
    if not w:
        return [word] if word else []

    parts: list[str] = []
    i = 0
    lower = w.lower()

    while i < len(w):
        matched = False
        for team in VOWEL_TEAMS:
            if lower.startswith(team, i):
                parts.append(w[i : i + len(team)])
                i += len(team)
                matched = True
                break
        if matched:
            continue
        ch = w[i]
        if ch.lower() in "aeiou":
            parts.append(ch)
            i += 1
            if i < len(w) and w[i].lower() == "e" and i == len(w) - 1:
                parts.append(w[i])
                i += 1
            continue
        parts.append(ch)
        i += 1
    return parts


def phonics_display(english: str) -> str:
    tokens = []
    for piece in english.split():
        if piece in ("I", "a", "A"):
            tokens.append(piece.lower() if piece == "a" else piece)
            continue
        sub = segment_graphemes(piece)
        tokens.append("-".join(sub) if sub else piece)
    return " ".join(tokens)


def _format_ipa(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    if not raw.startswith("/"):
        raw = f"/{raw}/"
    return raw


_ENG_TO_IPA_WARNED = False


def ipa_from_eng_to_ipa(word: str) -> str:
    global _ENG_TO_IPA_WARNED
    try:
        import eng_to_ipa as eta
    except ImportError:
        if not _ENG_TO_IPA_WARNED:
            from .log import log

            log("[ipa] eng-to-ipa not installed; run: pip install eng-to-ipa")
            _ENG_TO_IPA_WARNED = True
        return ""
    try:
        converted = eta.convert(word)
        if converted and converted.lower() != word.lower():
            return _format_ipa(converted)
    except Exception:
        pass
    return ""


def lookup_ipa_word(word: str, *, allow_network: bool = False) -> str:
    w = word.lower().replace("'", "'")
    if word in MANUAL_IPA:
        return MANUAL_IPA[word]
    if w in _IPA_CACHE and _IPA_CACHE[w]:
        return _IPA_CACHE[w]

    ipa = ipa_from_eng_to_ipa(word)
    if ipa:
        _IPA_CACHE[w] = ipa
        return ipa

    if not allow_network:
        _IPA_CACHE[w] = ""
        return ""

    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(w, safe='')}"
    try:
        with urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        for entry in data:
            if entry.get("phonetic"):
                ipa = _format_ipa(entry["phonetic"])
                _IPA_CACHE[w] = ipa
                return ipa
            for phon in entry.get("phonetics", []):
                if phon.get("text"):
                    ipa = _format_ipa(phon["text"])
                    _IPA_CACHE[w] = ipa
                    return ipa
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        pass
    _IPA_CACHE[w] = ""
    return ""


def to_ipa(english: str, *, allow_network: bool = False) -> str:
    head = clean_headword(english)
    if not head or not re.search(r"[a-zA-Z]", head):
        return ""
    ipas = []
    for piece in head.split():
        ipa = lookup_ipa_word(piece, allow_network=allow_network)
        if ipa:
            ipas.append(ipa)
    return " ".join(ipas)


def phonics_column(english: str, *, include_ipa: bool = True, allow_network: bool = False) -> str:
    """e.g. beef -> b-ee-f  /biːf/"""
    seg = phonics_display(english)
    if not include_ipa:
        return seg
    ipa = to_ipa(english, allow_network=allow_network)
    if ipa:
        return f"{seg}  {ipa}"
    return seg


def prefetch_ipa(entries, book_dir: Path, *, use_network: bool = False) -> None:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from .log import log

    load_ipa_cache(book_dir)

    words: set[str] = set()
    for e in entries:
        head = clean_headword(e.english)
        for piece in head.split():
            if re.search(r"[a-zA-Z]", piece):
                words.add(piece)

    total = len(words)
    mode = "offline + cache" if not use_network else "offline, cache, then online"
    log(f"[ipa] start: building IPA for {total} headwords ({mode})...")
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(lookup_ipa_word, w, allow_network=use_network): w
            for w in sorted(words)
        }
        done = 0
        for fut in as_completed(futures):
            fut.result()
            done += 1
            if done % 50 == 0 or done == total:
                log(f"[ipa] progress: {done}/{total}")
    save_ipa_cache(book_dir)
    filled = sum(1 for w in words if _IPA_CACHE.get(w.lower(), ""))
    log(f"[ipa] finished: {filled}/{total} with IPA")
    if filled < total:
        log("[ipa] tip: pip install -r requirements.txt (needs eng-to-ipa for offline IPA)")
