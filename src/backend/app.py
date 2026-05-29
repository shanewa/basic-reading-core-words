from __future__ import annotations

import json
import random
import sys
import time
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


@app.after_request
def add_no_cache_headers(response):
    # Prevent stale frontend assets causing old client logic to keep running.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


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
    delay = int(settings.get("answer_delay_ms", 150) or 150)
    if delay < 100 or delay > 1000:
        settings = STORAGE.upsert_settings({"answer_delay_ms": 150})
    return settings


def _pick_next_word(wordbank: dict, book_dir: str, settings: dict) -> dict | None:
    words = wordbank["words"]
    today = _today()
    reviewed_today = STORAGE.list_reviewed_word_ids(book_dir, today)
    due_ids = STORAGE.list_due_word_ids(book_dir, today)

    due_candidates = [w for w in words if w["id"] in due_ids and w["id"] not in reviewed_today]
    if due_candidates:
        return random.choice(due_candidates)

    # Bulk-load all known word ids once instead of N point queries.
    known_ids = STORAGE.list_known_word_ids(book_dir)
    new_candidates = [
        w
        for w in words
        if w["id"] not in known_ids and w["id"] not in reviewed_today
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
        "wrongAttempts": 0,
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
        patch["answer_delay_ms"] = max(100, min(1000, int(patch["answer_delay_ms"])))
    settings = STORAGE.upsert_settings(patch)
    return jsonify({"ok": True, "settings": settings})


@app.get("/api/session")
def api_session():
    t0 = time.perf_counter()
    settings = _ensure_default_settings()
    t1 = time.perf_counter()
    book_dir = settings["book_dir"]
    if not book_dir:
        return jsonify({"error": "no book selected"}), 400

    continue_learning = request.args.get("continue", "0") in {"1", "true", "True"}
    replay_word_id = request.args.get("wordId", "").strip()

    wordbank = load_wordbank(CFG.books_dir, book_dir)
    t2 = time.perf_counter()
    progress = STORAGE.progress_summary(book_dir, len(wordbank["words"]), _today())
    t3 = time.perf_counter()

    # Explicit replay (e.g. clicking "Previous") bypasses the daily-target gate.
    if replay_word_id:
        word = next((w for w in wordbank["words"] if w["id"] == replay_word_id), None)
        if not word:
            return jsonify({"error": "wordId not found in current book"}), 404
        q = _build_question(word, wordbank["words"], settings)
        t5 = time.perf_counter()
        print(
            f"[session] settings={(t1-t0)*1000:.0f}ms wordbank={(t2-t1)*1000:.0f}ms "
            f"progress={(t3-t2)*1000:.0f}ms build={(t5-t3)*1000:.0f}ms "
            f"TOTAL={(t5-t0)*1000:.0f}ms (replay)",
            flush=True,
        )
        return jsonify(
            {
                "done": False,
                "book": wordbank["book"],
                "question": q,
                "progress": progress,
                "dailyTarget": int(settings.get("daily_target", CFG.daily_target_default)),
                "replay": True,
                "favorited": STORAGE.is_favorite(book_dir, word["id"]),
            }
        )

    if (not continue_learning) and progress["todayReviewed"] >= int(settings.get("daily_target", CFG.daily_target_default)):
        print(f"[session] settings={(t1-t0)*1000:.0f}ms wordbank={(t2-t1)*1000:.0f}ms progress={(t3-t2)*1000:.0f}ms TOTAL={(t3-t0)*1000:.0f}ms (done)", flush=True)
        return jsonify({"done": True, "progress": progress, "question": None, "canContinue": True})

    word = _pick_next_word(wordbank, book_dir, settings)
    t4 = time.perf_counter()
    if not word:
        print(f"[session] settings={(t1-t0)*1000:.0f}ms wordbank={(t2-t1)*1000:.0f}ms progress={(t3-t2)*1000:.0f}ms pick={(t4-t3)*1000:.0f}ms TOTAL={(t4-t0)*1000:.0f}ms (no word)", flush=True)
        return jsonify({"done": True, "progress": progress, "question": None, "canContinue": False})

    q = _build_question(word, wordbank["words"], settings)
    t5 = time.perf_counter()
    print(
        f"[session] settings={(t1-t0)*1000:.0f}ms wordbank={(t2-t1)*1000:.0f}ms "
        f"progress={(t3-t2)*1000:.0f}ms pick={(t4-t3)*1000:.0f}ms build={(t5-t4)*1000:.0f}ms "
        f"TOTAL={(t5-t0)*1000:.0f}ms",
        flush=True,
    )
    return jsonify(
        {
            "done": False,
            "book": wordbank["book"],
            "question": q,
            "progress": progress,
            "dailyTarget": int(settings.get("daily_target", CFG.daily_target_default)),
            "favorited": STORAGE.is_favorite(book_dir, word["id"]),
        }
    )


@app.post("/api/favorites/toggle")
def api_favorites_toggle():
    payload = request.get_json(silent=True) or {}
    word_id = (payload.get("wordId") or "").strip()
    if not word_id:
        return jsonify({"error": "wordId required"}), 400
    settings = _ensure_default_settings()
    book_dir = settings["book_dir"]
    if not book_dir:
        return jsonify({"error": "no book selected"}), 400
    now_iso = datetime.utcnow().isoformat() + "Z"
    favorited = STORAGE.toggle_favorite(book_dir, word_id, now_iso)
    return jsonify({"ok": True, "wordId": word_id, "favorited": favorited})


@app.get("/api/favorites")
def api_favorites_list():
    settings = _ensure_default_settings()
    book_dir = settings["book_dir"]
    if not book_dir:
        return jsonify({"error": "no book selected"}), 400
    word_ids = STORAGE.list_favorites(book_dir)
    if not word_ids:
        return jsonify({"ok": True, "items": []})
    wordbank = load_wordbank(CFG.books_dir, book_dir)
    by_id = {w["id"]: w for w in wordbank["words"]}
    items = []
    for wid in word_ids:
        w = by_id.get(wid)
        if not w:
            # Word may have been removed from the book; surface it anyway.
            items.append({"wordId": wid, "headword": wid, "zhHans": "", "missing": True})
            continue
        items.append(
            {
                "wordId": wid,
                "headword": w.get("headword") or w.get("display") or wid,
                "zhHans": ((w.get("translation") or {}).get("zhHans")) or "",
            }
        )
    return jsonify({"ok": True, "items": items})


@app.post("/api/answer")
def api_answer():
    payload = request.get_json(silent=True) or {}
    qid = payload.get("questionId")
    user_answer = payload.get("answer")
    if not qid or qid not in QUESTION_CACHE:
        return jsonify({"error": "question expired or invalid"}), 400

    qinfo = QUESTION_CACHE[qid]
    settings = _ensure_default_settings()
    book_dir = settings["book_dir"]

    is_correct, base_quality = evaluate_answer(qinfo["mode"], qinfo["answer"], user_answer)

    today_s = _today()
    wrong_attempts = int(qinfo.get("wrongAttempts", 0))

    if not is_correct:
        qinfo["wrongAttempts"] = wrong_attempts + 1
        STORAGE.log_review(
            reviewed_at=datetime.utcnow().isoformat() + "Z",
            study_date=today_s,
            book_dir=book_dir,
            word_id=qinfo["wordId"],
            mode=qinfo["mode"],
            quality=1,
            is_correct=False,
            user_answer=json.dumps(user_answer, ensure_ascii=False),
        )
        return jsonify(
            {
                "ok": True,
                "isCorrect": False,
                "quality": 1,
                "stayOnQuestion": True,
                "wrongAttempts": qinfo["wrongAttempts"],
            }
        )

    # Correct answer: apply penalty based on wrong attempts before success.
    penalty = min(3, wrong_attempts)
    quality = max(0, int(base_quality) - penalty)

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

    # Question is completed only after correct answer.
    QUESTION_CACHE.pop(qid, None)

    return jsonify(
        {
            "ok": True,
            "isCorrect": is_correct,
            "quality": quality,
            "nextDueDate": updated.due_date,
            "intervalDays": updated.interval_days,
            "wrongAttempts": wrong_attempts,
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
