"""Общие middleware: обработка ошибок, логирование, троттлинг.

Троттлинг хранит состояние в памяти процесса — это осознанно: при рестарте
достаточно, чтобы счётчик обнулился, никакой пользовательской логики за ним
нет. Это не то состояние, которое CLAUDE.md запрещает терять (FSM/прогресс
пользователя), поэтому Redis или БД здесь не нужны.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app import texts

logger = logging.getLogger(__name__)


def _extract_user_id(event: TelegramObject) -> int | None:
    if isinstance(event, Update):
        for attr in ("message", "callback_query", "edited_message", "my_chat_member"):
            inner = getattr(event, attr, None)
            if inner is not None and getattr(inner, "from_user", None):
                return inner.from_user.id
        return None
    from_user = getattr(event, "from_user", None)
    return from_user.id if from_user else None


class ErrorHandlingMiddleware(BaseMiddleware):
    """Ловит все необработанные исключения хендлеров: пользователю — вежливое
    сообщение, в лог — полный трейсбек с user_id. Не даёт боту упасть из-за
    ошибки в одном апдейте."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = _extract_user_id(event)
        try:
            return await handler(event, data)
        except Exception:
            logger.exception("Необработанная ошибка при обработке апдейта, user_id=%s", user_id)
            message = getattr(event, "message", None) or (
                event if hasattr(event, "answer") else None
            )
            try:
                if message is not None:
                    await message.answer(texts.ERROR_GENERIC)
                else:
                    callback = getattr(event, "callback_query", None)
                    if callback is not None:
                        await callback.answer(texts.ERROR_GENERIC, show_alert=True)
            except Exception:
                logger.exception("Не удалось отправить сообщение об ошибке, user_id=%s", user_id)
            return None


class ThrottlingMiddleware(BaseMiddleware):
    """Простой rate-limit по user_id: не чаще одного апдейта в `interval` секунд."""

    def __init__(self, interval: float = 0.7) -> None:
        self.interval = interval
        self._last_seen: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = _extract_user_id(event)
        if user_id is not None:
            now = time.monotonic()
            last = self._last_seen.get(user_id)
            if last is not None and now - last < self.interval:
                return None
            self._last_seen[user_id] = now
        return await handler(event, data)
