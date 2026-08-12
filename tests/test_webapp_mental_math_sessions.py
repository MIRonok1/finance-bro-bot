"""Интеграционные тесты интерактивного API устного счёта
(app/webapp/mental_math_api.py) — через полный aiohttp-стек."""

from datetime import UTC, datetime, timedelta

import pytest

from app.config import Settings
from app.payments.repo import get_daily_usage_count
from app.timeutils import today_msk
from tests.webapp_test_utils import BOT_TOKEN, make_client, signed_init_data

_SQLITE_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _auth_headers(user_id: int) -> dict:
    return {"Authorization": f"tma {signed_init_data(user_id)}"}


@pytest.mark.asyncio
async def test_start_session_returns_task_without_answer():
    client, conn = await make_client()
    try:
        resp = await client.post(
            "/api/mental_math/sessions", headers=_auth_headers(1), json={"difficulty": 2}
        )
        assert resp.status == 201
        body = await resp.json()
        assert body["difficulty"] == 2
        assert body["streak"] == 0
        task = body["task"]
        assert set(task.keys()) == {"kind", "prompt"}
        assert task["prompt"]
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_start_session_rejects_bad_difficulty():
    client, conn = await make_client()
    try:
        resp = await client.post(
            "/api/mental_math/sessions", headers=_auth_headers(1), json={"difficulty": 9}
        )
        assert resp.status == 400
        assert (await resp.json())["error"] == "invalid_difficulty"
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_start_session_consumes_paywall_gate():
    settings = Settings(bot_token=BOT_TOKEN, admin_ids="1", paywall_enabled=True)
    client, conn = await make_client(settings)
    try:
        today = today_msk().isoformat()
        assert await get_daily_usage_count(conn, 1, today) == 0
        resp = await client.post(
            "/api/mental_math/sessions", headers=_auth_headers(1), json={"difficulty": 1}
        )
        assert resp.status == 201
        assert await get_daily_usage_count(conn, 1, today) == 1
    finally:
        await client.close()
        await conn.close()


async def _start_session(client, difficulty=2) -> tuple[str, dict]:
    resp = await client.post(
        "/api/mental_math/sessions", headers=_auth_headers(1), json={"difficulty": difficulty}
    )
    body = await resp.json()
    return body["session_id"], body


async def _correct_answer_for(conn, session_id: str) -> str:
    cursor = await conn.execute(
        "SELECT current_answer FROM mental_math_sessions WHERE id = ?", (session_id,)
    )
    return (await cursor.fetchone())["current_answer"]


