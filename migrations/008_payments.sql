-- Пейволл на Telegram Stars (Веха 6). Всё бездействует, пока
-- PAYWALL_ENABLED=false — таблицы просто не используются.

CREATE TABLE IF NOT EXISTS entitlements (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(telegram_id),
    plan            TEXT NOT NULL,
    valid_until     TEXT NOT NULL,   -- UTC, формат datetime('now'): 'YYYY-MM-DD HH:MM:SS'
    source          TEXT NOT NULL,   -- 'stars_purchase' | 'admin_grant' | ...
    stars_paid      INTEGER,
    charge_id       TEXT UNIQUE,     -- telegram_payment_charge_id — идемпотентность
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_entitlements_user ON entitlements(user_id);

-- Дневной лимит бесплатных задач (считается только при PAYWALL_ENABLED=true).
CREATE TABLE IF NOT EXISTS daily_usage (
    user_id     INTEGER NOT NULL REFERENCES users(telegram_id),
    usage_date  TEXT NOT NULL,
    count       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, usage_date)
);
