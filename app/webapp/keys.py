"""Типизированные ключи aiohttp Application — общие между server.py и
api.py, чтобы app["db"]/app["settings"] не ловили NotAppKeyWarning."""

from __future__ import annotations

import aiosqlite
from aiohttp import web

from app.config import Settings

DB_KEY: web.AppKey[aiosqlite.Connection] = web.AppKey("db", aiosqlite.Connection)
SETTINGS_KEY: web.AppKey[Settings] = web.AppKey("settings", Settings)
