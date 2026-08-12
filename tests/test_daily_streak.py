from datetime import date

import aiosqlite
import pytest

import app.db as db_module
from app.db import apply_migrations, get_daily_streak, touch_daily_streak, upsert_user


async def _conn() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await apply_migrations(conn)
    await upsert_user(conn, telegram_id=1, username="u", is_admin=False)
    return conn


@pytest.mark.asyncio
async def test_first_touch_sets_streak_to_one():
    conn = await _conn()
    try:
        streak = await touch_daily_streak(conn, 1)
        assert streak == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_same_day_touch_does_not_increment(monkeypatch):
    conn = await _conn()
    try:
        monkeypatch.setattr(db_module, "today_msk", lambda: date(2026, 8, 12))
        await touch_daily_streak(conn, 1)
        streak = await touch_daily_streak(conn, 1)
        assert streak == 1
        assert await get_daily_streak(conn, 1) == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_consecutive_day_increments_streak(monkeypatch):
    conn = await _conn()
    try:
        monkeypatch.setattr(db_module, "today_msk", lambda: date(2026, 8, 12))
        await touch_daily_streak(conn, 1)
        monkeypatch.setattr(db_module, "today_msk", lambda: date(2026, 8, 13))
        streak = await touch_daily_streak(conn, 1)
        assert streak == 2
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_gap_day_resets_streak(monkeypatch):
    conn = await _conn()
    try:
        monkeypatch.setattr(db_module, "today_msk", lambda: date(2026, 8, 12))
        await touch_daily_streak(conn, 1)
        monkeypatch.setattr(db_module, "today_msk", lambda: date(2026, 8, 15))
        streak = await touch_daily_streak(conn, 1)
        assert streak == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_unknown_user_returns_zero():
    conn = await _conn()
    try:
        assert await touch_daily_streak(conn, 999) == 0
        assert await get_daily_streak(conn, 999) == 0
    finally:
        await conn.close()
