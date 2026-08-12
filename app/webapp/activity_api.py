"""API для Duolingo-style календаря активности в Mini App (Фаза 4)."""

from __future__ import annotations

from datetime import timedelta

from aiohttp import web

from app.db import get_daily_streak, get_recent_activity_dates
from app.timeutils import today_msk
from app.webapp.keys import DB_KEY

routes = web.RouteTableDef()

ACTIVITY_WINDOW_DAYS = 28


@routes.get("/api/activity")
async def get_activity(request: web.Request) -> web.Response:
    tg_user = request["tg_user"]
    db = request.app[DB_KEY]

    streak = await get_daily_streak(db, tg_user.id)
    active_dates = await get_recent_activity_dates(db, tg_user.id, days=ACTIVITY_WINDOW_DAYS)

    today = today_msk()
    days = []
    for offset in range(ACTIVITY_WINDOW_DAYS - 1, -1, -1):
        d = today - timedelta(days=offset)
        days.append({"date": d.isoformat(), "active": d.isoformat() in active_dates})

    return web.json_response({"streak": streak, "days": days})
