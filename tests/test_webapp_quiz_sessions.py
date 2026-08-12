"""Интеграционные тесты интерактивного API квиза (app/webapp/quiz_api.py) —
через полный aiohttp-стек, как test_webapp_integration.py. Использует
реальные seed-вопросы из migrations/004_seed_questions.sql, а не моки."""

import json

import pytest

from app.config import Settings
from app.payments.repo import get_daily_usage_count
from app.timeutils import today_msk
from tests.webapp_test_utils import BOT_TOKEN, make_client, signed_init_data


def _auth_headers(user_id: int) -> dict:
    return {"Authorization": f"tma {signed_init_data(user_id)}"}


async def _known_mcq_question_id(conn) -> int:
    cursor = await conn.execute(
        "SELECT id FROM questions WHERE type = 'mcq' AND status = 'approved' LIMIT 1"
    )
    row = await cursor.fetchone()
    assert row is not None, "seed должен содержать хотя бы один approved mcq-вопрос"
    return row["id"]


async def _known_numeric_question_id(conn) -> int:
    cursor = await conn.execute(
        "SELECT id FROM questions WHERE type = 'numeric' AND status = 'approved' LIMIT 1"
    )
    row = await cursor.fetchone()
    assert row is not None
    return row["id"]


async def _known_open_question_id(conn) -> int:
    cursor = await conn.execute(
        "SELECT id FROM questions WHERE type = 'open' AND status = 'approved' LIMIT 1"
    )
    row = await cursor.fetchone()
    assert row is not None
    return row["id"]


async def _insert_user(conn, user_id: int) -> None:
    await conn.execute(
        "INSERT OR IGNORE INTO users (telegram_id, username, is_admin) VALUES (?, NULL, 0)",
        (user_id,),
    )
    await conn.commit()


async def _make_session_for_question(conn, user_id: int, question_id: int) -> str:
    """Создаёт сессию из одного заранее известного вопроса — в обход
    рандомного pick_session_question_ids, чтобы тесты были детерминированы."""
    import uuid

    session_id = uuid.uuid4().hex
    await _insert_user(conn, user_id)
    await conn.execute(
        """
        INSERT INTO quiz_sessions (id, user_id, mode, topic_id, difficulty, question_ids_json)
        VALUES (?, ?, 'topic', NULL, NULL, ?)
        """,
        (session_id, user_id, json.dumps([question_id])),
    )
    await conn.commit()
    return session_id


