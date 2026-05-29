from __future__ import annotations

import json
import random
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.backend.config import load_config
from src.backend.quiz import (
    build_image_question,
    build_meaning_question,
    build_typing_question,
    evaluate_answer,
    pick_modes,
)
from src.backend.scheduler import SM2State, update_sm2
from src.backend.storage import StudyStorage
from src.backend.wordbank import build_wordbank_for_book, list_books, load_wordbank

CFG = load_config()
STORAGE = StudyStorage(CFG.db_path)
QUESTION_CACHE: dict[str, dict] = {}

FRONTEND_DIR = CFG.repo_root / "src" / "frontend"
app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")


def _today() -> str:
    return date.today().isoformat()


def _ensure_default_settings() -> dict:
    settings = STORAGE.get_settings()
    books = list_books(CFG.books_dir)
    if not settings.get("book_dir") and books:
        settings = STORAGE.upsert_settings({"book_dir": books[0]["bookDir"]})
    if int(settings.get("daily_target", 0) or 0) <= 0:
        settings = STORAGE.upsert_settings({"daily_target": CFG.daily_target_default})
    if not CFG.image_mode_enabled and settings.get("mode_image"):
        settings = STORAGE.upsert_settings({"mode_image": False})
    typing_mode = str(settings.get("typing_mode", "")).strip()
    legacy_mode_map = {
        "full": "all_missing",
        "missing_vowels": "missing_multi_vowels",
    }
    if typing_mode in legacy_mode_map:
        settings = STORAGE.upsert_settings({"typing_mode": legacy_mode_map[typing_mode]})
        typing_mode = settings.get("typing_mode", "")
    if typing_mode not in {"all_missing", "missing_one_vowel", "missing_multi_vowels"}:
        settings = STORAGE.upsert_settings({"typing_mode": "missing_multi_vowels"})
    delay = int(settings.get("answer_delay_ms", 300) or 300)
    if delay < 100 or delay > 3000:
        settings = STORAGE.upsert_settings({"answer_delay_ms": 300})
    return settings


def _pick_next_word(wordbank: dict, book_dir: str, settings: dict) -> dict | None:
    words = wordbank["words"]
    today = _today()
    reviewed_today = STORAGE.list_reviewed_word_ids(book_dir, today)
    due_ids = STORAGE.list_due_word_ids(book_dir, today)

    due_candidates = [w for w in words if w["id"] in due_ids and w["id"] not in reviewed_today]
    if due_candidates:
        return random.choice(due_candidates)

    new_candidates = [
        w
        for w in words
        if STORAGE.get_word_state(book_dir, w["id"]) is None and w["id"] not in reviewed_today
    ]
    if new_candidates:
        return random.choice(new_candidates)

    fallback = [w for w in words if w["id"] in due_ids] or words
    return random.choice(fallback) if fallback else None


def _build_question(word: dict, all_words: list[dict], settings: dict) -> dict:
    rng = random.Random()
    mode = rng.choice(pick_modes(settings))

    if mode == "image" and not CFG.image_mode_enabled:
        mode = "meaning"

    if mode == "meaning":
        q = build_meaning_question(word, all_words, rng)
    elif mode == "typing":
        q = build_typing_question(word, rng, typing_mode=settings.get("typing_mode", "missing_one_vowel"))
    else:
        q = build_image_question(word, all_words, rng, provider=CFG.image_provider)

    qid = str(uuid.uuid4())
    source_items = word.get("sources") or []
    source_text = " / ".join(s.get("raw") or s.get("label") or "" for s in source_items if isinstance(s, dict))
    ipa_text = str((word.get("pronunciation") or {}).get("ipa") or "")
    QUESTION_CACHE[qid] = {
        "wordId": word["id"],
        "mode": q["type"],
        "answer": q["answer"],
    }
    q["questionId"] = qid
    q["wordId"] = word["id"]
    q["sourceText"] = source_text
    q["ipaText"] = ipa_text
    q.pop("answer", None)
    return q


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "time": datetime.utcnow().isoformat() + "Z"})


@app.get("/api/books")
def api_books():
    return jsonify({"books": list_books(CFG.books_dir)})


@app.post("/api/wordbank/rebuild")
def api_rebuild_wordbank():
    payload = request.get_json(silent=True) or {}
    book_dir = payload.get("bookDir")
    if not book_dir:
        return jsonify({"error": "bookDir is required"}), 400
    target = CFG.books_dir / book_dir
    if not target.is_dir():
        return jsonify({"error": "bookDir not found"}), 404
    path = build_wordbank_for_book(target, offline=True)
    return jsonify({"ok": True, "path": str(path.relative_to(CFG.repo_root))})


@app.get("/api/settings")
def api_get_settings():
    settings = _ensure_default_settings()
    return jsonify({"settings": settings})


