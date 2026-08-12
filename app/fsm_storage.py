"""SQLite-backed хранилище FSM для aiogram.

CLAUDE.md запрещает MemoryStorage: процесс должен подниматься с нуля и
восстанавливать состояние только из БД. Реализует минимальный набор
абстрактных методов BaseStorage поверх таблицы fsm_storage.
"""

from __future__ import annotations

import json
from typing import Any

import aiosqlite
from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey


def _serialize_key(key: StorageKey) -> str:
    return (
        f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.thread_id}:"
        f"{key.business_connection_id}:{key.destiny}"
    )


class SQLiteStorage(BaseStorage):
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def set_state(self, key: StorageKey, state: str | State | None = None) -> None:
        state_str = state.state if isinstance(state, State) else state
        row_key = _serialize_key(key)
        await self._conn.execute(
            """
            INSERT INTO fsm_storage (key, state, data_json, updated_at)
            VALUES (?, ?, '{}', datetime('now'))
            ON CONFLICT(key) DO UPDATE SET state = excluded.state, updated_at = datetime('now')
            """,
            (row_key, state_str),
        )
        await self._conn.commit()

    async def get_state(self, key: StorageKey) -> str | None:
        cursor = await self._conn.execute(
            "SELECT state FROM fsm_storage WHERE key = ?", (_serialize_key(key),)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        row_key = _serialize_key(key)
        data_json = json.dumps(data)
        await self._conn.execute(
            """
            INSERT INTO fsm_storage (key, state, data_json, updated_at)
            VALUES (?, NULL, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE SET
                data_json = excluded.data_json, updated_at = datetime('now')
            """,
            (row_key, data_json),
        )
        await self._conn.commit()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        cursor = await self._conn.execute(
            "SELECT data_json FROM fsm_storage WHERE key = ?", (_serialize_key(key),)
        )
        row = await cursor.fetchone()
        if not row or not row[0]:
            return {}
        return json.loads(row[0])

    async def close(self) -> None:
        # Соединением владеет main.py — закрывать его здесь не нужно.
        pass
