"""Общие хелперы для тестов Mini App backend (app/webapp/*) — подпись
initData тем же алгоритмом, что app/webapp/auth.py, и поднятие полного
aiohttp-приложения через aiohttp.test_utils.

Вынесено из tests/test_webapp_integration.py, чтобы не дублировать один и
тот же блок в каждом новом test_webapp_*.py файле (Фаза 4 добавляет
несколько таких файлов подряд)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import aiosqlite
from aiohttp.test_utils import TestClient, TestServer

from app.config import Settings
from app.db import apply_migrations
from app.portfolio.ws_hub import SubscriptionHub
from app.webapp.server import create_app

BOT_TOKEN = "123456:fake-token"


def signed_init_data(user_id: int, bot_token: str = BOT_TOKEN) -> str:
    user = {"id": user_id, "first_name": "Dima"}
    payload = {"auth_date": str(int(time.time())), "user": json.dumps(user)}
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(payload)


async def make_client(
    settings: Settings | None = None, hub: SubscriptionHub | None = None
) -> tuple[TestClient, aiosqlite.Connection]:
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await apply_migrations(conn)
    settings = settings or Settings(bot_token=BOT_TOKEN, admin_ids="1")
    hub = hub or SubscriptionHub()
    app = create_app(conn, settings, hub)
    client = TestClient(TestServer(app))
    await client.start_server()
    return client, conn
