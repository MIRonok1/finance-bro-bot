-- Хранилище FSM aiogram на SQLite (см. CLAUDE.md: никакого MemoryStorage).
-- key — сериализованный StorageKey (bot_id:chat_id:user_id:thread_id:destiny).

CREATE TABLE IF NOT EXISTS fsm_storage (
    key         TEXT PRIMARY KEY,
    state       TEXT,
    data_json   TEXT NOT NULL DEFAULT '{}',
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
