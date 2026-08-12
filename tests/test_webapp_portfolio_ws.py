"""Тесты WebSocket живых цен портфеля (app/webapp/portfolio_ws.py).

Не гоняем реальный ws_poll.ws_price_poll_loop (он бы дёрнул MOEX ISS,
недоступный в этой среде разработки) — вместо этого напрямую зовём
hub.broadcast(), как и советует план: happy-path проверяет именно
доставку через WebSocket, а не сам поллинг (он уже покрыт unit-тестами
moex_client при наличии сети на Netrun, см. doctor.py)."""

import asyncio
from urllib.parse import quote

import aiohttp
import pytest

from app.portfolio.ws_hub import SubscriptionHub
from tests.webapp_test_utils import make_client, signed_init_data


def _ws_url(user_id: int) -> str:
    init_data = signed_init_data(user_id)
    return f"/api/portfolio/ws?initData={quote(init_data, safe='')}"


async def _wait_until_subscribed(hub: SubscriptionHub, ticker: str, timeout: float = 2.0) -> None:
    """Хендлер сервера регистрирует подписку асинхронно (после ws.prepare()
    ещё идёт запрос в БД за тикерами) — клиентский ws_connect() возвращается
    раньше, чем hub.subscribe() успевает отработать. В проде эта гонка не
    ощутима (следующий бродкаст — не раньше чем через WS_POLL_INTERVAL_SECONDS
    секунд), но тест не должен полагаться на удачный тайминг."""
    async with asyncio.timeout(timeout):
        while ticker not in hub.subscribed_tickers():
            await asyncio.sleep(0.01)


async def _seed_holding(conn, user_id: int, ticker: str = "SBER") -> None:
    await conn.execute(
        "INSERT INTO users (telegram_id, username, is_admin) VALUES (?, NULL, 0)",
        (user_id,),
    )
    await conn.execute(
        """
        INSERT INTO portfolios (user_id, cash_kopecks, equity_open_kopecks, equity_open_date)
        VALUES (?, 100000000, 100000000, '2026-08-12')
        """,
        (user_id,),
    )
    cursor = await conn.execute("SELECT id FROM portfolios WHERE user_id = ?", (user_id,))
    portfolio_id = (await cursor.fetchone())["id"]
    await conn.execute(
        "INSERT INTO holdings (portfolio_id, ticker, quantity, avg_price_kopecks) "
        "VALUES (?, ?, 10, 25000)",
        (portfolio_id, ticker),
    )
    await conn.commit()


@pytest.mark.asyncio
async def test_ws_rejects_missing_init_data():
    client, conn = await make_client()
    try:
        with pytest.raises(aiohttp.WSServerHandshakeError):
            await client.ws_connect("/api/portfolio/ws")
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_ws_rejects_tampered_init_data():
    client, conn = await make_client()
    try:
        init_data = signed_init_data(1)
        bad = init_data[:-1] + ("0" if init_data[-1] != "0" else "1")
        with pytest.raises(aiohttp.WSServerHandshakeError):
            await client.ws_connect(f"/api/portfolio/ws?initData={quote(bad, safe='')}")
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_ws_sends_cached_price_snapshot_on_connect():
    hub = SubscriptionHub()
    client, conn = await make_client(hub=hub)
    try:
        await _seed_holding(conn, 1, "SBER")
        await conn.execute(
            "INSERT INTO price_cache (ticker, price_kopecks, fetched_at) "
            "VALUES ('SBER', 27000, datetime('now'))"
        )
        await conn.commit()

        ws = await client.ws_connect(_ws_url(1))
        try:
            msg = await ws.receive_json(timeout=5)
            assert msg == {"type": "price", "ticker": "SBER", "price_rub": "270"}
        finally:
            await ws.close()
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_ws_receives_broadcast_for_subscribed_ticker():
    hub = SubscriptionHub()
    client, conn = await make_client(hub=hub)
    try:
        await _seed_holding(conn, 1, "GAZP")

        ws = await client.ws_connect(_ws_url(1))
        try:
            await _wait_until_subscribed(hub, "GAZP")
            await hub.broadcast("GAZP", {"type": "price", "ticker": "GAZP", "price_rub": "150"})
            msg = await ws.receive_json(timeout=5)
            assert msg == {"type": "price", "ticker": "GAZP", "price_rub": "150"}
        finally:
            await ws.close()
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_ws_does_not_receive_broadcast_for_unsubscribed_ticker():
    hub = SubscriptionHub()
    client, conn = await make_client(hub=hub)
    try:
        await _seed_holding(conn, 1, "GAZP")  # подписан только на GAZP

        ws = await client.ws_connect(_ws_url(1))
        try:
            await hub.broadcast("SBER", {"type": "price", "ticker": "SBER", "price_rub": "999"})
            # ничего не пришло за разумное время -> broadcast не долетел
            with pytest.raises(TimeoutError):
                await ws.receive_json(timeout=0.3)
        finally:
            await ws.close()
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_hub_unsubscribes_on_disconnect():
    hub = SubscriptionHub()
    client, conn = await make_client(hub=hub)
    try:
        await _seed_holding(conn, 1, "GAZP")
        ws = await client.ws_connect(_ws_url(1))
        await _wait_until_subscribed(hub, "GAZP")
        await ws.close()
        # даём серверному хендлеру отработать finally после закрытия клиентом
        async with asyncio.timeout(2.0):
            while "GAZP" in hub.subscribed_tickers():
                await asyncio.sleep(0.01)
    finally:
        await client.close()
        await conn.close()
