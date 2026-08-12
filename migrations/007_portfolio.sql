-- Симулятор портфеля на данных MOEX (Веха 5, Фаза 2).
-- Деньги — целые копейки (INTEGER), никогда float (см. CLAUDE.md).

CREATE TABLE IF NOT EXISTS portfolios (
    id                  INTEGER PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES users(telegram_id),
    cash_kopecks        INTEGER NOT NULL,
    -- Точка отсчёта для дневного P&L и сравнения с IMOEX: обновляется раз в
    -- сутки (Europe/Moscow) при первом обращении к портфелю в этот день.
    equity_open_kopecks INTEGER NOT NULL,
    equity_open_date    TEXT NOT NULL,
    imoex_open_value    TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id)
);

CREATE TABLE IF NOT EXISTS holdings (
    id                  INTEGER PRIMARY KEY,
    portfolio_id        INTEGER NOT NULL REFERENCES portfolios(id),
    ticker              TEXT NOT NULL,
    quantity            INTEGER NOT NULL,
    avg_price_kopecks   INTEGER NOT NULL,
    UNIQUE (portfolio_id, ticker)
);

CREATE TABLE IF NOT EXISTS orders (
    id                  INTEGER PRIMARY KEY,
    portfolio_id        INTEGER NOT NULL REFERENCES portfolios(id),
    ticker              TEXT NOT NULL,
    side                TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity            INTEGER NOT NULL,
    price_kopecks       INTEGER NOT NULL,
    executed_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_orders_portfolio ON orders(portfolio_id);

-- TTL-кэш котировок MOEX ISS, чтобы не дёргать внешний API на каждый чих.
CREATE TABLE IF NOT EXISTS price_cache (
    ticker              TEXT PRIMARY KEY,
    price_kopecks       INTEGER NOT NULL,
    fetched_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
