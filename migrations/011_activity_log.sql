-- Duolingo-style календарь активности (Фаза 4). users.daily_streak/
-- last_active_date (миграция 006) остаётся источником истины для самого
-- счётчика серии — эта таблица только для календаря/heatmap "в какие дни
-- пользователь занимался", append-only, без истории изменений.

CREATE TABLE IF NOT EXISTS user_activity_days (
    user_id         INTEGER NOT NULL REFERENCES users(telegram_id),
    activity_date   TEXT NOT NULL,   -- Europe/Moscow дата, формат today_msk().isoformat()
    PRIMARY KEY (user_id, activity_date)
);
CREATE INDEX IF NOT EXISTS idx_activity_days_user ON user_activity_days(user_id, activity_date);
