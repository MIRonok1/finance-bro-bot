"""Доступ к БД для админского /review: список draft-вопросов, approve/reject/edit.

В отличие от app/quiz/repo.py (который выдаёт только status='approved'
пользователям), здесь сознательно читаем вопрос любого статуса — это
единственное место в проекте, где мы работаем с draft-контентом напрямую."""

from __future__ import annotations

import aiosqlite

from app.quiz.repo import Question, _row_to_question

__all__ = ["Question", "list_draft_ids", "get_any_question", "set_status", "update_body"]


async def list_draft_ids(conn: aiosqlite.Connection) -> list[int]:
    cursor = await conn.execute("SELECT id FROM questions WHERE status = 'draft' ORDER BY id")
    rows = await cursor.fetchall()
    return [r["id"] for r in rows]


async def get_any_question(conn: aiosqlite.Connection, question_id: int) -> Question | None:
    cursor = await conn.execute(
        """
        SELECT id, topic_id, type, difficulty, body, options_json, correct_key,
               correct_answer, tolerance_pct, explanation, source, status
        FROM questions WHERE id = ?
        """,
        (question_id,),
    )
    row = await cursor.fetchone()
    return _row_to_question(row) if row else None


async def set_status(conn: aiosqlite.Connection, question_id: int, status: str) -> None:
    await conn.execute("UPDATE questions SET status = ? WHERE id = ?", (status, question_id))
    await conn.commit()


async def update_body(conn: aiosqlite.Connection, question_id: int, new_body: str) -> None:
    await conn.execute("UPDATE questions SET body = ? WHERE id = ?", (new_body, question_id))
    await conn.commit()
