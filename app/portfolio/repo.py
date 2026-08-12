"""Доступ к БД для симулятора портфеля: portfolios, holdings, orders,
price_cache. Все денежные поля — int-копейки."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import aiosqlite

from app.portfolio.logic import INITIAL_CASH_KOPECKS
from app.timeutils import today_msk

PRICE_CACHE_TTL_SECONDS = 300


@dataclass
class Portfolio:
    id: int
    user_id: int
    cash_kopecks: int
    equity_open_kopecks: int
    equity_open_date: str
    imoex_open_value: Decimal | None


@dataclass
class Holding:
    ticker: str
    quantity: int
    avg_price_kopecks: int


async def get_or_create_portfolio(conn: aiosqlite.Connection, user_id: int) -> Portfolio:
    row = await (
        await conn.execute(
            "SELECT id, user_id, cash_kopecks, equity_open_kopecks, equity_open_date, "
            "imoex_open_value FROM portfolios WHERE user_id = ?",
            (user_id,),
        )
    ).fetchone()
    if row is not None:
        return _row_to_portfolio(row)

    today = today_msk().isoformat()
    cursor = await conn.execute(
        """
        INSERT INTO portfolios
            (user_id, cash_kopecks, equity_open_kopecks, equity_open_date, imoex_open_value)
        VALUES (?, ?, ?, ?, NULL)
        """,
        (user_id, INITIAL_CASH_KOPECKS, INITIAL_CASH_KOPECKS, today),
    )
    await conn.commit()
    return Portfolio(
        id=cursor.lastrowid,
        user_id=user_id,
        cash_kopecks=INITIAL_CASH_KOPECKS,
        equity_open_kopecks=INITIAL_CASH_KOPECKS,
        equity_open_date=today,
        imoex_open_value=None,
    )


def _row_to_portfolio(row: aiosqlite.Row) -> Portfolio:
    imoex_open = Decimal(row["imoex_open_value"]) if row["imoex_open_value"] is not None else None
    return Portfolio(
        id=row["id"],
        user_id=row["user_id"],
        cash_kopecks=row["cash_kopecks"],
        equity_open_kopecks=row["equity_open_kopecks"],
        equity_open_date=row["equity_open_date"],
        imoex_open_value=imoex_open,
    )


async def maybe_reset_daily_reference(
    conn: aiosqlite.Connection,
    portfolio: Portfolio,
    current_equity_kopecks: int,
    current_imoex: Decimal,
) -> Portfolio:
    """Раз в сутки (Europe/Moscow) фиксирует точку отсчёта для дневного P&L
    и сравнения с IMOEX — при первом обращении к портфелю в новый день."""
    today = today_msk().isoformat()
    if portfolio.equity_open_date == today:
        return portfolio

    await conn.execute(
        "UPDATE portfolios SET equity_open_kopecks = ?, equity_open_date = ?, "
        "imoex_open_value = ? WHERE id = ?",
        (current_equity_kopecks, today, str(current_imoex), portfolio.id),
    )
    # Тот же переход дня — точка для графика equity в Mini App (Фаза 3).
    # INSERT OR IGNORE — снепшот на сегодня пишется максимум один раз.
    await conn.execute(
        "INSERT OR IGNORE INTO portfolio_daily_snapshots "
        "(portfolio_id, snapshot_date, equity_kopecks, imoex_value) VALUES (?, ?, ?, ?)",
        (portfolio.id, today, current_equity_kopecks, str(current_imoex)),
    )
    await conn.commit()
    portfolio.equity_open_kopecks = current_equity_kopecks
    portfolio.equity_open_date = today
    portfolio.imoex_open_value = current_imoex
    return portfolio


async def get_equity_history(
    conn: aiosqlite.Connection, portfolio_id: int, days: int = 30
) -> list[tuple[str, int]]:
    """(дата, equity_kopecks) за последние `days` дней, по возрастанию даты."""
    cursor = await conn.execute(
        """
        SELECT snapshot_date, equity_kopecks FROM portfolio_daily_snapshots
        WHERE portfolio_id = ?
        ORDER BY snapshot_date DESC
        LIMIT ?
        """,
        (portfolio_id, days),
    )
    rows = await cursor.fetchall()
    return [(r["snapshot_date"], r["equity_kopecks"]) for r in reversed(rows)]


async def list_holdings(conn: aiosqlite.Connection, portfolio_id: int) -> list[Holding]:
    cursor = await conn.execute(
        "SELECT ticker, quantity, avg_price_kopecks FROM holdings "
        "WHERE portfolio_id = ? AND quantity > 0 ORDER BY ticker",
        (portfolio_id,),
    )
    rows = await cursor.fetchall()
    return [
        Holding(
            ticker=r["ticker"], quantity=r["quantity"], avg_price_kopecks=r["avg_price_kopecks"]
        )
        for r in rows
    ]


async def get_holding(conn: aiosqlite.Connection, portfolio_id: int, ticker: str) -> Holding | None:
    row = await (
        await conn.execute(
            "SELECT ticker, quantity, avg_price_kopecks FROM holdings "
            "WHERE portfolio_id = ? AND ticker = ?",
            (portfolio_id, ticker),
        )
    ).fetchone()
    if row is None:
        return None
    return Holding(
        ticker=row["ticker"], quantity=row["quantity"], avg_price_kopecks=row["avg_price_kopecks"]
    )


async def apply_buy(
    conn: aiosqlite.Connection,
    portfolio_id: int,
    ticker: str,
    quantity: int,
    price_kopecks: int,
    new_cash_kopecks: int,
    new_quantity: int,
    new_avg_price_kopecks: int,
) -> None:
    await conn.execute(
        "UPDATE portfolios SET cash_kopecks = ? WHERE id = ?", (new_cash_kopecks, portfolio_id)
    )
    await conn.execute(
        """
        INSERT INTO holdings (portfolio_id, ticker, quantity, avg_price_kopecks)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(portfolio_id, ticker) DO UPDATE SET
            quantity = excluded.quantity, avg_price_kopecks = excluded.avg_price_kopecks
        """,
        (portfolio_id, ticker, new_quantity, new_avg_price_kopecks),
    )
    await conn.execute(
        "INSERT INTO orders (portfolio_id, ticker, side, quantity, price_kopecks) "
        "VALUES (?, ?, 'buy', ?, ?)",
        (portfolio_id, ticker, quantity, price_kopecks),
    )
    await conn.commit()


async def apply_sell(
    conn: aiosqlite.Connection,
    portfolio_id: int,
    ticker: str,
    quantity: int,
    price_kopecks: int,
    new_cash_kopecks: int,
    new_quantity: int,
) -> None:
    await conn.execute(
        "UPDATE portfolios SET cash_kopecks = ? WHERE id = ?", (new_cash_kopecks, portfolio_id)
    )
    await conn.execute(
        "UPDATE holdings SET quantity = ? WHERE portfolio_id = ? AND ticker = ?",
        (new_quantity, portfolio_id, ticker),
    )
    await conn.execute(
        "INSERT INTO orders (portfolio_id, ticker, side, quantity, price_kopecks) "
        "VALUES (?, ?, 'sell', ?, ?)",
        (portfolio_id, ticker, quantity, price_kopecks),
    )
    await conn.commit()


# --- price_cache: TTL-кэш котировок, чтобы не дёргать MOEX ISS на каждый чих ---


async def get_cached_price_kopecks(
    conn: aiosqlite.Connection, ticker: str, ttl_seconds: int = PRICE_CACHE_TTL_SECONDS
) -> int | None:
    row = await (
        await conn.execute(
            "SELECT price_kopecks FROM price_cache WHERE ticker = ? "
            "AND fetched_at >= datetime('now', ?)",
            (ticker, f"-{ttl_seconds} seconds"),
        )
    ).fetchone()
    return row["price_kopecks"] if row else None


async def set_cached_price_kopecks(
    conn: aiosqlite.Connection, ticker: str, price_kopecks: int
) -> None:
    await conn.execute(
        """
        INSERT INTO price_cache (ticker, price_kopecks, fetched_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(ticker) DO UPDATE SET
            price_kopecks = excluded.price_kopecks, fetched_at = datetime('now')
        """,
        (ticker, price_kopecks),
    )
    await conn.commit()


async def list_all_cached_tickers(conn: aiosqlite.Connection) -> list[str]:
    """Все тикеры, когда-либо запрошенные (для фоновой задачи обновления)."""
    cursor = await conn.execute("SELECT DISTINCT ticker FROM price_cache")
    rows = await cursor.fetchall()
    return [r["ticker"] for r in rows]


async def list_held_tickers(conn: aiosqlite.Connection) -> list[str]:
    """Тикеры, реально присутствующие хоть в одном портфеле — их и обновляем
    в фоне, не тратя запросы на давно забытые котировки."""
    cursor = await conn.execute("SELECT DISTINCT ticker FROM holdings WHERE quantity > 0")
    rows = await cursor.fetchall()
    return [r["ticker"] for r in rows]


async def list_held_tickers_for_user(conn: aiosqlite.Connection, user_id: int) -> list[str]:
    """Тикеры конкретно этого пользователя — для WS-подписки на живые цены
    (Фаза 4). В отличие от list_held_tickers (все портфели, используется
    фоновым 5-минутным рефрешером), здесь нужен just-this-user срез."""
    cursor = await conn.execute(
        """
        SELECT h.ticker FROM holdings h
        JOIN portfolios p ON p.id = h.portfolio_id
        WHERE p.user_id = ? AND h.quantity > 0
        """,
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [r["ticker"] for r in rows]
