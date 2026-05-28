import json
import re
import urllib.error
import urllib.parse
import urllib.request

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


def lookup_ipa_word(word: str) -> str:
    w = word.lower().replace("'", "'")
    if word in MANUAL_IPA:
        return MANUAL_IPA[word]
    if w in _IPA_CACHE:
        return _IPA_CACHE[w]

    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(w, safe='')}"
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        for entry in data:
            if entry.get("phonetic"):
                ipa = entry["phonetic"].strip()
                if not ipa.startswith("/"):
                    ipa = f"/{ipa}/"
                _IPA_CACHE[w] = ipa
                return ipa
            for phon in entry.get("phonetics", []):
                if phon.get("text"):
                    ipa = phon["text"].strip()
                    if not ipa.startswith("/"):
                        ipa = f"/{ipa}/"
                    _IPA_CACHE[w] = ipa
                    return ipa
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        pass
    _IPA_CACHE[w] = ""
    return ""


def to_ipa(english: str) -> str:
    head = clean_headword(english)
    if not head or not re.search(r"[a-zA-Z]", head):
        return ""
    ipas = []
    for piece in head.split():
        ipa = lookup_ipa_word(piece)
        if ipa:
            ipas.append(ipa)
    return " ".join(ipas)


def phonics_column(english: str) -> str:
    seg = phonics_display(english)
    ipa = to_ipa(english)
    if ipa:
        return f"{seg}  {ipa}"
    return seg


def prefetch_ipa(entries) -> None:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from .log import log

    words: set[str] = set()
    for e in entries:
        head = clean_headword(e.english)
        for piece in head.split():
            if re.search(r"[a-zA-Z]", piece):
                words.add(piece)

    total = len(words)
    log(f"[ipa] start: fetching phonetics for {total} headwords (network)...")
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(lookup_ipa_word, w): w for w in sorted(words)}
        done = 0
        for fut in as_completed(futures):
            fut.result()
            done += 1
            if done % 50 == 0 or done == total:
                log(f"[ipa] progress: {done}/{total}")
    log(f"[ipa] finished: {total} headwords")
