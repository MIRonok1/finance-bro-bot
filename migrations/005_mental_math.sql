-- Попытки и агрегированная статистика модуля «Быстрый счёт».

CREATE TABLE IF NOT EXISTS mental_math_attempts (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(telegram_id),
    kind            TEXT NOT NULL,
    difficulty      INTEGER NOT NULL,
    is_correct      INTEGER NOT NULL,
    elapsed_ms      INTEGER NOT NULL,
    answered_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_mm_attempts_user ON mental_math_attempts(user_id);

CREATE TABLE IF NOT EXISTS mental_math_stats (
    user_id         INTEGER PRIMARY KEY REFERENCES users(telegram_id),
    best_streak     INTEGER NOT NULL DEFAULT 0,
    total_attempts  INTEGER NOT NULL DEFAULT 0,
    total_correct   INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
