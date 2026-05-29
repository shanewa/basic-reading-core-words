from __future__ import annotations

import random
import re


VOWELS = set("aeiou")


def _slug(text: str) -> str:
    value = text.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "word"


def normalize_typing(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[\.,!?;:'\"\(\)\[\]\{\}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _letters_only(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


def _mask_vowels(text: str) -> str:
    chars: list[str] = []
    for ch in text:
        if ch.lower() in VOWELS and ch.isalpha():
            chars.append("_")
        else:
            chars.append(ch)
    return "".join(chars)


def _missing_vowels(text: str) -> str:
    letters = _letters_only(text)
    return "".join(ch for ch in letters if ch in VOWELS)


def _vowel_groups(text: str) -> list[list[int]]:
    groups: list[list[int]] = []
    cur: list[int] = []
    for i, ch in enumerate(text):
        low = ch.lower()
        if not ch.isalpha():
            if cur:
                groups.append(cur)
                cur = []
            continue
        if low in VOWELS:
            cur.append(i)
        else:
            if cur:
                groups.append(cur)
                cur = []
    if cur:
        groups.append(cur)
    return groups


def _alpha_positions(text: str) -> list[int]:
    return [i for i, ch in enumerate(text) if ch.isalpha()]


def _build_masked_template(text: str, missing_positions: list[int]) -> tuple[str, str]:
    miss_set = set(missing_positions)
    chars: list[str] = []
    missing_letters: list[str] = []
    for i, ch in enumerate(text):
        if i in miss_set:
            chars.append("_")
            missing_letters.append(ch)
        else:
            chars.append(ch)
    return "".join(chars), "".join(missing_letters)


def pick_modes(settings: dict) -> list[str]:
    modes: list[str] = []
    if settings.get("mode_meaning", True):
        modes.append("meaning")
    if settings.get("mode_image", True):
        modes.append("image")
    if settings.get("mode_typing", True):
        modes.append("typing")
    return modes or ["meaning"]


def image_url_for_query(query: str, sig: int, provider: str = "loremflickr") -> str:
    safe = query.strip().replace(" ", ",")
    slug = _slug(query)
    provider = (provider or "loremflickr").strip().lower()

    if provider == "loremflickr":
        return f"https://loremflickr.com/600/420/{safe}?lock={sig}"
    if provider == "picsum":
        return f"https://picsum.photos/seed/{slug}-{sig}/600/420"
    if provider == "unsplash-source":
        return f"https://source.unsplash.com/600x420/?{safe}&sig={sig}"
    return f"https://loremflickr.com/600/420/{safe}?lock={sig}"


def build_meaning_question(word: dict, all_words: list[dict], rng: random.Random) -> dict:
    target_zh = word.get("translation", {}).get("zhHans") or word["headword"]
    pool = [
        w.get("translation", {}).get("zhHans")
        for w in all_words
        if w["id"] != word["id"] and w.get("translation", {}).get("zhHans")
    ]
    rng.shuffle(pool)
    distractors = []
    for item in pool:
        if item != target_zh and item not in distractors:
            distractors.append(item)
        if len(distractors) == 2:
            break
    while len(distractors) < 2:
        distractors.append(word["headword"])

    options = [target_zh] + distractors
    rng.shuffle(options)

    return {
        "type": "meaning",
        "prompt": word["headword"],
        "subPrompt": word.get("pronunciation", {}).get("ipa") or "",
        "options": [{"id": f"opt_{i}", "text": t} for i, t in enumerate(options)],
        "answer": target_zh,
    }


def build_typing_question(word: dict, rng: random.Random, typing_mode: str = "missing_one_vowel") -> dict:
    headword = word["headword"]
    mode = (typing_mode or "missing_one_vowel").strip().lower()
    if mode not in {"all_missing", "missing_one_vowel", "missing_multi_vowels"}:
        mode = "missing_one_vowel"

    alpha_pos = _alpha_positions(headword)
    vowel_groups = _vowel_groups(headword)
    missing_positions: list[int] = []

    if mode == "all_missing":
        missing_positions = list(alpha_pos)
    elif mode == "missing_multi_vowels":
        for g in vowel_groups:
            missing_positions.extend(g)
    else:
        if vowel_groups:
            missing_positions = list(rng.choice(vowel_groups))
        else:
            # No vowels: fallback to one random alphabetic letter.
            if alpha_pos:
                missing_positions = [rng.choice(alpha_pos)]

    if not missing_positions and alpha_pos:
        missing_positions = [rng.choice(alpha_pos)]

    mask_template, missing_letters = _build_masked_template(headword, missing_positions)

    return {
        "type": "typing",
        "typingMode": mode,
        "prompt": word["translation"].get("zhHans") or headword,
        "subPrompt": "",
        "maskTemplate": mask_template,
        "missingCount": len(missing_letters),
        "inputHint": "Fill the missing letters",
        "answer": {
            "style": "masked_completion",
            "full": headword,
            "missing": missing_letters,
        },
    }


def build_image_question(
    word: dict,
    all_words: list[dict],
    rng: random.Random,
    provider: str = "loremflickr",
) -> dict:
    target = word["headword"]
    unrelated = rng.choice([w["headword"] for w in all_words if w["id"] != word["id"]])

    options = [
        {
            "id": "img_0",
            "imageUrl": image_url_for_query(target, rng.randint(1, 100000), provider=provider),
            "isRelated": True,
        },
        {
            "id": "img_1",
            "imageUrl": image_url_for_query(target, rng.randint(1, 100000), provider=provider),
            "isRelated": True,
        },
        {
            "id": "img_2",
            "imageUrl": image_url_for_query(unrelated, rng.randint(1, 100000), provider=provider),
            "isRelated": False,
        },
    ]
    rng.shuffle(options)
    answer_ids = sorted([o["id"] for o in options if o["isRelated"]])

    return {
        "type": "image",
        "prompt": target,
        "subPrompt": "Select two related images",
        "options": [{"id": o["id"], "imageUrl": o["imageUrl"]} for o in options],
        "answer": answer_ids,
    }


def evaluate_answer(mode: str, expected, user_answer) -> tuple[bool, int]:
    if mode == "meaning":
        ok = str(user_answer or "") == str(expected)
        return ok, 4 if ok else 1
    if mode == "typing":
        user_text = str(user_answer or "")
        if isinstance(expected, dict):
            style = expected.get("style", "masked_completion")
            full = str(expected.get("full", ""))
            if style == "masked_completion":
                missing = str(expected.get("missing", ""))
                ok = (
                    _letters_only(user_text) == _letters_only(missing)
                    or normalize_typing(user_text) == normalize_typing(full)
                )
            else:
                ok = normalize_typing(user_text) == normalize_typing(full)
        else:
            ok = normalize_typing(user_text) == normalize_typing(str(expected or ""))
        return ok, 5 if ok else 2
    if mode == "image":
        got = sorted(list(user_answer or []))
        ok = got == sorted(list(expected or []))
        return ok, 4 if ok else 1
    return False, 0
