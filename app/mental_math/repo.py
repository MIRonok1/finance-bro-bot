"""Доступ к БД для модуля «Быстрый счёт»: попытки и агрегированная статистика."""

from __future__ import annotations

import aiosqlite


async def record_attempt(
    conn: aiosqlite.Connection,
    user_id: int,
    kind: str,
    difficulty: int,
    is_correct: bool,
    elapsed_ms: int,
) -> None:
    await conn.execute(
        """
        INSERT INTO mental_math_attempts (user_id, kind, difficulty, is_correct, elapsed_ms)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, kind, difficulty, int(is_correct), elapsed_ms),
    )
    await conn.commit()


async def update_stats(
    conn: aiosqlite.Connection, user_id: int, is_correct: bool, current_streak: int
) -> tuple[int, int, int]:
    """Обновляет best_streak (максимум) и счётчики попыток; возвращает
    (best_streak, total_attempts, total_correct) после обновления."""
    await conn.execute(
        """
        INSERT INTO mental_math_stats (user_id, best_streak, total_attempts, total_correct)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            best_streak = MAX(mental_math_stats.best_streak, excluded.best_streak),
            total_attempts = mental_math_stats.total_attempts + 1,
            total_correct = mental_math_stats.total_correct + excluded.total_correct,
            updated_at = datetime('now')
        """,
        (user_id, current_streak, int(is_correct)),
    )
    await conn.commit()

    cursor = await conn.execute(
        "SELECT best_streak, total_attempts, total_correct FROM mental_math_stats "
        "WHERE user_id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    return row["best_streak"], row["total_attempts"], row["total_correct"]


async def get_stats(conn: aiosqlite.Connection, user_id: int) -> tuple[int, int, int]:
    cursor = await conn.execute(
        "SELECT best_streak, total_attempts, total_correct FROM mental_math_stats "
        "WHERE user_id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return 0, 0, 0
    return row["best_streak"], row["total_attempts"], row["total_correct"]


async def get_daily_accuracy(
    conn: aiosqlite.Connection, user_id: int, days: int = 14
) -> list[tuple[str, int, int]]:
    """(дата, всего, верно) за последние `days` дней — для графика в Mini App.

    Россия — фиксированный UTC+3 без перевода часов с 2014 года, поэтому
    группировка по '+3 hours' даёт корректную дату Europe/Moscow без
    необходимости тянуть zoneinfo в SQL."""
    cursor = await conn.execute(
        """
        SELECT date(answered_at, '+3 hours') AS d,
               COUNT(*) AS total,
               SUM(is_correct) AS correct
        FROM mental_math_attempts
        WHERE user_id = ? AND answered_at >= datetime('now', ?)
        GROUP BY d
        ORDER BY d
        """,
        (user_id, f"-{days} days"),
    )
    rows = await cursor.fetchall()
    return [(r["d"], r["total"], r["correct"] or 0) for r in rows]