@pytest.mark.asyncio
async def test_answer_correct_updates_streak_and_stats():
    client, conn = await make_client()
    try:
        session_id, _ = await _start_session(client)
        correct = await _correct_answer_for(conn, session_id)

        resp = await client.post(
            f"/api/mental_math/sessions/{session_id}/answer",
            headers=_auth_headers(1),
            json={"answer": correct},
        )
        assert resp.status == 200
        body = await resp.json()
        assert body["is_correct"] is True
        assert body["streak"] == 1
        assert body["total"] == 1
        assert body["correct"] == 1
        assert body["checkpoint"] is False
        assert isinstance(body["elapsed_ms"], int)

        cursor = await conn.execute("SELECT COUNT(*) FROM mental_math_attempts WHERE user_id = 1")
        (count,) = await cursor.fetchone()
        assert count == 1

        cursor = await conn.execute("SELECT daily_streak FROM users WHERE telegram_id = 1")
        assert (await cursor.fetchone())["daily_streak"] == 1
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_could_not_parse_does_not_record_or_lock_session():
    client, conn = await make_client()
    try:
        session_id, _ = await _start_session(client)
        resp = await client.post(
            f"/api/mental_math/sessions/{session_id}/answer",
            headers=_auth_headers(1),
            json={"answer": "чепуха"},
        )
        assert resp.status == 400
        assert (await resp.json())["error"] == "could_not_parse"

        cursor = await conn.execute(
            "SELECT current_answered FROM mental_math_sessions WHERE id = ?", (session_id,)
        )
        assert (await cursor.fetchone())["current_answered"] == 0

        cursor = await conn.execute("SELECT COUNT(*) FROM mental_math_attempts WHERE user_id = 1")
        (count,) = await cursor.fetchone()
        assert count == 0
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_answer_twice_conflicts():
    client, conn = await make_client()
    try:
        session_id, _ = await _start_session(client)
        correct = await _correct_answer_for(conn, session_id)

        first = await client.post(
            f"/api/mental_math/sessions/{session_id}/answer",
            headers=_auth_headers(1),
            json={"answer": correct},
        )
        assert first.status == 200

        second = await client.post(
            f"/api/mental_math/sessions/{session_id}/answer",
            headers=_auth_headers(1),
            json={"answer": correct},
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
        session_id, _ = await _start_session(client)
        resp = await client.post(
            f"/api/mental_math/sessions/{session_id}/next", headers=_auth_headers(1)
        )
        assert resp.status == 409
        assert (await resp.json())["error"] == "not_answered_yet"
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_next_generates_fresh_task_and_resets_answered():
    client, conn = await make_client()
    try:
        session_id, _ = await _start_session(client)
        correct = await _correct_answer_for(conn, session_id)
        await client.post(
            f"/api/mental_math/sessions/{session_id}/answer",
            headers=_auth_headers(1),
            json={"answer": correct},
        )
        resp = await client.post(
            f"/api/mental_math/sessions/{session_id}/next", headers=_auth_headers(1)
        )
        assert resp.status == 200
        task = (await resp.json())["task"]
        assert set(task.keys()) == {"kind", "prompt"}

        cursor = await conn.execute(
            "SELECT current_answered FROM mental_math_sessions WHERE id = ?", (session_id,)
        )
        assert (await cursor.fetchone())["current_answered"] == 0
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_checkpoint_flag_at_tenth_task():
    client, conn = await make_client()
    try:
        session_id, _ = await _start_session(client)
        for i in range(10):
            correct = await _correct_answer_for(conn, session_id)
            resp = await client.post(
                f"/api/mental_math/sessions/{session_id}/answer",
                headers=_auth_headers(1),
                json={"answer": correct},
            )
            body = await resp.json()
            if i < 9:
                assert body["checkpoint"] is False
                await client.post(
                    f"/api/mental_math/sessions/{session_id}/next", headers=_auth_headers(1)
                )
            else:
                assert body["checkpoint"] is True
                assert body["total"] == 10
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_finish_returns_summary_and_marks_done():
    client, conn = await make_client()
    try:
        session_id, _ = await _start_session(client)
        correct = await _correct_answer_for(conn, session_id)
        await client.post(
            f"/api/mental_math/sessions/{session_id}/answer",
            headers=_auth_headers(1),
            json={"answer": correct},
        )
        resp = await client.post(
            f"/api/mental_math/sessions/{session_id}/finish", headers=_auth_headers(1)
        )
        assert resp.status == 200
        body = await resp.json()
        assert body == {"total": 1, "correct": 1, "pct": 100, "session_best_streak": 1}

        cursor = await conn.execute(
            "SELECT status FROM mental_math_sessions WHERE id = ?", (session_id,)
        )
        assert (await cursor.fetchone())["status"] == "done"
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_elapsed_ms_computed_server_side_ignores_client():
    """Анти-чит: даже если бы клиент прислал своё elapsed-время, оно не
    используется — таймер целиком на сервере (current_started_at в БД)."""
    client, conn = await make_client()
    try:
        session_id, _ = await _start_session(client)
        # искусственно сдвигаем "старт" на 5 секунд назад в БД
        past = (datetime.now(UTC) - timedelta(seconds=5)).strftime(_SQLITE_DATETIME_FORMAT)
        await conn.execute(
            "UPDATE mental_math_sessions SET current_started_at = ? WHERE id = ?",
            (past, session_id),
        )
        await conn.commit()

        correct = await _correct_answer_for(conn, session_id)
        resp = await client.post(
            f"/api/mental_math/sessions/{session_id}/answer",
            headers=_auth_headers(1),
            json={"answer": correct, "elapsed_ms": 1},  # клиент врёт — должно игнорироваться
        )
        body = await resp.json()
        assert body["elapsed_ms"] >= 4500
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_session_not_visible_to_other_user():
    client, conn = await make_client()
    try:
        session_id, _ = await _start_session(client)
        resp = await client.get(f"/api/mental_math/sessions/{session_id}", headers=_auth_headers(2))
        assert resp.status == 404
    finally:
        await client.close()
        await conn.close()
