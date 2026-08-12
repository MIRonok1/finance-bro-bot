"""Работа с SQLite: подключение и применение миграций.

Никакой ORM — чистый SQL. Миграции — пронумерованные .sql-файлы в migrations/,
применяются по возрастанию номера, факт применения фиксируется в schema_version.
"""

from __future__ import annotations

import logging
import re
from datetime import timedelta
from pathlib import Path

import aiosqlite

from app.timeutils import today_msk

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
_MIGRATION_RE = re.compile(r"^(\d+)_.*\.sql$")


def _discover_migrations() -> list[tuple[int, Path]]:
    migrations: list[tuple[int, Path]] = []
    if not MIGRATIONS_DIR.exists():
        return migrations
    for path in MIGRATIONS_DIR.iterdir():
        match = _MIGRATION_RE.match(path.name)
        if match:
            migrations.append((int(match.group(1)), path))
    migrations.sort(key=lambda item: item[0])
    return migrations


async def apply_migrations(conn: aiosqlite.Connection) -> None:
    """Применяет все ещё не применённые миграции по порядку номеров."""
    # schema_version может ещё не существовать при самом первом запуске —
    # первая миграция обязана её создавать.
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version ("
        "version INTEGER PRIMARY KEY, "
        "applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    await conn.commit()

    cursor = await conn.execute("SELECT version FROM schema_version")
    applied = {row[0] for row in await cursor.fetchall()}

    for version, path in _discover_migrations():
        if version in applied:
            continue
        logger.info("Применяю миграцию %s (%s)", version, path.name)
        sql = path.read_text(encoding="utf-8")
        await conn.executescript(sql)
        await conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (?)", (version,))
        await conn.commit()


async def open_db(db_path: str) -> aiosqlite.Connection:
    """Открывает соединение с БД, создаёт директорию при необходимости,
    применяет миграции и возвращает готовое к работе соединение."""
    path = Path(db_path)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON")
    await conn.execute("PRAGMA journal_mode = WAL")
    await apply_migrations(conn)
    return conn


async def upsert_user(
    conn: aiosqlite.Connection,
    telegram_id: int,
    username: str | None,
    is_admin: bool,
) -> None:
    """Регистрирует пользователя или обновляет last_seen_at/username при повторном визите."""
    await conn.execute(
        """
        INSERT INTO users (telegram_id, username, is_admin)
        VALUES (?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            username = excluded.username,
            last_seen_at = datetime('now'),
            is_admin = excluded.is_admin
        """,
        (telegram_id, username, int(is_admin)),
    )
    await conn.commit()


async def touch_daily_streak(conn: aiosqlite.Connection, user_id: int) -> int:
    """Отмечает активность пользователя сегодня (дата — Europe/Moscow) и
    обновляет серию дней подряд. Возвращает актуальное значение серии.

    Один и тот же день не увеличивает серию повторно; пропущенный день
    сбрасывает её до 1."""
    today = today_msk()
    today_str = today.isoformat()

    cursor = await conn.execute(
        "SELECT daily_streak, last_active_date FROM users WHERE telegram_id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return 0

    streak, last_active = row["daily_streak"], row["last_active_date"]
    if last_active == today_str:
        return streak

    yesterday_str = (today - timedelta(days=1)).isoformat()
    streak = streak + 1 if last_active == yesterday_str else 1

    await conn.execute(
        "UPDATE users SET daily_streak = ?, last_active_date = ? WHERE telegram_id = ?",
        (streak, today_str, user_id),
    )
    await conn.commit()
    return streak


async def get_daily_streak(conn: aiosqlite.Connection, user_id: int) -> int:
    cursor = await conn.execute("SELECT daily_streak FROM users WHERE telegram_id = ?", (user_id,))
    row = await cursor.fetchone()
    return row["daily_streak"] if row else 0
