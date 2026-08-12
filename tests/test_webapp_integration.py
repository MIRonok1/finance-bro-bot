"""Интеграционные тесты полного aiohttp-приложения (сервер + auth-мидлварь
+ роуты вместе) через aiohttp.test_utils — без реального TCP-порта из
main.py.

Намеренно не тестируем здесь /api/portfolio (дашборд) — он делает живой
запрос к MOEX ISS (fetch_imoex_value) и в этой среде разработки без сети
завис бы на таймауте вместо честного ответа. Логика самого дашборда
(app/portfolio/dashboard.py) уже покрыта тестами через переиспользуемые
repo/logic-функции; /api/portfolio/history сети не требует и протестирован
ниже."""

import pytest

from tests.webapp_test_utils import make_client, signed_init_data


@pytest.mark.asyncio
async def test_healthz_is_public():
    client, conn = await make_client()
    try:
        resp = await client.get("/healthz")
        assert resp.status == 200
        assert await resp.json() == {"status": "ok"}
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_api_requires_auth():
    client, conn = await make_client()
    try:
        resp = await client.get("/api/me")
        assert resp.status == 401
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_api_me_with_valid_init_data_registers_user():
    client, conn = await make_client()
    try:
        init_data = signed_init_data(777)
        resp = await client.get("/api/me", headers={"Authorization": f"tma {init_data}"})
        assert resp.status == 200
        body = await resp.json()
        assert body["telegram_id"] == 777
        assert body["daily_streak"] == 0
        assert body["subscription"] == {"active": False, "plan": None}

        cursor = await conn.execute("SELECT COUNT(*) FROM users WHERE telegram_id = 777")
        (count,) = await cursor.fetchone()
        assert count == 1
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_fresh_user_can_hit_non_profile_endpoint_first():
    """Регрессия: раньше upsert_user происходил только в /api/me, и любой
    другой /api/* эндпоинт падал на FK-констрейнте для совсем нового
    пользователя. Регистрация теперь в auth_middleware, до диспетчеризации
    в конкретный хендлер."""
    client, conn = await make_client()
    try:
        init_data = signed_init_data(999)
        resp = await client.get("/api/quiz/stats", headers={"Authorization": f"tma {init_data}"})
        assert resp.status == 200
        assert await resp.json() == {"topics": [], "due_review": 0}
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_api_mental_math_stats_shape():
    client, conn = await make_client()
    try:
        init_data = signed_init_data(1)
        resp = await client.get(
            "/api/mental_math/stats", headers={"Authorization": f"tma {init_data}"}
        )
        assert resp.status == 200
        assert await resp.json() == {
            "best_streak": 0,
            "total_attempts": 0,
            "total_correct": 0,
            "daily": [],
        }
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_api_portfolio_history_shape_for_new_user():
    client, conn = await make_client()
    try:
        init_data = signed_init_data(1)
        resp = await client.get(
            "/api/portfolio/history", headers={"Authorization": f"tma {init_data}"}
        )
        assert resp.status == 200
        assert await resp.json() == {"history": []}
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_tampered_init_data_rejected_by_full_app():
    client, conn = await make_client()
    try:
        init_data = signed_init_data(1)
        bad = init_data[:-1] + ("0" if init_data[-1] != "0" else "1")
        resp = await client.get("/api/me", headers={"Authorization": f"tma {bad}"})
        assert resp.status == 401
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_index_html_served_at_root_when_no_build_present():
    """Без собранного webapp/dist сервер отдаёт только /api/* и /healthz —
    убеждаемся, что это деградирует чисто (404), а не падает с 500."""
    client, conn = await make_client()
    try:
        resp = await client.get("/")
        assert resp.status in (404, 200)  # 200 только если dist реально собран локально
    finally:
        await client.close()
        await conn.close()
