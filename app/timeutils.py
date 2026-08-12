"""Даты, видимые пользователю, — в Europe/Moscow; хранение времени — UTC
(см. CLAUDE.md). Используется для дневной серии и календаря повторений,
которые оперируют «днём пользователя», а не моментом времени в UTC."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def today_msk() -> date:
    return datetime.now(MOSCOW_TZ).date()
