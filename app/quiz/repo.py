"""Доступ к БД для банка вопросов: темы, approved-вопросы, попытки.

Выдача пользователям — исключительно status='approved' (см. CLAUDE.md).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import timedelta

import aiosqlite

from app.srs import DEFAULT_EASINESS_FACTOR, sm2_update
from app.timeutils import today_msk

QUIZ_SESSION_SIZE = 5

# Тема считается «слабым местом», только если по ней накопилось достаточно
# попыток — иначе одна неудача на старте будет ложно выглядеть как проблема.
# Общий порог для /stats в боте и для Mini App API — единый источник правды.
WEAK_TOPIC_MIN_ATTEMPTS = 3
WEAK_TOPIC_THRESHOLD_PCT = 60


def is_weak_topic(total: int, correct: int) -> bool:
    if total < WEAK_TOPIC_MIN_ATTEMPTS:
        return False
    pct = correct / total * 100
    return pct < WEAK_TOPIC_THRESHOLD_PCT


@dataclass
class Topic:
    id: int
    slug: str
    title: str


@dataclass
class Question:
    id: int
    topic_id: int
    type: str
    difficulty: int
    body: str
    options_json: str | None
    correct_key: str | None
    correct_answer: str | None
    tolerance_pct: float | None
    explanation: str
    source: str | None
    status: str


def _row_to_question(row: aiosqlite.Row) -> Question:
    return Question(
        id=row["id"],
        topic_id=row["topic_id"],
        type=row["type"],
        difficulty=row["difficulty"],
        body=row["body"],
        options_json=row["options_json"],
        correct_key=row["correct_key"],
        correct_answer=row["correct_answer"],
        tolerance_pct=row["tolerance_pct"],
        explanation=row["explanation"],
        source=row["source"],
        status=row["status"],
    )


async def list_topics(conn: aiosqlite.Connection) -> list[Topic]:
    cursor = await conn.execute("SELECT id, slug, title FROM topics ORDER BY sort_order")
    rows = await cursor.fetchall()
    return [Topic(id=r["id"], slug=r["slug"], title=r["title"]) for r in rows]


async def get_topic(conn: aiosqlite.Connection, topic_id: int) -> Topic | None:
    cursor = await conn.execute("SELECT id, slug, title FROM topics WHERE id = ?", (topic_id,))
    row = await cursor.fetchone()
    return Topic(id=row["id"], slug=row["slug"], title=row["title"]) if row else None


async def pick_session_question_ids(
    conn: aiosqlite.Connection,
    topic_id: int,
    difficulty: int | None = None,
    size: int = QUIZ_SESSION_SIZE,
) -> list[int]:
    """Случайно выбирает id approved-вопросов темы (и опционально сложности)
    для одной сессии квиза."""
    if difficulty is None:
        cursor = await conn.execute(
            "SELECT id FROM questions WHERE topic_id = ? AND status = 'approved'",
            (topic_id,),
        )
    else:
        cursor = await conn.execute(
            "SELECT id FROM questions "
            "WHERE topic_id = ? AND status = 'approved' AND difficulty = ?",
            (topic_id, difficulty),
        )
    rows = await cursor.fetchall()
    ids = [r["id"] for r in rows]
    random.shuffle(ids)
    return ids[:size]


async def get_question(conn: aiosqlite.Connection, question_id: int) -> Question | None:
    cursor = await conn.execute(
        """
        SELECT id, topic_id, type, difficulty, body, options_json, correct_key,
               correct_answer, tolerance_pct, explanation, source, status
        FROM questions WHERE id = ? AND status = 'approved'
        """,
        (question_id,),
    )
    row = await cursor.fetchone()
    return _row_to_question(row) if row else None


async def record_attempt(
    conn: aiosqlite.Connection,
    user_id: int,
    question_id: int,
    session_id: str,
    user_answer: str | None,
    is_correct: bool,
) -> None:
    await conn.execute(
        """
        INSERT INTO attempts (user_id, question_id, session_id, user_answer, is_correct)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, question_id, session_id, user_answer, int(is_correct)),
    )
    await conn.commit()


async def topic_stats(conn: aiosqlite.Connection, user_id: int) -> list[tuple[str, int, int]]:
    """Возвращает (title, всего_попыток, верных) по темам, где у пользователя есть попытки."""
    cursor = await conn.execute(
        """
        SELECT t.title, COUNT(*) AS total, SUM(a.is_correct) AS correct
        FROM attempts a
        JOIN questions q ON q.id = a.question_id
        JOIN topics t ON t.id = q.topic_id
        WHERE a.user_id = ?
        GROUP BY t.id
        ORDER BY t.sort_order
        """,
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [(r["title"], r["total"], r["correct"] or 0) for r in rows]


async def upsert_review_after_attempt(
    conn: aiosqlite.Connection, user_id: int, question_id: int, is_correct: bool
) -> None:
    """Обновляет расписание повторения вопроса по упрощённому SM-2 после
    каждой попытки (и верной, и неверной)."""
    cursor = await conn.execute(
        "SELECT easiness_factor, interval_days, repetitions FROM review_schedule "
        "WHERE user_id = ? AND question_id = ?",
        (user_id, question_id),
    )
    row = await cursor.fetchone()
    ef, interval, reps = (
        (row["easiness_factor"], row["interval_days"], row["repetitions"])
        if row
        else (DEFAULT_EASINESS_FACTOR, 0, 0)
    )

    new_ef, new_interval, new_reps = sm2_update(ef, interval, reps, is_correct)
    due_date = (today_msk() + timedelta(days=new_interval)).isoformat()

    await conn.execute(
        """
        INSERT INTO review_schedule
            (user_id, question_id, easiness_factor, interval_days, repetitions, due_date)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, question_id) DO UPDATE SET
            easiness_factor = excluded.easiness_factor,
            interval_days = excluded.interval_days,
            repetitions = excluded.repetitions,
            due_date = excluded.due_date,
            last_reviewed_at = datetime('now')
        """,
        (user_id, question_id, new_ef, new_interval, new_reps, due_date),
    )
    await conn.commit()


async def get_due_question_ids(
    conn: aiosqlite.Connection, user_id: int, limit: int = QUIZ_SESSION_SIZE
) -> list[int]:
    today_str = today_msk().isoformat()
    cursor = await conn.execute(
        """
        SELECT rs.question_id FROM review_schedule rs
        JOIN questions q ON q.id = rs.question_id
        WHERE rs.user_id = ? AND rs.due_date <= ? AND q.status = 'approved'
        ORDER BY rs.due_date
        LIMIT ?
        """,
        (user_id, today_str, limit),
    )
    rows = await cursor.fetchall()
    return [r["question_id"] for r in rows]


async def count_due_questions(conn: aiosqlite.Connection, user_id: int) -> int:
    today_str = today_msk().isoformat()
    cursor = await conn.execute(
        "SELECT COUNT(*) FROM review_schedule WHERE user_id = ? AND due_date <= ?",
        (user_id, today_str),
    )
    (count,) = await cursor.fetchone()
    return count