@pytest.mark.asyncio
async def test_topics_lists_seeded_topics():
    client, conn = await make_client()
    try:
        resp = await client.get("/api/quiz/topics", headers=_auth_headers(1))
        assert resp.status == 200
        body = await resp.json()
        assert len(body["topics"]) >= 1
        assert {"id", "slug", "title"} <= body["topics"][0].keys()
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_start_topic_session_hides_correct_answer():
    client, conn = await make_client()
    try:
        resp = await client.post(
            "/api/quiz/sessions", headers=_auth_headers(1), json={"topic_id": 1}
        )
        assert resp.status == 201
        body = await resp.json()
        assert body["status"] == "in_progress"
        assert 1 <= body["total"] <= 5
        question = body["question"]
        assert "correct_key" not in question
        assert "correct_answer" not in question
        assert "tolerance_pct" not in question
        assert "status" not in question
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_start_session_no_questions_for_empty_combo():
    client, conn = await make_client()
    try:
        # сложность 5 у первой темы не заполнена в seed-данных
        resp = await client.post(
            "/api/quiz/sessions",
            headers=_auth_headers(1),
            json={"topic_id": 1, "difficulty": 5},
        )
        assert resp.status == 404
        assert (await resp.json())["error"] == "no_questions"
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_start_topic_session_consumes_paywall_gate():
    settings = Settings(bot_token=BOT_TOKEN, admin_ids="1", paywall_enabled=True)
    client, conn = await make_client(settings)
    try:
        today = today_msk().isoformat()
        assert await get_daily_usage_count(conn, 1, today) == 0
        resp = await client.post(
            "/api/quiz/sessions", headers=_auth_headers(1), json={"topic_id": 1}
        )
        assert resp.status == 201
        assert await get_daily_usage_count(conn, 1, today) == 1
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_review_session_does_not_consume_paywall_gate():
    settings = Settings(bot_token=BOT_TOKEN, admin_ids="1", paywall_enabled=True)
    client, conn = await make_client(settings)
    try:
        await _insert_user(conn, 1)
        question_id = await _known_mcq_question_id(conn)
        await conn.execute(
            "INSERT INTO review_schedule (user_id, question_id, due_date) VALUES (?, ?, ?)",
            (1, question_id, today_msk().isoformat()),
        )
        await conn.commit()

        today = today_msk().isoformat()
        resp = await client.post(
            "/api/quiz/sessions", headers=_auth_headers(1), json={"mode": "review"}
        )
        assert resp.status == 201
        assert await get_daily_usage_count(conn, 1, today) == 0
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_answer_mcq_correct_records_attempt_and_review_schedule():
    client, conn = await make_client()
    try:
        question_id = await _known_mcq_question_id(conn)
        session_id = await _make_session_for_question(conn, 1, question_id)

        cursor = await conn.execute(
            "SELECT correct_key FROM questions WHERE id = ?", (question_id,)
        )
        correct_key = (await cursor.fetchone())["correct_key"]

        resp = await client.post(
            f"/api/quiz/sessions/{session_id}/answer",
            headers=_auth_headers(1),
            json={"chosen_key": correct_key},
        )
        assert resp.status == 200
        body = await resp.json()
        assert body["is_correct"] is True
        assert body["correct_key"] == correct_key

        cursor = await conn.execute(
            "SELECT COUNT(*) FROM attempts WHERE question_id = ?", (question_id,)
        )
        (count,) = await cursor.fetchone()
        assert count == 1

        cursor = await conn.execute(
            "SELECT repetitions FROM review_schedule WHERE user_id = 1 AND question_id = ?",
            (question_id,),
        )
        row = await cursor.fetchone()
        assert row is not None and row["repetitions"] == 1

        cursor = await conn.execute("SELECT daily_streak FROM users WHERE telegram_id = 1")
        assert (await cursor.fetchone())["daily_streak"] == 1
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_answer_twice_conflicts():
    client, conn = await make_client()
    try:
        question_id = await _known_mcq_question_id(conn)
        session_id = await _make_session_for_question(conn, 1, question_id)

        first = await client.post(
            f"/api/quiz/sessions/{session_id}/answer",
            headers=_auth_headers(1),
            json={"chosen_key": "A"},
        )
        assert first.status == 200

        second = await client.post(
            f"/api/quiz/sessions/{session_id}/answer",
            headers=_auth_headers(1),
            json={"chosen_key": "A"},
        )
        assert second.status == 409
        assert (await second.json())["error"] == "already_answered"
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_next_before_answered_conflicts():
    client, conn = await make_client()
    try:
        question_id = await _known_mcq_question_id(conn)
        session_id = await _make_session_for_question(conn, 1, question_id)

        resp = await client.post(f"/api/quiz/sessions/{session_id}/next", headers=_auth_headers(1))
        assert resp.status == 409
        assert (await resp.json())["error"] == "not_answered_yet"
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_next_after_last_question_completes_session():
    client, conn = await make_client()
    try:
        question_id = await _known_mcq_question_id(conn)
        session_id = await _make_session_for_question(conn, 1, question_id)

        await client.post(
            f"/api/quiz/sessions/{session_id}/answer",
            headers=_auth_headers(1),
            json={"chosen_key": "A"},
        )
        resp = await client.post(f"/api/quiz/sessions/{session_id}/next", headers=_auth_headers(1))
        assert resp.status == 200
        body = await resp.json()
        assert body["status"] == "done"
        assert body["question"] is None
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_numeric_could_not_parse_does_not_record_attempt():
    client, conn = await make_client()
    try:
        question_id = await _known_numeric_question_id(conn)
        session_id = await _make_session_for_question(conn, 1, question_id)

        resp = await client.post(
            f"/api/quiz/sessions/{session_id}/answer",
            headers=_auth_headers(1),
            json={"answer": "не число"},
        )
        assert resp.status == 400
        assert (await resp.json())["error"] == "could_not_parse"

        cursor = await conn.execute(
            "SELECT COUNT(*) FROM attempts WHERE question_id = ?", (question_id,)
        )
        (count,) = await cursor.fetchone()
        assert count == 0

        # сессия всё ещё отвечаема — current_answered не выставлен
        cursor = await conn.execute(
            "SELECT current_answered FROM quiz_sessions WHERE id = ?", (session_id,)
        )
        assert (await cursor.fetchone())["current_answered"] == 0
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_open_question_answer_then_rate_flow():
    client, conn = await make_client()
    try:
        question_id = await _known_open_question_id(conn)
        session_id = await _make_session_for_question(conn, 1, question_id)

        answer_resp = await client.post(
            f"/api/quiz/sessions/{session_id}/answer",
            headers=_auth_headers(1),
            json={"answer": "мой развёрнутый ответ"},
        )
        assert answer_resp.status == 200
        assert "explanation" in await answer_resp.json()

        # ещё не оценено самим пользователем -> not_answered_yet на /next
        premature_next = await client.post(
            f"/api/quiz/sessions/{session_id}/next", headers=_auth_headers(1)
        )
        assert premature_next.status == 409

        rate_resp = await client.post(
            f"/api/quiz/sessions/{session_id}/rate",
            headers=_auth_headers(1),
            json={"rating": "correct"},
        )
        assert rate_resp.status == 200
        assert (await rate_resp.json())["is_correct"] is True

        cursor = await conn.execute(
            "SELECT user_answer FROM attempts WHERE question_id = ?", (question_id,)
        )
        assert (await cursor.fetchone())["user_answer"] == "мой развёрнутый ответ"
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_session_not_visible_to_other_user():
    client, conn = await make_client()
    try:
        question_id = await _known_mcq_question_id(conn)
        session_id = await _make_session_for_question(conn, 1, question_id)

        resp = await client.get(f"/api/quiz/sessions/{session_id}", headers=_auth_headers(2))
        assert resp.status == 404
    finally:
        await client.close()
        await conn.close()
