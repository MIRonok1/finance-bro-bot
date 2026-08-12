"""Интерактивная игровая сессия квиза для Mini App (Фаза 4).

Заменяет чат-FSM (`app/handlers/quiz.py`, удалён) — сама логика грейдинга,
выбора вопросов и SM-2 не переписывается, целиком переиспользуется из
`app.quiz.repo`/`app.quiz.logic`/`app.srs` (см. CLAUDE.md: «неверный
правильный ответ — критический баг», значит два места с одной и той же
проверкой недопустимы).

Состояние сессии — в таблице `quiz_sessions` (миграция 010), не в памяти
процесса: Netrun усыпляет процесс при простое по HTTP, сессия обязана
пережить рестарт (тот же принцип, что FSM бота на SQLite-сторадже).

DTO вопроса, отдаваемое клиенту (`_question_dto`), никогда не содержит
`correct_key`/`correct_answer`/`tolerance_pct`/`status`/`source` — это
раскрывается только в ответе на `/answer`, после того как попытка уже
записана.
"""

from __future__ import annotations

import json
import logging
import uuid

from aiohttp import web

from app.db import touch_daily_streak
from app.payments.gate import check_and_consume
from app.payments.plans import FREE_DAILY_TASKS
from app.quiz import repo as quiz_repo
from app.quiz.logic import grade_mcq, grade_numeric, grade_open
from app.quiz.repo import Question
from app.webapp.keys import DB_KEY, SETTINGS_KEY

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()


def _question_dto(question: Question) -> dict:
    dto: dict = {
        "id": question.id,
        "topic_id": question.topic_id,
        "type": question.type,
        "difficulty": question.difficulty,
        "body": question.body,
    }
    if question.type == "mcq" and question.options_json:
        dto["options"] = json.loads(question.options_json)
    return dto


