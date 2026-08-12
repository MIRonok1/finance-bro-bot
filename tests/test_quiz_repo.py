from datetime import date

import aiosqlite
import pytest

import app.quiz.repo as repo_module
from app.db import apply_migrations, upsert_user
from app.quiz import repo


async def _seeded_conn() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await apply_migrations(conn)
    return conn


@pytest.mark.asyncio
async def test_seed_bank_has_40_approved_questions():
    conn = await _seeded_conn()
    try:
        cursor = await conn.execute("SELECT COUNT(*) FROM questions WHERE status = 'approved'")
        (count,) = await cursor.fetchone()
        assert count == 40
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_list_topics_returns_five_topics_in_order():
    conn = await _seeded_conn()
    try:
        topics = await repo.list_topics(conn)
        assert [t.slug for t in topics] == ["dcf", "multiples", "lbo", "accounting", "ma"]
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_pick_session_question_ids_respects_topic_and_size():
    conn = await _seeded_conn()
    try:
        ids = await repo.pick_session_question_ids(conn, topic_id=1, size=5)
        assert len(ids) == 5
        for qid in ids:
            question = await repo.get_question(conn, qid)
            assert question is not None
            assert question.topic_id == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_pick_session_question_ids_respects_difficulty_filter():
    conn = await _seeded_conn()
    try:
        ids = await repo.pick_session_question_ids(conn, topic_id=1, difficulty=1, size=10)
        for qid in ids:
            question = await repo.get_question(conn, qid)
            assert question.difficulty == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_get_question_only_returns_approved():
    conn = await _seeded_conn()
    try:
        await conn.execute(
            "INSERT INTO questions (topic_id, type, difficulty, body, explanation, status) "
            "VALUES (1, 'open', 1, 'draft body', 'draft explanation', 'draft')"
        )
        await conn.commit()
        cursor = await conn.execute("SELECT id FROM questions WHERE status = 'draft'")
        (draft_id,) = await cursor.fetchone()
        assert await repo.get_question(conn, draft_id) is None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_record_attempt_and_topic_stats():
    conn = await _seeded_conn()
    try:
        await upsert_user(conn, telegram_id=1, username="u", is_admin=False)
        ids = await repo.pick_session_question_ids(conn, topic_id=1, size=2)
        await repo.record_attempt(conn, 1, ids[0], "session-1", "answer", True)
        await repo.record_attempt(conn, 1, ids[1], "session-1", "answer", False)

        stats = await repo.topic_stats(conn, user_id=1)
        assert len(stats) == 1
        title, total, correct = stats[0]
        assert title == "DCF"
        assert total == 2
        assert correct == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_upsert_review_after_attempt_sets_due_date_one_day_ahead(monkeypatch):
    conn = await _seeded_conn()
    try:
        await upsert_user(conn, telegram_id=1, username="u", is_admin=False)
        monkeypatch.setattr(repo_module, "today_msk", lambda: date(2026, 8, 12))
        ids = await repo.pick_session_question_ids(conn, topic_id=1, size=1)
        qid = ids[0]

        await repo.upsert_review_after_attempt(conn, 1, qid, is_correct=True)
        cursor = await conn.execute(
            "SELECT due_date, repetitions FROM review_schedule WHERE user_id=1 AND question_id=?",
            (qid,),
        )
        row = await cursor.fetchone()
        assert row["due_date"] == "2026-08-13"
        assert row["repetitions"] == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_get_due_question_ids_returns_only_due_and_approved(monkeypatch):
    conn = await _seeded_conn()
    try:
        await upsert_user(conn, telegram_id=1, username="u", is_admin=False)
        ids = await repo.pick_session_question_ids(conn, topic_id=1, size=2)
        due_qid, not_due_qid = ids[0], ids[1]

        monkeypatch.setattr(repo_module, "today_msk", lambda: date(2026, 8, 12))
        # Неверный ответ -> due_date = завтра тоже, поэтому явно откатим одно
        # из двух расписаний в прошлое, а другое оставим в будущем.
        await repo.upsert_review_after_attempt(conn, 1, due_qid, is_correct=False)
        await conn.execute(
            "UPDATE review_schedule SET due_date = '2026-08-10' WHERE user_id=1 AND question_id=?",
            (due_qid,),
        )
        await repo.upsert_review_after_attempt(conn, 1, not_due_qid, is_correct=True)
        await conn.execute(
            "UPDATE review_schedule SET due_date = '2099-01-01' WHERE user_id=1 AND question_id=?",
            (not_due_qid,),
        )
        await conn.commit()

        due_ids = await repo.get_due_question_ids(conn, 1, limit=10)
        assert due_ids == [due_qid]
        assert await repo.count_due_questions(conn, 1) == 1
    finally:
        await conn.close()
