import aiosqlite
import pytest

from app.admin import repo as admin_repo
from app.db import apply_migrations


async def _conn() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await apply_migrations(conn)
    return conn


async def _insert_draft(conn: aiosqlite.Connection, body: str = "draft body") -> int:
    cursor = await conn.execute(
        "INSERT INTO questions (topic_id, type, difficulty, body, explanation, status) "
        "VALUES (1, 'open', 1, ?, 'draft explanation', 'draft')",
        (body,),
    )
    await conn.commit()
    return cursor.lastrowid


@pytest.mark.asyncio
async def test_list_draft_ids_returns_only_drafts_in_order():
    conn = await _conn()
    try:
        id1 = await _insert_draft(conn, "first")
        id2 = await _insert_draft(conn, "second")
        # approved вопросы из seed-миграции не должны попасть в список
        draft_ids = await admin_repo.list_draft_ids(conn)
        assert draft_ids == sorted([id1, id2])
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_get_any_question_returns_draft_unlike_quiz_repo():
    conn = await _conn()
    try:
        draft_id = await _insert_draft(conn)
        question = await admin_repo.get_any_question(conn, draft_id)
        assert question is not None
        assert question.status == "draft"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_get_any_question_returns_none_for_missing_id():
    conn = await _conn()
    try:
        assert await admin_repo.get_any_question(conn, 999999) is None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_set_status_updates_status():
    conn = await _conn()
    try:
        draft_id = await _insert_draft(conn)
        await admin_repo.set_status(conn, draft_id, "approved")
        question = await admin_repo.get_any_question(conn, draft_id)
        assert question.status == "approved"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_update_body_changes_only_body():
    conn = await _conn()
    try:
        draft_id = await _insert_draft(conn, "old body")
        await admin_repo.update_body(conn, draft_id, "new body")
        question = await admin_repo.get_any_question(conn, draft_id)
        assert question.body == "new body"
        assert question.status == "draft"
    finally:
        await conn.close()
