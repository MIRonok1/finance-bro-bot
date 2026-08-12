import aiosqlite
import pytest

from app.db import apply_migrations, upsert_user


@pytest.mark.asyncio
async def test_apply_migrations_creates_tables():
    conn = await aiosqlite.connect(":memory:")
    try:
        await apply_migrations(conn)
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in await cursor.fetchall()}
        assert {"schema_version", "users"} <= tables

        cursor = await conn.execute("SELECT version FROM schema_version")
        versions = {row[0] for row in await cursor.fetchall()}
        assert 1 in versions
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_apply_migrations_is_idempotent():
    conn = await aiosqlite.connect(":memory:")
    try:
        await apply_migrations(conn)
        cursor = await conn.execute("SELECT COUNT(*) FROM schema_version")
        (count_after_first,) = await cursor.fetchone()

        await apply_migrations(conn)  # не должно упасть и не должно задвоить записи
        cursor = await conn.execute("SELECT COUNT(*) FROM schema_version")
        (count_after_second,) = await cursor.fetchone()

        assert count_after_first > 0
        assert count_after_second == count_after_first
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_upsert_user_inserts_and_updates():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    try:
        await apply_migrations(conn)

        await upsert_user(conn, telegram_id=42, username="dima", is_admin=True)
        cursor = await conn.execute("SELECT * FROM users WHERE telegram_id = 42")
        row = await cursor.fetchone()
        assert row["username"] == "dima"
        assert row["is_admin"] == 1

        await upsert_user(conn, telegram_id=42, username="dima2", is_admin=False)
        cursor = await conn.execute("SELECT * FROM users WHERE telegram_id = 42")
        row = await cursor.fetchone()
        assert row["username"] == "dima2"
        assert row["is_admin"] == 0

        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        (count,) = await cursor.fetchone()
        assert count == 1
    finally:
        await conn.close()
