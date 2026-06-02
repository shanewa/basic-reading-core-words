"""HTTP(S) with optional proxy from proxy.env or environment variables."""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path

# repo root: src/scripts/vocab_pdf/net.py -> parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROXY_LOADED = False


def _load_proxy_env_file() -> None:
    global _PROXY_LOADED
    if _PROXY_LOADED:
        return
    _PROXY_LOADED = True

    for name in ("proxy.env", ".proxy"):
        path = _REPO_ROOT / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key, val)
            else:
                url = line
                for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
                    os.environ.setdefault(key, url)
        break


def get_proxy_url() -> str | None:
    _load_proxy_env_file()
    return (
        os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("http_proxy")
    )


def urlopen(url: str, timeout: float = 10.0):
    proxy = get_proxy_url()
    if proxy:
        handlers = [urllib.request.ProxyHandler({"http": proxy, "https": proxy})]
        opener = urllib.request.build_opener(*handlers)
    else:
        opener = urllib.request.build_opener()
    return opener.open(url, timeout=timeout)
