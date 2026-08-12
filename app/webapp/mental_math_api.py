"""Интерактивная игровая сессия устного счёта для Mini App (Фаза 4).

Заменяет чат-FSM (`app/handlers/mental_math.py`, удалён). Генерация задач и
парсинг/проверка ответа переиспользуются как есть из
`app.mental_math.generators`/`app.quiz.answer_parser` — **не** через
`app.mental_math.answer_check.check_answer()`: старый чат-хендлер её не
вызывал, а делал `parse_answer` → `is_within_tolerance` напрямую (чтобы
"не распарсилось" и "неверно" были разными исходами). Здесь — та же
логика, для полной совместимости поведения со старым флоу.

Elapsed time считается на сервере (`current_started_at` в БД против
`datetime('now')`), клиентскому времени не доверяем — анти-чит для
статистики скорости.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from aiohttp import web

from app.db import touch_daily_streak
from app.mental_math import repo as mm_repo
from app.mental_math.engine import Task
from app.mental_math.generators import random_task
from app.payments.gate import check_and_consume
from app.payments.plans import FREE_DAILY_TASKS
from app.quiz.answer_parser import is_within_tolerance, parse_numeric_answer
from app.webapp.keys import DB_KEY, SETTINGS_KEY

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()

CHECKPOINT_EVERY = 10  # тот же порог, что был в app/handlers/mental_math.py

_SQLITE_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _task_dto(task: Task) -> dict:
    return {"kind": task.kind, "prompt": task.prompt}


async def _get_session_row(db, session_id: str, user_id: int) -> dict | None:
    cursor = await db.execute("SELECT * FROM mental_math_sessions WHERE id = ?", (session_id,))
    row = await cursor.fetchone()
    if row is None or row["user_id"] != user_id:
        return None
    return dict(row)


def _session_summary(session: dict) -> dict:
    return {
        "session_id": session["id"],
        "status": session["status"],
        "difficulty": session["difficulty"],
        "streak": session["streak"],
        "session_best_streak": session["session_best_streak"],
        "total": session["total"],
        "correct": session["correct"],
        "task": None
        if session["status"] == "done"
        else {"kind": session["current_kind"], "prompt": session["current_prompt"]},
    }


@routes.post("/api/mental_math/sessions")
async def start_session(request: web.Request) -> web.Response:
    tg_user = request["tg_user"]
    db = request.app[DB_KEY]
    settings = request.app[SETTINGS_KEY]

    try:
        body = await request.json()
    except ValueError:
        body = {}
    difficulty = body.get("difficulty")
    if not isinstance(difficulty, int) or not (1 <= difficulty <= 5):
        return web.json_response({"error": "invalid_difficulty"}, status=400)

    allowed = await check_and_consume(db, tg_user.id, settings)
    if not allowed:
        return web.json_response({"error": "paywall_limit", "limit": FREE_DAILY_TASKS}, status=402)

    task = random_task(difficulty)
    session_id = uuid.uuid4().hex
    started_at = datetime.now(UTC).strftime(_SQLITE_DATETIME_FORMAT)
    await db.execute(
        """
        INSERT INTO mental_math_sessions
            (id, user_id, difficulty, current_kind, current_prompt, current_answer,
             current_tolerance_pct, current_explanation, current_started_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            tg_user.id,
            difficulty,
            task.kind,
            task.prompt,
            str(task.answer),
            task.tolerance_pct,
            task.explanation,
            started_at,
        ),
    )
    await db.commit()

    return web.json_response(
        {
            "session_id": session_id,
            "difficulty": difficulty,
            "task": _task_dto(task),
            "streak": 0,
            "total": 0,
            "correct": 0,
        },
        status=201,
    )


@routes.get("/api/mental_math/sessions/{session_id}")
async def get_session(request: web.Request) -> web.Response:
    tg_user = request["tg_user"]
    db = request.app[DB_KEY]
    session = await _get_session_row(db, request.match_info["session_id"], tg_user.id)
    if session is None:
        return web.json_response({"error": "not_found"}, status=404)
    return web.json_response(_session_summary(session))


