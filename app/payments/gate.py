"""Гейт бесплатных задач в день. При PAYWALL_ENABLED=false всегда пропускает
и ничего не считает — флаг управляет пейволлом целиком, как и требуется."""

from __future__ import annotations

import aiosqlite

from app.config import Settings
from app.payments import repo as payments_repo
from app.payments.plans import FREE_DAILY_TASKS
from app.timeutils import today_msk


async def check_and_consume(conn: aiosqlite.Connection, user_id: int, settings: Settings) -> bool:
    """True — можно начинать сессию (и это уже учтено в дневном лимите).
    False — бесплатный лимит на сегодня исчерпан."""
    if not settings.paywall_enabled:
        return True

    if await payments_repo.has_active_entitlement(conn, user_id):
        return True

    today = today_msk().isoformat()
    used = await payments_repo.get_daily_usage_count(conn, user_id, today)
    if used >= FREE_DAILY_TASKS:
        return False

    await payments_repo.increment_daily_usage(conn, user_id, today)
    return True
