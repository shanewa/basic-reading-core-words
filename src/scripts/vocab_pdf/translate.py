import json
import time
import urllib.parse
from pathlib import Path

from .entries import WordEntry
from .net import urlopen
from .log import log
from .util import clean_headword


class TranslationStore:
    """Local translations.json + optional .cache; online API only if enabled."""

    def __init__(
        self,
        book_dir: Path,
        *,
        translate_missing: bool = False,
        api_timeout: float = 8.0,
        api_retries: int = 2,
    ) -> None:
        self.book_dir = book_dir
        self.translate_missing = translate_missing
        self.api_timeout = api_timeout
        self.api_retries = api_retries
        self._local: dict[str, str] = {}
        self._cache: dict[str, str] = {}
        self._load_files()

    def _load_files(self) -> None:
        for name, target in (
            ("translations.json", self._local),
            (".cache/translations.json", self._cache),
        ):
            path = self.book_dir / name
            if path.is_file():
                data = json.loads(path.read_text(encoding="utf-8"))
                target.update({k.lower(): v for k, v in data.items()})

    def lookup(self, head: str) -> str | None:
        key = head.lower()
        if key in self._local:
            return self._local[key]
        if key in self._cache:
            return self._cache[key]
        return None

    def save_cache(self) -> None:
        if not self._cache:
            return
        cache_dir = self.book_dir / ".cache"
        cache_dir.mkdir(exist_ok=True)
        path = cache_dir / "translations.json"
        merged = dict(self._local)
        merged.update(self._cache)
        path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def translate_online(self, text: str) -> str | None:
        q = urllib.parse.quote(text)
        url = (
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=en&tl=zh-CN&dt=t&q={q}"
        )
        last_err: Exception | None = None
        for attempt in range(1, self.api_retries + 1):
            log(f"  [translate] API {attempt}/{self.api_retries}: {text!r} ...")
            try:
                with urlopen(url, timeout=self.api_timeout) as resp:
                    data = json.loads(resp.read().decode())
                zh = "".join(part[0] for part in data[0] if part[0])
                log(f"  [translate] done: {text!r} -> {zh!r}")
                return zh
            except Exception as exc:
                last_err = exc
                log(f"  [translate] failed: {text!r} ({exc})")
                if attempt < self.api_retries:
                    time.sleep(1.5 * attempt)
        log(f"  [translate] giving up on {text!r} ({last_err})")
        return None


def fill_chinese(
    entries: list[WordEntry],
    book_dir: Path,
    *,
    translate_missing: bool = False,
    offline: bool = False,
) -> None:
    store = TranslationStore(
        book_dir,
        translate_missing=translate_missing and not offline,
    )
    missing = [e for e in entries if not e.chinese]
    total = len(missing)
    if total == 0:
        log("[translate] all entries already have Chinese, skipping.")
        return

    local_hits = sum(1 for e in missing if store.lookup(clean_headword(e.english)))
    log(
        f"[translate] {total} entries need Chinese "
        f"({local_hits} in translations.json/cache)"
    )

    if offline:
        translate_missing = False
        log("[translate] offline mode: will not call translation API")

    api_count = 0
    done = 0
    for e in missing:
        head = clean_headword(e.english)
        zh = store.lookup(head)
        if zh:
            e.chinese = zh
            done += 1
            continue

        if not translate_missing:
            e.chinese = head
            done += 1
            if done % 50 == 0 or done == total:
                log(f"[translate] progress: {done}/{total} (no API, English fallback)")
            continue

        done += 1
        api_count += 1
        log(f"[translate] progress: {done}/{total} {head}")
        zh = store.translate_online(head)
        if zh:
            e.chinese = zh
            store._cache[head.lower()] = zh
        else:
            e.chinese = head

    store.save_cache()
    if api_count:
        log(f"[translate] finished: {api_count} API call(s)")
    else:
        log(f"[translate] finished: no API calls")
