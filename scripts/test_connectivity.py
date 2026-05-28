#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test network access used by vocabulary PDF build (Google Translate, dictionary IPA)."""

from __future__ import annotations

import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from vocab_pdf.net import get_proxy_url, urlopen


def _probe(
    name: str,
    url: str,
    *,
    timeout: float = 10.0,
    parse_ok=None,
) -> bool:
    print(f"\n[{name}]")
    print(f"  URL: {url[:80]}{'...' if len(url) > 80 else ''}")
    print(f"  timeout: {timeout}s")
    t0 = time.perf_counter()
    try:
        with urlopen(url, timeout=timeout) as resp:
            body = resp.read()
        elapsed = time.perf_counter() - t0
        print(f"  HTTP: OK ({len(body)} bytes, {elapsed:.2f}s)")
        if parse_ok:
            parse_ok(body)
        return True
    except ssl.SSLError as exc:
        print(f"  FAIL: SSL error — {exc}")
    except urllib.error.HTTPError as exc:
        print(f"  FAIL: HTTP {exc.code} — {exc.reason}")
    except urllib.error.URLError as exc:
        print(f"  FAIL: {exc.reason}")
    except TimeoutError:
        print(f"  FAIL: timed out after {timeout}s")
    except Exception as exc:
        print(f"  FAIL: {type(exc).__name__}: {exc}")
    return False


def test_google_translate(timeout: float = 10.0) -> bool:
    word = "hello"
    q = urllib.parse.quote(word)
    url = (
        "https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl=en&tl=zh-CN&dt=t&q={q}"
    )

    def check(body: bytes) -> None:
        data = json.loads(body.decode())
        zh = "".join(part[0] for part in data[0] if part[0])
        print(f"  sample: {word!r} -> {zh!r}")

    return _probe("Google Translate", url, timeout=timeout, parse_ok=check)


def test_dictionary_api(timeout: float = 10.0) -> bool:
    word = "hello"
    url = (
        "https://api.dictionaryapi.dev/api/v2/entries/en/"
        f"{urllib.parse.quote(word, safe='')}"
    )

    def check(body: bytes) -> None:
        data = json.loads(body.decode())
        phonetic = data[0].get("phonetic") or "(no phonetic field)"
        print(f"  sample: {word!r} phonetic = {phonetic}")

    return _probe("Dictionary API (IPA)", url, timeout=timeout, parse_ok=check)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Test connectivity for online translation / IPA used by make pdf."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Request timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--translate-only",
        action="store_true",
        help="Only test Google Translate",
    )
    parser.add_argument(
        "--ipa-only",
        action="store_true",
        help="Only test dictionary API",
    )
    args = parser.parse_args(argv)

    print("Network connectivity test for basic-reading-core-400-words")
    print("=" * 56)
    proxy = get_proxy_url()
    if proxy:
        print(f"Proxy: {proxy}")
    else:
        print("Proxy: (none — set proxy.env or HTTP_PROXY)")

    tests: list[tuple[str, bool]] = []
    if not args.ipa_only:
        tests.append(("Google Translate", test_google_translate(args.timeout)))
    if not args.translate_only:
        tests.append(("Dictionary API", test_dictionary_api(args.timeout)))

    print("\n" + "=" * 56)
    print("Summary:")
    all_ok = True
    for label, ok in tests:
        status = "OK" if ok else "FAIL"
        print(f"  {label}: {status}")
        all_ok = all_ok and ok

    if all_ok:
        print("\nAll checks passed. You can set translate_missing / fetch_ipa in book.json.")
        return 0

    print(
        "\nSome checks failed. PDF build can still use translations.json and eng-to-ipa offline."
    )
    print("Fix network/proxy/firewall, or keep translate_missing=false in book.json.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
