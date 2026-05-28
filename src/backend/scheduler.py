from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class SM2State:
    repetitions: int = 0
    interval_days: int = 0
    ef: float = 2.5
    due_date: str = ""
    lapses: int = 0
    correct_streak: int = 0
    total_reviews: int = 0
    total_correct: int = 0


def clamp_quality(q: int) -> int:
    return max(0, min(5, int(q)))


def update_sm2(state: SM2State, quality: int, on_date: date | None = None) -> SM2State:
    q = clamp_quality(quality)
    today = on_date or date.today()

    repetitions = state.repetitions
    interval_days = state.interval_days
    ef = state.ef
    lapses = state.lapses
    correct_streak = state.correct_streak

    if q < 3:
        repetitions = 0
        interval_days = 1
        lapses += 1
        correct_streak = 0
    else:
        if repetitions == 0:
            interval_days = 1
        elif repetitions == 1:
            interval_days = 6
        else:
            interval_days = max(1, int(round(interval_days * ef)))
        repetitions += 1
        correct_streak += 1

    ef = ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    ef = max(1.3, ef)

    due = today + timedelta(days=interval_days)

    return SM2State(
        repetitions=repetitions,
        interval_days=interval_days,
        ef=ef,
        due_date=due.isoformat(),
        lapses=lapses,
        correct_streak=correct_streak,
        total_reviews=state.total_reviews + 1,
        total_correct=state.total_correct + (1 if q >= 3 else 0),
    )
