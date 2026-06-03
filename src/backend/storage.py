from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date
from pathlib import Path


DEFAULT_SETTINGS = {
    "book_dir": "",
    "daily_target": 20,
    "mode_meaning": True,
    "mode_image": False,
    "mode_typing": True,
    # When true, wordbank rebuild may call the free dictionary API for US-style IPA (needs network).
    "fetch_ipa": False,
    # Default typing style: partial phonics omission mode.
    "typing_mode": "missing_multi_vowels",
    "answer_delay_ms": 150,
    "ui_language": "zh",
    "child_name": "",
    "avatar_ext": "",  # set when an avatar has been uploaded (e.g. "png").
}


class StudyStorage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Persistent single connection — avoids the per-request open/close
        # overhead which is catastrophically slow on /mnt/c (WSL).
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            isolation_level=None,  # autocommit; we manage transactions explicitly.
        )
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        # WAL gives much better read/write concurrency; synchronous=NORMAL is
        # safe for our single-user app and dramatically reduces fsync waits.
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA temp_store=MEMORY")
        self._settings_cache: dict | None = None
        self._init_db()

    @contextmanager
    def conn(self):
        # Serialize access to the single connection; SQLite connections are
        # not safe for concurrent use across threads even with check_same_thread.
        # We run in autocommit (isolation_level=None) so each statement is
        # its own transaction — sufficient for this single-user app.
        with self._lock:
            yield self._conn

    def _init_db(self) -> None:
        with self.conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS word_state (
                    book_dir TEXT NOT NULL,
                    word_id TEXT NOT NULL,
                    repetitions INTEGER NOT NULL DEFAULT 0,
                    interval_days INTEGER NOT NULL DEFAULT 0,
                    ef REAL NOT NULL DEFAULT 2.5,
                    due_date TEXT NOT NULL,
                    last_review_date TEXT,
                    lapses INTEGER NOT NULL DEFAULT 0,
                    correct_streak INTEGER NOT NULL DEFAULT 0,
                    total_reviews INTEGER NOT NULL DEFAULT 0,
                    total_correct INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (book_dir, word_id)
                );

                CREATE TABLE IF NOT EXISTS review_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reviewed_at TEXT NOT NULL,
                    study_date TEXT NOT NULL,
                    book_dir TEXT NOT NULL,
                    word_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    quality INTEGER NOT NULL,
                    is_correct INTEGER NOT NULL,
                    user_answer TEXT
                );

                CREATE TABLE IF NOT EXISTS favorites (
                    book_dir TEXT NOT NULL,
                    word_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (book_dir, word_id)
                );
                """
            )

    def get_settings(self) -> dict:
        if self._settings_cache is not None:
            return dict(self._settings_cache)
        with self.conn() as conn:
            rows = conn.execute("SELECT key, value FROM user_settings").fetchall()
        settings = dict(DEFAULT_SETTINGS)
        for r in rows:
            value = r["value"]
            if r["key"] in {"daily_target", "answer_delay_ms"}:
                settings[r["key"]] = int(value)
            elif r["key"] in {"mode_meaning", "mode_image", "mode_typing", "fetch_ipa"}:
                settings[r["key"]] = value == "1"
            else:
                settings[r["key"]] = value
        self._settings_cache = settings
        return dict(settings)

    def upsert_settings(self, patch: dict) -> dict:
        merged = self.get_settings()
        merged.update(patch)
        with self.conn() as conn:
            for k, v in merged.items():
                if isinstance(v, bool):
                    val = "1" if v else "0"
                else:
                    val = str(v)
                conn.execute(
                    """
                    INSERT INTO user_settings(key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value
                    """,
                    (k, val),
                )
        self._settings_cache = dict(merged)
        return merged

    def get_word_state(self, book_dir: str, word_id: str) -> dict | None:
        with self.conn() as conn:
            row = conn.execute(
                "SELECT * FROM word_state WHERE book_dir=? AND word_id=?",
                (book_dir, word_id),
            ).fetchone()
        return dict(row) if row else None

    def upsert_word_state(self, book_dir: str, word_id: str, state: dict, today: str) -> None:
        with self.conn() as conn:
            conn.execute(
                """
                INSERT INTO word_state(
                    book_dir, word_id, repetitions, interval_days, ef, due_date,
                    last_review_date, lapses, correct_streak, total_reviews, total_correct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(book_dir, word_id) DO UPDATE SET
                    repetitions=excluded.repetitions,
                    interval_days=excluded.interval_days,
                    ef=excluded.ef,
                    due_date=excluded.due_date,
                    last_review_date=excluded.last_review_date,
                    lapses=excluded.lapses,
                    correct_streak=excluded.correct_streak,
                    total_reviews=excluded.total_reviews,
                    total_correct=excluded.total_correct
                """,
                (
                    book_dir,
                    word_id,
                    state["repetitions"],
                    state["interval_days"],
                    state["ef"],
                    state["due_date"],
                    today,
                    state["lapses"],
                    state["correct_streak"],
                    state["total_reviews"],
                    state["total_correct"],
                ),
            )

    def log_review(
        self,
        *,
        reviewed_at: str,
        study_date: str,
        book_dir: str,
        word_id: str,
        mode: str,
        quality: int,
        is_correct: bool,
        user_answer: str,
    ) -> None:
        with self.conn() as conn:
            conn.execute(
                """
                INSERT INTO review_log(
                    reviewed_at, study_date, book_dir, word_id, mode, quality, is_correct, user_answer
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reviewed_at,
                    study_date,
                    book_dir,
                    word_id,
                    mode,
                    quality,
                    1 if is_correct else 0,
                    user_answer,
                ),
            )

    def count_today_reviews(self, book_dir: str, today: str) -> int:
        with self.conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM review_log WHERE book_dir=? AND study_date=?",
                (book_dir, today),
            ).fetchone()
        return int(row["c"]) if row else 0

    def list_reviewed_word_ids(self, book_dir: str, today: str) -> set[str]:
        with self.conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT word_id FROM review_log WHERE book_dir=? AND study_date=?",
                (book_dir, today),
            ).fetchall()
        return {r["word_id"] for r in rows}

    def list_known_word_ids(self, book_dir: str) -> set[str]:
        with self.conn() as conn:
            rows = conn.execute(
                "SELECT word_id FROM word_state WHERE book_dir=?",
                (book_dir,),
            ).fetchall()
        return {r["word_id"] for r in rows}

    def list_due_word_ids(self, book_dir: str, today: str) -> set[str]:
        with self.conn() as conn:
            rows = conn.execute(
                "SELECT word_id FROM word_state WHERE book_dir=? AND due_date<=?",
                (book_dir, today),
            ).fetchall()
        return {r["word_id"] for r in rows}

    def list_word_states_for_book(self, book_dir: str) -> dict[str, dict]:
        """All SM-2 rows for a book, keyed by word_id."""
        with self.conn() as conn:
            rows = conn.execute(
                "SELECT * FROM word_state WHERE book_dir=?",
                (book_dir,),
            ).fetchall()
        return {str(r["word_id"]): dict(r) for r in rows}

    def review_log_stats_by_word(self, book_dir: str) -> dict[str, dict[str, int]]:
        """Per-word counts from review_log (includes wrong attempts)."""
        with self.conn() as conn:
            rows = conn.execute(
                """
                SELECT word_id,
                       COUNT(*) AS attempts,
                       COALESCE(SUM(is_correct), 0) AS correct_attempts
                FROM review_log
                WHERE book_dir=?
                GROUP BY word_id
                """,
                (book_dir,),
            ).fetchall()
        return {
            str(r["word_id"]): {
                "attempts": int(r["attempts"] or 0),
                "correctAttempts": int(r["correct_attempts"] or 0),
            }
            for r in rows
        }

    def progress_summary(self, book_dir: str, total_words: int, today: str) -> dict:
        with self.conn() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS learned,
                    SUM(CASE WHEN due_date <= ? THEN 1 ELSE 0 END) AS due
                FROM word_state
                WHERE book_dir=?
                """,
                (today, book_dir),
            ).fetchone()
            stats = conn.execute(
                """
                SELECT COUNT(*) AS c, COALESCE(SUM(is_correct), 0) AS ok
                FROM review_log
                WHERE book_dir=? AND study_date=?
                """,
                (book_dir, today),
            ).fetchone()
            completed = conn.execute(
                """
                SELECT COUNT(DISTINCT word_id) AS completed_words
                FROM review_log
                WHERE book_dir=? AND study_date=? AND is_correct=1
                """,
                (book_dir, today),
            ).fetchone()
        learned = int(row["learned"] or 0)
        due = int(row["due"] or 0)
        today_count = int(stats["c"] or 0)
        today_ok = int(stats["ok"] or 0)
        today_completed_words = int(completed["completed_words"] or 0)
        return {
            "totalWords": total_words,
            "learnedWords": learned,
            "newWords": max(0, total_words - learned),
            "dueWords": due,
            # Use completed word count so retries do not exhaust daily quota.
            "todayReviewed": today_completed_words,
            "todayCorrect": today_ok,
            "todayAttempts": today_count,
            "todayAccuracy": (today_ok / today_count) if today_count else 0.0,
        }

    def is_favorite(self, book_dir: str, word_id: str) -> bool:
        with self.conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM favorites WHERE book_dir=? AND word_id=?",
                (book_dir, word_id),
            ).fetchone()
        return row is not None

    def toggle_favorite(self, book_dir: str, word_id: str, now_iso: str) -> bool:
        """Returns the new favorited state (True if now favorited)."""
        with self.conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM favorites WHERE book_dir=? AND word_id=?",
                (book_dir, word_id),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO favorites(book_dir, word_id, created_at) VALUES (?, ?, ?)",
                    (book_dir, word_id, now_iso),
                )
                return True
            conn.execute(
                "DELETE FROM favorites WHERE book_dir=? AND word_id=?",
                (book_dir, word_id),
            )
            return False

    def list_favorites(self, book_dir: str) -> list[str]:
        with self.conn() as conn:
            rows = conn.execute(
                "SELECT word_id FROM favorites WHERE book_dir=? ORDER BY created_at DESC",
                (book_dir,),
            ).fetchall()
        return [r["word_id"] for r in rows]

    def count_word_states_by_book_dir(self) -> list[tuple[str, int]]:
        """For each book_dir, how many SM-2 rows exist (descending by count)."""
        with self.conn() as conn:
            rows = conn.execute(
                """
                SELECT book_dir, COUNT(*) AS c
                FROM word_state
                GROUP BY book_dir
                ORDER BY c DESC
                """
            ).fetchall()
        return [(str(r["book_dir"]), int(r["c"])) for r in rows]

    def migrate_book_dir(self, old: str, new: str) -> tuple[int, int, int]:
        """Move all study rows from a stale folder name ``old`` to ``new``.

        Used when the vocabulary book directory was renamed or ``book_dir`` in
        settings was auto-corrected. Never drops rows except PK conflicts on
        ``word_state`` / ``favorites``, where the incoming (old) row wins by
        deleting the duplicate stub on ``new`` first.

        Returns counts ``(word_state_updated, review_log_updated, favorites_updated)``.
        """
        if not old or not new or old == new:
            return (0, 0, 0)
        with self.conn() as conn:
            conn.execute(
                """
                DELETE FROM word_state
                WHERE book_dir = ?
                  AND word_id IN (SELECT word_id FROM word_state WHERE book_dir = ?)
                """,
                (new, old),
            )
            cur = conn.execute(
                "UPDATE word_state SET book_dir = ? WHERE book_dir = ?",
                (new, old),
            )
            ws_n = cur.rowcount or 0
            conn.execute(
                """
                DELETE FROM favorites
                WHERE book_dir = ?
                  AND word_id IN (SELECT word_id FROM favorites WHERE book_dir = ?)
                """,
                (new, old),
            )
            cur = conn.execute(
                "UPDATE favorites SET book_dir = ? WHERE book_dir = ?",
                (new, old),
            )
            fav_n = cur.rowcount or 0
            cur = conn.execute(
                "UPDATE review_log SET book_dir = ? WHERE book_dir = ?",
                (new, old),
            )
            log_n = cur.rowcount or 0
        return (ws_n, log_n, fav_n)

    def apply_book_dir_renames_file(self, books_dir: Path) -> None:
        """Apply ``src/data/book_dir_renames.json`` if present: ``{"old_dir": "new_dir"}``.

        Use when you renamed a folder under ``books/`` so SQLite rows keyed by the
        old name are moved to the new folder name. File is gitignored with other
        ``src/data/*`` contents; see ``book_dir_renames.example.json`` in repo root.
        """
        path = self.db_path.parent / "book_dir_renames.json"
        if not path.is_file():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return
        if not isinstance(raw, dict):
            return
        for old, new in raw.items():
            old_s, new_s = str(old).strip(), str(new).strip()
            if not old_s or not new_s or old_s == new_s:
                continue
            np = books_dir / new_s
            if not (np.is_dir() and (np / "book.json").is_file()):
                continue
            self.migrate_book_dir(old_s, new_s)

    def reset_book_progress(self, book_dir: str) -> None:
        with self.conn() as conn:
            conn.execute("DELETE FROM word_state WHERE book_dir=?", (book_dir,))
            conn.execute("DELETE FROM review_log WHERE book_dir=?", (book_dir,))
            conn.execute("DELETE FROM favorites WHERE book_dir=?", (book_dir,))
