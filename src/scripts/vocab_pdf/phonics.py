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

# Hand-tuned General American (GA); eng-to-ipa is CMUdict-based (already AmE).
MANUAL_IPA: dict[str, str] = {
    "I": "/aɪ/",
    "a": "/ə/",
    "PE": "/ˌpiːˈiː/",
    "OK": "/ˌoʊˈkeɪ/",
    "Mr": "/ˈmɪstɚ/",
    "o'clock": "/əˈklɑːk/",
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
    # Drop syllable-separator dots (common on Wiktionary) so /ˈæl.ɪ.ɡeɪ.tɚ/ → /ˈælɪɡeɪtɚ/, closer to many learner / 百度-style prints.
    if raw.startswith("/") and raw.endswith("/") and len(raw) > 2:
        inner = raw[1:-1].replace(".", "")
        raw = f"/{inner}/"
    return raw


_ENG_TO_IPA_WARNED = False


def ipa_from_eng_to_ipa(word: str) -> str:
    """CMUdict → IPA via eng-to-ipa (American English inventory)."""
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


def _score_phonetic_us_preference(text: str, audio_url: str) -> int:
    """Prefer US (or neutral) over UK/AU when dictionaryapi.dev lists several phonetics."""
    t = text or ""
    a = (audio_url or "").lower()
    score = 0
    if re.search(r"[-_]uk\.mp3|[-.]uk[._]", a) or "uk.mp3" in a:
        score -= 8
    if re.search(r"[-_]us\.mp3|[-.]us[._]", a) or "us.mp3" in a:
        score += 10
    if "au.mp3" in a or re.search(r"[-_]au\.mp3", a):
        score -= 4
    if "oʊ" in t:
        score += 4
    if "əʊ" in t:
        score -= 4
    if "ɒ" in t:
        score -= 3
    if "ɑ" in t:
        score += 1
    # Full vowel ɪ in the syllable after primary stress often matches US learner transcriptions (vs schwa).
    if re.search(r"ˈ[^ˈˌ]*ɪ", t):
        score += 1
    return score


def _best_phonetic_from_dictionary_entry(entry: dict) -> str:
    """Pick the most US-like phonetic string from a free-dictionary-api.dev entry."""
    candidates: list[tuple[int, str]] = []
    top = entry.get("phonetic")
    if top and str(top).strip():
        candidates.append((_score_phonetic_us_preference(str(top), ""), str(top).strip()))
    for phon in entry.get("phonetics") or []:
        if not isinstance(phon, dict):
            continue
        t = phon.get("text")
        if not t or not str(t).strip():
            continue
        t = str(t).strip()
        candidates.append((_score_phonetic_us_preference(t, phon.get("audio") or ""), t))
    if not candidates:
        return ""
    candidates.sort(key=lambda x: (-x[0], -len(x[1])))
    return candidates[0][1]


def _lookup_ipa_dictionary_api(w: str) -> str:
    """Free dictionaryapi.dev — Wiktionary-style US transcriptions (learner-friendlier than CMU alone)."""
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(w, safe='')}"
    try:
        with urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        for entry in data:
            if not isinstance(entry, dict):
                continue
            best = _best_phonetic_from_dictionary_entry(entry)
            if best:
                return _format_ipa(best)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        pass
    return ""


def lookup_ipa_word(word: str, *, allow_network: bool = False) -> str:
    w = word.lower().replace("'", "'")
    if word in MANUAL_IPA:
        return MANUAL_IPA[word]
    if w in _IPA_CACHE and _IPA_CACHE[w]:
        return _IPA_CACHE[w]

    ipa = ""
    if allow_network:
        ipa = _lookup_ipa_dictionary_api(w)
    if not ipa:
        ipa = ipa_from_eng_to_ipa(word)
    if ipa:
        _IPA_CACHE[w] = ipa
        return ipa

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

    if use_network:
        for w in words:
            _IPA_CACHE.pop(w.lower(), None)

    total = len(words)
    mode = "offline + cache (CMU)" if not use_network else "Wiktionary US first, then CMU + cache"
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