@routes.post("/api/mental_math/sessions/{session_id}/answer")
async def answer_task(request: web.Request) -> web.Response:
    tg_user = request["tg_user"]
    db = request.app[DB_KEY]
    session = await _get_session_row(db, request.match_info["session_id"], tg_user.id)
    if session is None:
        return web.json_response({"error": "not_found"}, status=404)
    if session["status"] != "in_progress":
        return web.json_response({"error": "session_done"}, status=409)
    if session["current_answered"]:
        return web.json_response({"error": "already_answered"}, status=409)

    try:
        body = await request.json()
    except ValueError:
        body = {}
    raw_answer = body.get("answer", "")

    # Двухшаговая проверка — точно как в старом чат-хендлере: "не
    # распарсилось" не пишет попытку и не трогает таймер/состояние.
    parsed = parse_numeric_answer(raw_answer)
    if parsed is None:
        return web.json_response({"error": "could_not_parse"}, status=400)

    correct_value = parse_numeric_answer(session["current_answer"])
    is_correct = is_within_tolerance(parsed, correct_value, session["current_tolerance_pct"])

    started_at = datetime.strptime(session["current_started_at"], _SQLITE_DATETIME_FORMAT).replace(
        tzinfo=UTC
    )
    elapsed_ms = max(0, int((datetime.now(UTC) - started_at).total_seconds() * 1000))

    await mm_repo.record_attempt(
        db, tg_user.id, session["current_kind"], session["difficulty"], is_correct, elapsed_ms
    )
    new_streak = session["streak"] + 1 if is_correct else 0
    best_streak_alltime, _, _ = await mm_repo.update_stats(db, tg_user.id, is_correct, new_streak)
    await touch_daily_streak(db, tg_user.id)

    new_total = session["total"] + 1
    new_correct = session["correct"] + (1 if is_correct else 0)
    new_session_best = max(session["session_best_streak"], new_streak)

    await db.execute(
        """
        UPDATE mental_math_sessions
        SET current_answered = 1, streak = ?, session_best_streak = ?,
            total = ?, correct = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (new_streak, new_session_best, new_total, new_correct, session["id"]),
    )
    await db.commit()

    return web.json_response(
        {
            "is_correct": is_correct,
            "correct_answer": session["current_answer"],
            "explanation": session["current_explanation"],
            "elapsed_ms": elapsed_ms,
            "streak": new_streak,
            "session_best_streak": new_session_best,
            "total": new_total,
            "correct": new_correct,
            "best_streak_alltime": best_streak_alltime,
            "checkpoint": new_total % CHECKPOINT_EVERY == 0,
        }
    )


@routes.post("/api/mental_math/sessions/{session_id}/next")
async def next_task(request: web.Request) -> web.Response:
    tg_user = request["tg_user"]
    db = request.app[DB_KEY]
    session = await _get_session_row(db, request.match_info["session_id"], tg_user.id)
    if session is None:
        return web.json_response({"error": "not_found"}, status=404)
    if session["status"] != "in_progress":
        return web.json_response({"error": "session_done"}, status=409)
    if not session["current_answered"]:
        return web.json_response({"error": "not_answered_yet"}, status=409)

    task = random_task(session["difficulty"])
    started_at = datetime.now(UTC).strftime(_SQLITE_DATETIME_FORMAT)
    await db.execute(
        """
        UPDATE mental_math_sessions
        SET current_kind = ?, current_prompt = ?, current_answer = ?,
            current_tolerance_pct = ?, current_explanation = ?, current_started_at = ?,
            current_answered = 0, updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            task.kind,
            task.prompt,
            str(task.answer),
            task.tolerance_pct,
            task.explanation,
            started_at,
            session["id"],
        ),
    )
    await db.commit()
    return web.json_response({"task": _task_dto(task)})


@routes.post("/api/mental_math/sessions/{session_id}/finish")
async def finish_session(request: web.Request) -> web.Response:
    tg_user = request["tg_user"]
    db = request.app[DB_KEY]
    session = await _get_session_row(db, request.match_info["session_id"], tg_user.id)
    if session is None:
        return web.json_response({"error": "not_found"}, status=404)

    await db.execute(
        "UPDATE mental_math_sessions "
        "SET status = 'done', updated_at = datetime('now') WHERE id = ?",
        (session["id"],),
    )
    await db.commit()

    total = session["total"]
    correct = session["correct"]
    pct = round(correct / total * 100) if total else 0
    return web.json_response(
        {
            "total": total,
            "correct": correct,
            "pct": pct,
            "session_best_streak": session["session_best_streak"],
        }
    )