@app.post("/api/settings")
def api_update_settings():
    payload = request.get_json(silent=True) or {}
    allowed = {
        "book_dir",
        "daily_target",
        "mode_meaning",
        "mode_image",
        "mode_typing",
        "typing_mode",
        "answer_delay_ms",
        "ui_language",
    }
    patch = {k: v for k, v in payload.items() if k in allowed}
    if "daily_target" in patch:
        patch["daily_target"] = max(1, int(patch["daily_target"]))
    if "typing_mode" in patch and patch["typing_mode"] not in {"all_missing", "missing_one_vowel", "missing_multi_vowels"}:
        patch["typing_mode"] = "missing_multi_vowels"
    if "answer_delay_ms" in patch:
        patch["answer_delay_ms"] = max(100, min(3000, int(patch["answer_delay_ms"])))
    settings = STORAGE.upsert_settings(patch)
    return jsonify({"ok": True, "settings": settings})


@app.get("/api/session")
def api_session():
    settings = _ensure_default_settings()
    book_dir = settings["book_dir"]
    if not book_dir:
        return jsonify({"error": "no book selected"}), 400

    continue_learning = request.args.get("continue", "0") in {"1", "true", "True"}

    wordbank = load_wordbank(CFG.books_dir, book_dir)
    progress = STORAGE.progress_summary(book_dir, len(wordbank["words"]), _today())

    if (not continue_learning) and progress["todayReviewed"] >= int(settings.get("daily_target", CFG.daily_target_default)):
        return jsonify({"done": True, "progress": progress, "question": None, "canContinue": True})

    word = _pick_next_word(wordbank, book_dir, settings)
    if not word:
        return jsonify({"done": True, "progress": progress, "question": None, "canContinue": False})

    q = _build_question(word, wordbank["words"], settings)
    return jsonify(
        {
            "done": False,
            "book": wordbank["book"],
            "question": q,
            "progress": progress,
            "dailyTarget": int(settings.get("daily_target", CFG.daily_target_default)),
        }
    )


@app.post("/api/answer")
def api_answer():
    payload = request.get_json(silent=True) or {}
    qid = payload.get("questionId")
    user_answer = payload.get("answer")
    if not qid or qid not in QUESTION_CACHE:
        return jsonify({"error": "question expired or invalid"}), 400

    qinfo = QUESTION_CACHE.pop(qid)
    settings = _ensure_default_settings()
    book_dir = settings["book_dir"]

    is_correct, quality = evaluate_answer(qinfo["mode"], qinfo["answer"], user_answer)

    today_s = _today()
    state_raw = STORAGE.get_word_state(book_dir, qinfo["wordId"]) or {
        "repetitions": 0,
        "interval_days": 0,
        "ef": 2.5,
        "due_date": today_s,
        "lapses": 0,
        "correct_streak": 0,
        "total_reviews": 0,
        "total_correct": 0,
    }
    prev = SM2State(
        repetitions=int(state_raw["repetitions"]),
        interval_days=int(state_raw["interval_days"]),
        ef=float(state_raw["ef"]),
        due_date=str(state_raw["due_date"]),
        lapses=int(state_raw["lapses"]),
        correct_streak=int(state_raw["correct_streak"]),
        total_reviews=int(state_raw["total_reviews"]),
        total_correct=int(state_raw["total_correct"]),
    )
    updated = update_sm2(prev, quality)
    STORAGE.upsert_word_state(book_dir, qinfo["wordId"], updated.__dict__, today_s)

    STORAGE.log_review(
        reviewed_at=datetime.utcnow().isoformat() + "Z",
        study_date=today_s,
        book_dir=book_dir,
        word_id=qinfo["wordId"],
        mode=qinfo["mode"],
        quality=quality,
        is_correct=is_correct,
        user_answer=json.dumps(user_answer, ensure_ascii=False),
    )

    return jsonify(
        {
            "ok": True,
            "isCorrect": is_correct,
            "quality": quality,
            "nextDueDate": updated.due_date,
            "intervalDays": updated.interval_days,
        }
    )


@app.get("/api/progress")
def api_progress():
    settings = _ensure_default_settings()
    book_dir = settings.get("book_dir")
    if not book_dir:
        return jsonify({"error": "no book selected"}), 400
    wordbank = load_wordbank(CFG.books_dir, book_dir)
    return jsonify({"progress": STORAGE.progress_summary(book_dir, len(wordbank["words"]), _today())})


@app.post("/api/reset")
def api_reset():
    settings = _ensure_default_settings()
    book_dir = settings.get("book_dir")
    if not book_dir:
        return jsonify({"error": "no book selected"}), 400
    STORAGE.reset_book_progress(book_dir)
    return jsonify({"ok": True})


@app.get("/")
def root_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:path>")
def static_proxy(path: str):
    target = FRONTEND_DIR / path
    if target.is_file():
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")


if __name__ == "__main__":
    _ensure_default_settings()
    app.run(host=CFG.host, port=CFG.port, debug=CFG.debug)
