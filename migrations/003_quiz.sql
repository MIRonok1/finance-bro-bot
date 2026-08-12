-- Банк технических вопросов и попытки прохождения.

CREATE TABLE IF NOT EXISTS topics (
    id          INTEGER PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO topics (id, slug, title, sort_order) VALUES
    (1, 'dcf', 'DCF', 1),
    (2, 'multiples', 'Мультипликаторы', 2),
    (3, 'lbo', 'LBO', 3),
    (4, 'accounting', 'Accounting', 4),
    (5, 'ma', 'M&A', 5);

-- type: mcq (options_json + correct_key), numeric (correct_answer + tolerance_pct),
-- open (correct_answer используется как эталонный разбор, оценивается самим пользователем).
CREATE TABLE IF NOT EXISTS questions (
    id              INTEGER PRIMARY KEY,
    topic_id        INTEGER NOT NULL REFERENCES topics(id),
    type            TEXT NOT NULL CHECK (type IN ('mcq', 'numeric', 'open')),
    difficulty      INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
    body            TEXT NOT NULL,
    options_json    TEXT,
    correct_key     TEXT,
    correct_answer  TEXT,
    tolerance_pct   REAL,
    explanation     TEXT NOT NULL,
    source          TEXT,
    status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'rejected')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_questions_topic_status ON questions(topic_id, status);

CREATE TABLE IF NOT EXISTS attempts (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(telegram_id),
    question_id     INTEGER NOT NULL REFERENCES questions(id),
    session_id      TEXT NOT NULL,
    user_answer     TEXT,
    is_correct      INTEGER NOT NULL,
    answered_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_attempts_user_question ON attempts(user_id, question_id);
