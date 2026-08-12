"""Тесты новых read-запросов, добавленных для Mini App: дневная точность
mental math, история equity портфеля, активный план подписки."""

from datetime import date

import aiosqlite
import pytest

import app.portfolio.repo as portfolio_repo_module
from app.db import apply_migrations, upsert_user
from app.mental_math import repo as mm_repo
from app.payments import repo as payments_repo
from app.payments.plans import MONTHLY_PLAN
from app.portfolio import repo as portfolio_repo


async def _conn(user_id: int = 1) -> aiosqlite.Connection:
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await apply_migrations(conn)
    await upsert_user(conn, telegram_id=user_id, username="u", is_admin=False)
    return conn


@pytest.mark.asyncio
async def test_get_daily_accuracy_groups_by_day():
    conn = await _conn()
    try:
        await mm_repo.record_attempt(conn, 1, "cagr", 2, True, 1000)
        await mm_repo.record_attempt(conn, 1, "cagr", 2, False, 2000)
        series = await mm_repo.get_daily_accuracy(conn, 1, days=14)
        assert len(series) == 1
        d, total, correct = series[0]
        assert total == 2
        assert correct == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_get_daily_accuracy_excludes_other_users():
    conn = await _conn(user_id=1)
    try:
        await upsert_user(conn, telegram_id=2, username="other", is_admin=False)
        await mm_repo.record_attempt(conn, 1, "cagr", 2, True, 1000)
        await mm_repo.record_attempt(conn, 2, "cagr", 2, True, 1000)
        series = await mm_repo.get_daily_accuracy(conn, 1, days=14)
        assert sum(total for _, total, _ in series) == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_get_daily_accuracy_respects_days_window(monkeypatch):
    conn = await _conn()
    try:
        await mm_repo.record_attempt(conn, 1, "cagr", 2, True, 1000)
        await conn.execute(
            "UPDATE mental_math_attempts SET answered_at = datetime('now', '-30 days')"
        )
        await conn.commit()
        series = await mm_repo.get_daily_accuracy(conn, 1, days=14)
        assert series == []
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_get_equity_history_empty_initially():
    conn = await _conn()
    try:
        portfolio = await portfolio_repo.get_or_create_portfolio(conn, 1)
        history = await portfolio_repo.get_equity_history(conn, portfolio.id)
        assert history == []
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_get_equity_history_records_snapshot_on_daily_reset(monkeypatch):
    from decimal import Decimal

    conn = await _conn()
    try:
        monkeypatch.setattr(portfolio_repo_module, "today_msk", lambda: date(2026, 8, 12))
        portfolio = await portfolio_repo.get_or_create_portfolio(conn, 1)

        monkeypatch.setattr(portfolio_repo_module, "today_msk", lambda: date(2026, 8, 13))
        await portfolio_repo.maybe_reset_daily_reference(
            conn, portfolio, 105_000_00, Decimal("3100")
        )

        history = await portfolio_repo.get_equity_history(conn, portfolio.id, days=30)
        assert history == [("2026-08-13", 105_000_00)]
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_get_equity_history_does_not_duplicate_same_day(monkeypatch):
    from decimal import Decimal

    conn = await _conn()
    try:
        monkeypatch.setattr(portfolio_repo_module, "today_msk", lambda: date(2026, 8, 12))
        portfolio = await portfolio_repo.get_or_create_portfolio(conn, 1)

        monkeypatch.setattr(portfolio_repo_module, "today_msk", lambda: date(2026, 8, 13))
        await portfolio_repo.maybe_reset_daily_reference(
            conn, portfolio, 100_000_00, Decimal("3000")
        )
        # повторный вызов в тот же день — no-op (equity_open_date уже сегодня)
        await portfolio_repo.maybe_reset_daily_reference(
            conn, portfolio, 999_999_00, Decimal("9999")
        )

        history = await portfolio_repo.get_equity_history(conn, portfolio.id, days=30)
        assert len(history) == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_get_active_plan_none_without_entitlement():
    conn = await _conn()
    try:
        assert await payments_repo.get_active_plan(conn, 1) is None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_get_active_plan_returns_plan_code():
    conn = await _conn()
    try:
        await payments_repo.grant_entitlement(
            conn, 1, MONTHLY_PLAN.code, 30, source="stars_purchase", charge_id="c1"
        )
        assert await payments_repo.get_active_plan(conn, 1) == MONTHLY_PLAN.code
    finally:
        await conn.close()
