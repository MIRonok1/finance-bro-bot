"""Админ-хендлеры. Доступ проверяется по ADMIN_IDS из конфига."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app import texts
from app.config import Settings

router = Router(name="admin")


@router.message(Command("admin"))
async def cmd_admin(message: Message, settings: Settings) -> None:
    user = message.from_user
    if not user or user.id not in settings.admin_ids_set:
        await message.answer(texts.ADMIN_ACCESS_DENIED)
        return
    await message.answer(texts.ADMIN_WELCOME)
