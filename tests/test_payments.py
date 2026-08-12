from datetime import UTC, date, datetime, timedelta

import aiosqlite
import pytest

from app.config import Settings
from app.db import apply_migrations, upsert_user
from app.payments import gate, repo
from app.payments.plans import FREE_DAILY_TASKS, MONTHLY_PLAN


async def _conn(user_id: int = 1) -> aiosqlite.Connection:
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await apply_migrations(conn)
    await upsert_user(conn, telegram_id=user_id, username="u", is_admin=False)
    return conn


def _settings(paywall_enabled: bool) -> Settings:
    return Settings(bot_token="123:abc", admin_ids="1", paywall_enabled=paywall_enabled)


# --- repo.grant_entitlement / has_active_entitlement ---


@pytest.mark.asyncio
async def test_has_active_entitlement_false_initially():
    conn = await _conn()
    try:
        assert await repo.has_active_entitlement(conn, 1) is False
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_grant_entitlement_activates_subscription():
    conn = await _conn()
    try:
        created = await repo.grant_entitlement(
            conn,
            1,
            MONTHLY_PLAN.code,
            MONTHLY_PLAN.duration_days,
            source="stars_purchase",
            stars_paid=100,
            charge_id="charge_1",
        )
        assert created is True
        assert await repo.has_active_entitlement(conn, 1) is True
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_grant_entitlement_is_idempotent_by_charge_id():
    conn = await _conn()
    try:
        first = await repo.grant_entitlement(
            conn,
            1,
            MONTHLY_PLAN.code,
            30,
            source="stars_purchase",
            stars_paid=100,
            charge_id="dup_charge",
        )
        second = await repo.grant_entitlement(
            conn,
            1,
            MONTHLY_PLAN.code,
            30,
            source="stars_purchase",
            stars_paid=100,
            charge_id="dup_charge",
        )
        assert first is True
        assert second is False

        cursor = await conn.execute(
            "SELECT COUNT(*) FROM entitlements WHERE charge_id = 'dup_charge'"
        )
        (count,) = await cursor.fetchone()
        assert count == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_grant_entitlement_extends_from_existing_valid_until():
    conn = await _conn()
    try:
        await repo.grant_entitlement(
            conn, 1, MONTHLY_PLAN.code, 10, source="stars_purchase", charge_id="c1"
        )
        cursor = await conn.execute("SELECT valid_until FROM entitlements WHERE charge_id = 'c1'")
        (first_valid_until,) = await cursor.fetchone()

        await repo.grant_entitlement(
            conn, 1, MONTHLY_PLAN.code, 10, source="stars_purchase", charge_id="c2"
        )
        cursor = await conn.execute("SELECT valid_until FROM entitlements WHERE charge_id = 'c2'")
        (second_valid_until,) = await cursor.fetchone()

        fmt = "%Y-%m-%d %H:%M:%S"
        delta = datetime.strptime(second_valid_until, fmt) - datetime.strptime(
            first_valid_until, fmt
        )
        assert delta.days == 10  # продлили от истечения первой, а не от "сейчас"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_grant_entitlement_starts_fresh_when_previous_expired():
    conn = await _conn()
    try:
        expired = (datetime.now(UTC).replace(tzinfo=None) - timedelta(days=5)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        await conn.execute(
            "INSERT INTO entitlements (user_id, plan, valid_until, source, charge_id) "
            "VALUES (1, 'monthly', ?, 'admin_grant', 'old')",
            (expired,),
        )
        await conn.commit()
        assert await repo.has_active_entitlement(conn, 1) is False

        await repo.grant_entitlement(
            conn, 1, MONTHLY_PLAN.code, 30, source="stars_purchase", charge_id="new"
        )
        assert await repo.has_active_entitlement(conn, 1) is True
    finally:
        await conn.close()


# --- repo.daily_usage ---


@pytest.mark.asyncio
async def test_daily_usage_starts_at_zero():
    conn = await _conn()
    try:
        assert await repo.get_daily_usage_count(conn, 1, "2026-08-12") == 0
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_increment_daily_usage_accumulates():
    conn = await _conn()
    try:
        await repo.increment_daily_usage(conn, 1, "2026-08-12")
        await repo.increment_daily_usage(conn, 1, "2026-08-12")
        count = await repo.increment_daily_usage(conn, 1, "2026-08-12")
        assert count == 3
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_daily_usage_is_per_date():
    conn = await _conn()
    try:
        await repo.increment_daily_usage(conn, 1, "2026-08-12")
        assert await repo.get_daily_usage_count(conn, 1, "2026-08-13") == 0
    finally:
        await conn.close()


# --- gate.check_and_consume ---


@pytest.mark.asyncio
async def test_gate_always_allows_when_paywall_disabled():
    conn = await _conn()
    try:
        settings = _settings(paywall_enabled=False)
        for _ in range(FREE_DAILY_TASKS + 5):
            assert await gate.check_and_consume(conn, 1, settings) is True
        # ничего не должно было посчитаться
        cursor = await conn.execute("SELECT COUNT(*) FROM daily_usage")
        (count,) = await cursor.fetchone()
        assert count == 0
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_gate_blocks_after_free_limit_when_enabled(monkeypatch):
    import app.payments.gate as gate_module

    conn = await _conn()
    try:
        monkeypatch.setattr(gate_module, "today_msk", lambda: date(2026, 8, 12))
        settings = _settings(paywall_enabled=True)

        for _ in range(FREE_DAILY_TASKS):
            assert await gate.check_and_consume(conn, 1, settings) is True

        assert await gate.check_and_consume(conn, 1, settings) is False
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_gate_active_entitlement_bypasses_daily_limit(monkeypatch):
    import app.payments.gate as gate_module

    conn = await _conn()
    try:
        monkeypatch.setattr(gate_module, "today_msk", lambda: date(2026, 8, 12))
        settings = _settings(paywall_enabled=True)

        await repo.grant_entitlement(
            conn, 1, MONTHLY_PLAN.code, 30, source="stars_purchase", charge_id="active"
        )
        for _ in range(FREE_DAILY_TASKS + 10):
            assert await gate.check_and_consume(conn, 1, settings) is True

        # с активной подпиской бесплатный счётчик вообще не растёт
        cursor = await conn.execute("SELECT COUNT(*) FROM daily_usage WHERE user_id = 1")
        (count,) = await cursor.fetchone()
        assert count == 0
    finally:
        await conn.close()
