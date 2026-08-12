-- Ежедневные снепшоты equity портфеля — нужны для графика в Mini App
-- (Фаза 3). Пишутся раз в сутки той же функцией, что двигает
-- equity_open_kopecks/imoex_open_value (см. portfolio/repo.py).

CREATE TABLE IF NOT EXISTS portfolio_daily_snapshots (
    portfolio_id    INTEGER NOT NULL REFERENCES portfolios(id),
    snapshot_date   TEXT NOT NULL,
    equity_kopecks  INTEGER NOT NULL,
    imoex_value     TEXT,
    PRIMARY KEY (portfolio_id, snapshot_date)
);
