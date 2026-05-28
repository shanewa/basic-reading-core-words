import re


def clean_headword(en: str) -> str:
    en = en.strip()
    en = re.sub(r"\s*\(.*$", "", en)
    en = re.sub(r"\s*=.*$", "", en)
    return en.strip()
