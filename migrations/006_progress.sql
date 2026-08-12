-- Ежедневная серия активности и интервальное повторение (упрощённый SM-2).

ALTER TABLE users ADD COLUMN daily_streak INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN last_active_date TEXT;

CREATE TABLE IF NOT EXISTS review_schedule (
    user_id           INTEGER NOT NULL REFERENCES users(telegram_id),
    question_id       INTEGER NOT NULL REFERENCES questions(id),
    easiness_factor   REAL NOT NULL DEFAULT 2.5,
    interval_days     INTEGER NOT NULL DEFAULT 0,
    repetitions       INTEGER NOT NULL DEFAULT 0,
    due_date          TEXT NOT NULL,
    last_reviewed_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_review_schedule_due ON review_schedule(user_id, due_date);
