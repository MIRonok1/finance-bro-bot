from datetime import date
from decimal import Decimal

import aiosqlite
import pytest

import app.portfolio.repo as repo_module
from app.db import apply_migrations, upsert_user
from app.portfolio import repo
from app.portfolio.logic import INITIAL_CASH_KOPECKS


async def _conn(user_id: int = 1) -> aiosqlite.Connection:
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await apply_migrations(conn)
    await upsert_user(conn, telegram_id=user_id, username="u", is_admin=False)
    return conn


@pytest.mark.asyncio
async def test_get_or_create_portfolio_creates_with_initial_cash():
    conn = await _conn()
    try:
        portfolio = await repo.get_or_create_portfolio(conn, user_id=1)
        assert portfolio.cash_kopecks == INITIAL_CASH_KOPECKS
        assert portfolio.equity_open_kopecks == INITIAL_CASH_KOPECKS
        assert portfolio.imoex_open_value is None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_get_or_create_portfolio_is_idempotent():
    conn = await _conn()
    try:
        p1 = await repo.get_or_create_portfolio(conn, user_id=1)
        p2 = await repo.get_or_create_portfolio(conn, user_id=1)
        assert p1.id == p2.id
        cursor = await conn.execute("SELECT COUNT(*) FROM portfolios WHERE user_id = 1")
        (count,) = await cursor.fetchone()
        assert count == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_apply_buy_creates_holding_and_order():
    conn = await _conn()
    try:
        portfolio = await repo.get_or_create_portfolio(conn, user_id=1)
        await repo.apply_buy(
            conn,
            portfolio.id,
            ticker="SBER",
            quantity=10,
            price_kopecks=28550,
            new_cash_kopecks=portfolio.cash_kopecks - 285500,
            new_quantity=10,
            new_avg_price_kopecks=28550,
        )
        holding = await repo.get_holding(conn, portfolio.id, "SBER")
        assert holding is not None
        assert holding.quantity == 10
        assert holding.avg_price_kopecks == 28550

        cursor = await conn.execute(
            "SELECT COUNT(*) FROM orders WHERE portfolio_id = ? AND side = 'buy'", (portfolio.id,)
        )
        (count,) = await cursor.fetchone()
        assert count == 1

        cursor = await conn.execute(
            "SELECT cash_kopecks FROM portfolios WHERE id = ?", (portfolio.id,)
        )
        (cash,) = await cursor.fetchone()
        assert cash == portfolio.cash_kopecks - 285500
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_apply_sell_updates_holding_and_cash():
    conn = await _conn()
    try:
        portfolio = await repo.get_or_create_portfolio(conn, user_id=1)
        await repo.apply_buy(
            conn, portfolio.id, "SBER", 10, 28550, portfolio.cash_kopecks - 285500, 10, 28550
        )
        await repo.apply_sell(
            conn,
            portfolio.id,
            ticker="SBER",
            quantity=4,
            price_kopecks=30000,
            new_cash_kopecks=portfolio.cash_kopecks - 285500 + 120000,
            new_quantity=6,
        )
        holding = await repo.get_holding(conn, portfolio.id, "SBER")
        assert holding.quantity == 6

        cursor = await conn.execute(
            "SELECT cash_kopecks FROM portfolios WHERE id = ?", (portfolio.id,)
        )
        (cash,) = await cursor.fetchone()
        assert cash == portfolio.cash_kopecks - 285500 + 120000
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_list_holdings_excludes_zero_quantity():
    conn = await _conn()
    try:
        portfolio = await repo.get_or_create_portfolio(conn, user_id=1)
        await repo.apply_buy(conn, portfolio.id, "SBER", 10, 28550, 0, 10, 28550)
        await repo.apply_sell(conn, portfolio.id, "SBER", 10, 30000, 300000, 0)
        holdings = await repo.list_holdings(conn, portfolio.id)
        assert holdings == []
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_price_cache_hit_within_ttl():
    conn = await _conn()
    try:
        await repo.set_cached_price_kopecks(conn, "SBER", 28550)
        price = await repo.get_cached_price_kopecks(conn, "SBER", ttl_seconds=300)
        assert price == 28550
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_price_cache_miss_when_expired():
    conn = await _conn()
    try:
        await repo.set_cached_price_kopecks(conn, "SBER", 28550)
        # искусственно «состариваем» запись
        await conn.execute(
            "UPDATE price_cache SET fetched_at = datetime('now', '-1 hour') WHERE ticker = 'SBER'"
        )
        await conn.commit()
        price = await repo.get_cached_price_kopecks(conn, "SBER", ttl_seconds=300)
        assert price is None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_price_cache_miss_for_unknown_ticker():
    conn = await _conn()
    try:
        assert await repo.get_cached_price_kopecks(conn, "UNKNOWN") is None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_set_cached_price_kopecks_upserts():
    conn = await _conn()
    try:
        await repo.set_cached_price_kopecks(conn, "SBER", 28550)
        await repo.set_cached_price_kopecks(conn, "SBER", 29000)
        price = await repo.get_cached_price_kopecks(conn, "SBER")
        assert price == 29000
        cursor = await conn.execute("SELECT COUNT(*) FROM price_cache WHERE ticker = 'SBER'")
        (count,) = await cursor.fetchone()
        assert count == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_list_held_tickers_only_positive_quantity():
    conn = await _conn()
    try:
        portfolio = await repo.get_or_create_portfolio(conn, user_id=1)
        await repo.apply_buy(conn, portfolio.id, "SBER", 10, 28550, 0, 10, 28550)
        await repo.apply_buy(conn, portfolio.id, "GAZP", 5, 15000, 0, 5, 15000)
        await repo.apply_sell(conn, portfolio.id, "GAZP", 5, 16000, 0, 0)
        assert await repo.list_held_tickers(conn) == ["SBER"]
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_maybe_reset_daily_reference_noop_same_day(monkeypatch):
    conn = await _conn()
    try:
        monkeypatch.setattr(repo_module, "today_msk", lambda: date(2026, 8, 12))
        # Портфель создаётся с equity_open_date == сегодня, поэтому вызов в
        # тот же день — no-op, даже если переданы другие equity/IMOEX.
        portfolio = await repo.get_or_create_portfolio(conn, user_id=1)
        updated = await repo.maybe_reset_daily_reference(
            conn, portfolio, 500_000_00, Decimal("3000")
        )
        assert updated.equity_open_kopecks == INITIAL_CASH_KOPECKS
        assert updated.imoex_open_value is None

        updated2 = await repo.maybe_reset_daily_reference(
            conn, updated, 999_999_00, Decimal("9999")
        )
        assert updated2.equity_open_kopecks == INITIAL_CASH_KOPECKS
        assert updated2.imoex_open_value is None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_maybe_reset_daily_reference_resets_on_new_day(monkeypatch):
    conn = await _conn()
    try:
        monkeypatch.setattr(repo_module, "today_msk", lambda: date(2026, 8, 12))
        portfolio = await repo.get_or_create_portfolio(conn, user_id=1)
        await repo.maybe_reset_daily_reference(conn, portfolio, 500_000_00, Decimal("3000"))

        monkeypatch.setattr(repo_module, "today_msk", lambda: date(2026, 8, 13))
        reloaded = await repo.get_or_create_portfolio(conn, user_id=1)
        updated = await repo.maybe_reset_daily_reference(
            conn, reloaded, 520_000_00, Decimal("3050")
        )
        assert updated.equity_open_kopecks == 520_000_00
        assert updated.equity_open_date == "2026-08-13"
        assert updated.imoex_open_value == Decimal("3050")
    finally:
        await conn.close()
