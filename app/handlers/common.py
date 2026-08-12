"""Общие хендлеры: /start, /help, главное меню."""

from __future__ import annotations

import logging

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from app import texts
from app.config import Settings
from app.db import upsert_user
from app.keyboards import CB_MODULE_MOVED, main_menu

logger = logging.getLogger(__name__)

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, db: aiosqlite.Connection, settings: Settings) -> None:
    user = message.from_user
    is_admin = bool(user) and user.id in settings.admin_ids_set
    if user:
        await upsert_user(db, user.id, user.username, is_admin)
    await message.answer(texts.START_GREETING, reply_markup=main_menu(settings.webapp_url))


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP_TEXT)


@router.callback_query(F.data == CB_MODULE_MOVED)
async def on_module_moved(callback: CallbackQuery) -> None:
    """Фолбэк для кнопок «Теория и кейсы»/«Быстрый счёт» в main_menu(), когда
    WEBAPP_URL не задан — сами модули теперь только в Mini App (Фаза 4)."""
    await callback.answer(texts.MODULE_MOVED_TO_WEBAPP, show_alert=True)
