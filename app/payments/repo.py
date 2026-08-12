"""Доступ к БД для пейволла: entitlements (Stars-подписка) и дневной лимит
бесплатных задач.

valid_until хранится в том же текстовом формате, что и sqlite datetime('now')
('YYYY-MM-DD HH:MM:SS', UTC), чтобы сравнение `valid_until > datetime('now')`
работало как обычное лексикографическое сравнение строк."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import aiosqlite

_SQLITE_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _format_sqlite_datetime(dt: datetime) -> str:
    return dt.strftime(_SQLITE_DATETIME_FORMAT)


async def has_active_entitlement(conn: aiosqlite.Connection, user_id: int) -> bool:
    row = await (
        await conn.execute(
            "SELECT 1 FROM entitlements "
            "WHERE user_id = ? AND valid_until > datetime('now') LIMIT 1",
            (user_id,),
        )
    ).fetchone()
    return row is not None


async def get_active_plan(conn: aiosqlite.Connection, user_id: int) -> str | None:
    """Код плана активной подписки (для профиля в Mini App), либо None."""
    row = await (
        await conn.execute(
            "SELECT plan FROM entitlements WHERE user_id = ? AND valid_until > datetime('now') "
            "ORDER BY valid_until DESC LIMIT 1",
            (user_id,),
        )
    ).fetchone()
    return row["plan"] if row else None


async def _max_valid_until(conn: aiosqlite.Connection, user_id: int) -> str | None:
    cursor = await conn.execute(
        "SELECT MAX(valid_until) FROM entitlements WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    return row[0] if row and row[0] else None


async def grant_entitlement(
    conn: aiosqlite.Connection,
    user_id: int,
    plan_code: str,
    duration_days: int,
    source: str,
    stars_paid: int | None = None,
    charge_id: str | None = None,
) -> bool:
    """Продлевает подписку (от текущего valid_until, если он ещё не истёк,
    иначе от сейчас) и создаёт запись entitlements.

    Возвращает False без изменений, если charge_id уже был обработан ранее
    (UNIQUE-конфликт) — это и есть идемпотентность на случай повторной
    доставки successful_payment от Telegram."""
    base = datetime.now(UTC).replace(tzinfo=None)
    current = await _max_valid_until(conn, user_id)
    if current:
        try:
            existing = datetime.strptime(current, _SQLITE_DATETIME_FORMAT)
            if existing > base:
                base = existing
        except ValueError:
            pass

    valid_until = _format_sqlite_datetime(base + timedelta(days=duration_days))

    try:
        await conn.execute(
            "INSERT INTO entitlements "
            "(user_id, plan, valid_until, source, stars_paid, charge_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, plan_code, valid_until, source, stars_paid, charge_id),
        )
        await conn.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def get_daily_usage_count(conn: aiosqlite.Connection, user_id: int, date_str: str) -> int:
    row = await (
        await conn.execute(
            "SELECT count FROM daily_usage WHERE user_id = ? AND usage_date = ?",
            (user_id, date_str),
        )
    ).fetchone()
    return row[0] if row else 0


async def increment_daily_usage(conn: aiosqlite.Connection, user_id: int, date_str: str) -> int:
    await conn.execute(
        """
        INSERT INTO daily_usage (user_id, usage_date, count) VALUES (?, ?, 1)
        ON CONFLICT(user_id, usage_date) DO UPDATE SET count = count + 1
        """,
        (user_id, date_str),
    )
    await conn.commit()
    return await get_daily_usage_count(conn, user_id, date_str)
