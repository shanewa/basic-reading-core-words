import json
import urllib.parse
import urllib.request

from .entries import WordEntry
from .log import log
from .util import clean_headword

_CN_CACHE: dict[str, str] = {}


def translate_zh(text: str) -> str:
    q = urllib.parse.quote(text)
    url = (
        "https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl=en&tl=zh-CN&dt=t&q={q}"
    )
    log(f"  [translate] calling API for: {text!r} ...")
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        zh = "".join(part[0] for part in data[0] if part[0])
        log(f"  [translate] done: {text!r} -> {zh!r}")
        return zh
    except Exception as exc:
        log(f"  [translate] failed: {text!r} ({exc}), keeping English")
        return text


def fill_chinese(entries: list[WordEntry]) -> None:
    missing = [e for e in entries if not e.chinese]
    total = len(missing)
    if total == 0:
        log("[translate] all entries already have Chinese, skipping.")
        return

    log(f"[translate] start: {total} words need translation (network, may take a while)")
    done = 0
    for e in missing:
        head = clean_headword(e.english)
        if head in _CN_CACHE:
            e.chinese = _CN_CACHE[head]
            done += 1
            if done % 20 == 0 or done == total:
                log(f"[translate] progress: {done}/{total} (cached)")
            continue
        done += 1
        log(f"[translate] progress: {done}/{total} {head}")
        e.chinese = translate_zh(head)
        _CN_CACHE[head] = e.chinese
    log(f"[translate] finished: {total} words")
