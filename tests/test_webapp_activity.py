"""Тесты GET /api/activity — Duolingo-style календарь (app/webapp/activity_api.py)."""

from datetime import date

import pytest

import app.db as db_module
import app.webapp.activity_api as activity_api_module
from app.db import touch_daily_streak
from tests.webapp_test_utils import make_client, signed_init_data


def _auth_headers(user_id: int) -> dict:
    return {"Authorization": f"tma {signed_init_data(user_id)}"}


@pytest.mark.asyncio
async def test_activity_shape_for_fresh_user():
    client, conn = await make_client()
    try:
        resp = await client.get("/api/activity", headers=_auth_headers(1))
        assert resp.status == 200
        body = await resp.json()
        assert body["streak"] == 0
        assert len(body["days"]) == 28
        assert all(d["active"] is False for d in body["days"])
        # по возрастанию: самый старый день первый, сегодня — последний
        assert body["days"][0]["date"] < body["days"][-1]["date"]
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_activity_reflects_touched_days(monkeypatch):
    client, conn = await make_client()
    try:
        # регистрируем пользователя через любой /api/* эндпоинт (тот же
        # паттерн, что test_fresh_user_can_hit_non_profile_endpoint_first)
        await client.get("/api/me", headers=_auth_headers(1))

        fake_today = date(2026, 8, 12)
        monkeypatch.setattr(db_module, "today_msk", lambda: fake_today)
        monkeypatch.setattr(activity_api_module, "today_msk", lambda: fake_today)
        await touch_daily_streak(conn, 1)

        resp = await client.get("/api/activity", headers=_auth_headers(1))
        body = await resp.json()
        assert body["days"][-1]["date"] == "2026-08-12"  # последний день окна — "сегодня"
        today_entry = next(d for d in body["days"] if d["date"] == "2026-08-12")
        assert today_entry["active"] is True
        assert body["streak"] == 1
    finally:
        await client.close()
        await conn.close()


@pytest.mark.asyncio
async def test_activity_requires_auth():
    client, conn = await make_client()
    try:
        resp = await client.get("/api/activity")
        assert resp.status == 401
    finally:
        await client.close()
        await conn.close()