async def _get_session_row(db, session_id: str, user_id: int) -> dict | None:
    cursor = await db.execute("SELECT * FROM quiz_sessions WHERE id = ?", (session_id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    if row["user_id"] != user_id:
        return None
    return dict(row)


async def _session_response(db, session: dict) -> dict:
    question_ids = json.loads(session["question_ids_json"])
    total = len(question_ids)
    if session["status"] == "done" or session["current_index"] >= total:
        return {
            "session_id": session["id"],
            "status": "done",
            "total": total,
            "correct_count": session["correct_count"],
            "question": None,
        }
    question_id = question_ids[session["current_index"]]
    question = await quiz_repo.get_question(db, question_id)
    if question is None:
        # Вопрос сняли с публикации посреди сессии — пропускаем без штрафа,
        # как и в старом чат-флоу.
        return await _advance_session(db, session)
    return {
        "session_id": session["id"],
        "status": "in_progress",
        "total": total,
        "index": session["current_index"],
        "correct_count": session["correct_count"],
        "question": _question_dto(question),
    }


async def _advance_session(db, session: dict) -> dict:
    question_ids = json.loads(session["question_ids_json"])
    new_index = session["current_index"] + 1
    await db.execute(
        """
        UPDATE quiz_sessions
        SET current_index = ?, current_answered = 0, pending_open_answer = NULL,
            status = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (new_index, "done" if new_index >= len(question_ids) else "in_progress", session["id"]),
    )
    await db.commit()
    session["current_index"] = new_index
    session["status"] = "done" if new_index >= len(question_ids) else "in_progress"
    return await _session_response(db, session)


@routes.get("/api/quiz/topics")
async def get_topics(request: web.Request) -> web.Response:
    db = request.app[DB_KEY]
    topics = await quiz_repo.list_topics(db)
    return web.json_response(
        {"topics": [{"id": t.id, "slug": t.slug, "title": t.title} for t in topics]}
    )


@routes.post("/api/quiz/sessions")
async def start_session(request: web.Request) -> web.Response:
    tg_user = request["tg_user"]
    db = request.app[DB_KEY]
    settings = request.app[SETTINGS_KEY]

    try:
        body = await request.json()
    except ValueError:
        body = {}
    mode = body.get("mode", "topic")

    if mode == "review":
        question_ids = await quiz_repo.get_due_question_ids(db, tg_user.id)
        topic_id = None
        difficulty = None
    elif mode == "topic":
        topic_id = body.get("topic_id")
        difficulty = body.get("difficulty")
        if not isinstance(topic_id, int):
            return web.json_response({"error": "topic_id_required"}, status=400)
        allowed = await check_and_consume(db, tg_user.id, settings)
        if not allowed:
            return web.json_response(
                {"error": "paywall_limit", "limit": FREE_DAILY_TASKS}, status=402
            )
        question_ids = await quiz_repo.pick_session_question_ids(db, topic_id, difficulty)
    else:
        return web.json_response({"error": "invalid_mode"}, status=400)

    if not question_ids:
        return web.json_response({"error": "no_questions"}, status=404)

    session_id = uuid.uuid4().hex
    await db.execute(
        """
        INSERT INTO quiz_sessions (id, user_id, mode, topic_id, difficulty, question_ids_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session_id, tg_user.id, mode, topic_id, difficulty, json.dumps(question_ids)),
    )
    await db.commit()

    session = await _get_session_row(db, session_id, tg_user.id)
    return web.json_response(await _session_response(db, session), status=201)


@routes.get("/api/quiz/sessions/{session_id}")
async def get_session(request: web.Request) -> web.Response:
    tg_user = request["tg_user"]
    db = request.app[DB_KEY]
    session = await _get_session_row(db, request.match_info["session_id"], tg_user.id)
    if session is None:
        return web.json_response({"error": "not_found"}, status=404)
    return web.json_response(await _session_response(db, session))


async def _load_in_progress_session(request: web.Request) -> tuple[dict, Question] | web.Response:
    """Общая подготовка для /answer, /rate: находит сессию, проверяет
    владение/статус/current_answered, возвращает (session, question) или
    готовый Response с ошибкой."""
    tg_user = request["tg_user"]
    db = request.app[DB_KEY]
    session = await _get_session_row(db, request.match_info["session_id"], tg_user.id)
    if session is None:
        return web.json_response({"error": "not_found"}, status=404)
    if session["status"] != "in_progress":
        return web.json_response({"error": "session_done"}, status=409)
    if session["current_answered"]:
        return web.json_response({"error": "already_answered"}, status=409)

    question_ids = json.loads(session["question_ids_json"])
    question_id = question_ids[session["current_index"]]
    question = await quiz_repo.get_question(db, question_id)
    if question is None:
        return web.json_response({"error": "question_unavailable"}, status=409)
    return session, question


async def _record_and_mark_answered(
    request: web.Request,
    session: dict,
    question: Question,
    user_answer: str | None,
    is_correct: bool,
) -> None:
    db = request.app[DB_KEY]
    tg_user = request["tg_user"]
    await quiz_repo.record_attempt(
        db, tg_user.id, question.id, session["id"], user_answer, is_correct
    )
    await quiz_repo.upsert_review_after_attempt(db, tg_user.id, question.id, is_correct)
    await touch_daily_streak(db, tg_user.id)

    new_correct_count = session["correct_count"] + (1 if is_correct else 0)
    await db.execute(
        "UPDATE quiz_sessions "
        "SET current_answered = 1, correct_count = ?, updated_at = datetime('now') "
        "WHERE id = ?",
        (new_correct_count, session["id"]),
    )
    await db.commit()


@routes.post("/api/quiz/sessions/{session_id}/answer")
async def answer_question(request: web.Request) -> web.Response:
    loaded = await _load_in_progress_session(request)
    if isinstance(loaded, web.Response):
        return loaded
    session, question = loaded

    try:
        body = await request.json()
    except ValueError:
        body = {}

    if question.type == "mcq":
        chosen_key = body.get("chosen_key", "")
        is_correct = grade_mcq(question, chosen_key)
        await _record_and_mark_answered(request, session, question, chosen_key, is_correct)
        return web.json_response(
            {
                "is_correct": is_correct,
                "correct_key": question.correct_key,
                "explanation": question.explanation,
            }
        )

    if question.type == "numeric":
        raw_answer = body.get("answer", "")
        is_correct, parsed = grade_numeric(question, raw_answer)
        if parsed is None:
            return web.json_response({"error": "could_not_parse"}, status=400)
        await _record_and_mark_answered(request, session, question, raw_answer, is_correct)
        return web.json_response(
            {
                "is_correct": is_correct,
                "correct_answer": question.correct_answer,
                "explanation": question.explanation,
            }
        )

    # open — ответ пока не оценивается, только сохраняется до /rate
    raw_answer = body.get("answer", "")
    db = request.app[DB_KEY]
    await db.execute(
        "UPDATE quiz_sessions "
        "SET pending_open_answer = ?, updated_at = datetime('now') WHERE id = ?",
        (raw_answer, session["id"]),
    )
    await db.commit()
    return web.json_response({"explanation": question.explanation})


@routes.post("/api/quiz/sessions/{session_id}/rate")
async def rate_open_answer(request: web.Request) -> web.Response:
    loaded = await _load_in_progress_session(request)
    if isinstance(loaded, web.Response):
        return loaded
    session, question = loaded
    if question.type != "open":
        return web.json_response({"error": "not_an_open_question"}, status=400)

    try:
        body = await request.json()
    except ValueError:
        body = {}
    rating = body.get("rating", "")
    is_correct = grade_open(rating)
    await _record_and_mark_answered(
        request, session, question, session.get("pending_open_answer"), is_correct
    )
    return web.json_response({"is_correct": is_correct})


@routes.post("/api/quiz/sessions/{session_id}/next")
async def next_question(request: web.Request) -> web.Response:
    tg_user = request["tg_user"]
    db = request.app[DB_KEY]
    session = await _get_session_row(db, request.match_info["session_id"], tg_user.id)
    if session is None:
        return web.json_response({"error": "not_found"}, status=404)
    if not session["current_answered"]:
        return web.json_response({"error": "not_answered_yet"}, status=409)
    return web.json_response(await _advance_session(db, session))
