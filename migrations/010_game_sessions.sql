-- DB-backed состояние игровых сессий Mini App (Фаза 4: интерактивные
-- квиз/устный счёт прямо в приложении, чат-FSM для них удалён). Состояние
-- обязательно живёт в БД, не в памяти процесса — Netrun усыпляет процесс
-- при простое по HTTP, сессия должна пережить рестарт (тот же принцип,
-- что FSM бота на SQLite-сторадже, не MemoryStorage, см. CLAUDE.md).

CREATE TABLE IF NOT EXISTS quiz_sessions (
    id                  TEXT PRIMARY KEY,       -- uuid4 hex, как attempts.session_id
    user_id             INTEGER NOT NULL REFERENCES users(telegram_id),
    mode                TEXT NOT NULL DEFAULT 'topic' CHECK (mode IN ('topic', 'review')),
    topic_id            INTEGER REFERENCES topics(id),   -- NULL для mode='review'
    difficulty          INTEGER,                          -- NULL = "любая"
    question_ids_json   TEXT NOT NULL,                     -- JSON-массив id, фиксируется при старте
    current_index       INTEGER NOT NULL DEFAULT 0,
    current_answered    INTEGER NOT NULL DEFAULT 0,        -- защита от повторной записи попытки при ретрае
    pending_open_answer TEXT,                              -- для type='open': текст до самооценки
    correct_count       INTEGER NOT NULL DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'done')),
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user ON quiz_sessions(user_id, status);

CREATE TABLE IF NOT EXISTS mental_math_sessions (
    id                     TEXT PRIMARY KEY,
    user_id                INTEGER NOT NULL REFERENCES users(telegram_id),
    difficulty             INTEGER NOT NULL,
    streak                 INTEGER NOT NULL DEFAULT 0,
    session_best_streak    INTEGER NOT NULL DEFAULT 0,
    total                  INTEGER NOT NULL DEFAULT 0,
    correct                INTEGER NOT NULL DEFAULT 0,
    current_kind           TEXT NOT NULL,
    current_prompt         TEXT NOT NULL,
    current_answer         TEXT NOT NULL,        -- Decimal как строка
    current_tolerance_pct  REAL NOT NULL,
    current_explanation    TEXT NOT NULL,
    current_started_at     TEXT NOT NULL,         -- datetime('now'), серверный якорь таймера (анти-чит)
    current_answered       INTEGER NOT NULL DEFAULT 0,
    status                 TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'done')),
    created_at             TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at             TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_mm_sessions_user ON mental_math_sessions(user_id, status);
