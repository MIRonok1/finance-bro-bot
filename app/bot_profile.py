"""Публичный профиль бота (команды, описание) через Bot API.

Заменяет ручные шаги в BotFather (`/setcommands`, `/setdescription`,
`/setshortdescription`) — вызывается на каждом старте (см. `main.py`),
идемпотентно: Telegram просто перезаписывает те же значения, лишний вызов
ничего не портит.

**Единственное, что всё равно нельзя автоматизировать — сам `/newbot`.**
У BotFather нет API: только он выдаёт `BOT_TOKEN`, и получить его можно
только руками в чате с @BotFather.

Админские команды (`/admin`, `/review`, `/refund`) не попадают в общий
список команд (`BotCommandScopeDefault`) — иначе их видели бы в автодополнении
все пользователи. Вместо этого им ставится отдельный список через
`BotCommandScopeChat` персонально на каждого админа из `ADMIN_IDS`.
"""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

logger = logging.getLogger("bot_profile")

PUBLIC_COMMANDS: list[BotCommand] = [
    BotCommand(command="start", description="Регистрация и главное меню"),
    BotCommand(command="help", description="Список команд и модулей"),
    BotCommand(command="stats", description="Статистика, дневная серия, повторение слабых мест"),
    BotCommand(command="subscribe", description="Подписка на Stars"),
]

ADMIN_ONLY_COMMANDS: list[BotCommand] = [
    BotCommand(command="admin", description="Админ-панель"),
    BotCommand(command="review", description="Проверка черновиков вопросов"),
    BotCommand(command="refund", description="Возврат оплаты: /refund user_id charge_id"),
]

SHORT_DESCRIPTION = (
    "Тренажёр для подготовки к интервью в инвестбанкинг: теория, устный счёт, портфель на MOEX."
)

DESCRIPTION = (
    "Finance bro — тренажёр для подготовки к интервью в инвестбанкинг и на "
    "другие финансовые позиции.\n\n"
    "📚 Теория и кейсы — DCF, мультипликаторы, LBO, accounting, M&A\n"
    "🧮 Быстрый счёт — арифметика под интервью на время\n"
    "📈 Портфель — симулятор на данных MOEX\n\n"
    "/start — начать"
)


async def configure_bot_profile(bot: Bot, admin_ids: set[int]) -> None:
    """Выставляет команды и описание бота через Bot API."""
    await bot.set_my_commands(commands=PUBLIC_COMMANDS, scope=BotCommandScopeDefault())

    admin_commands = PUBLIC_COMMANDS + ADMIN_ONLY_COMMANDS
    for admin_id in admin_ids:
        try:
            await bot.set_my_commands(
                commands=admin_commands, scope=BotCommandScopeChat(chat_id=admin_id)
            )
        except TelegramBadRequest:
            # Админ ещё ни разу не писал боту (нет приватного чата с этим
            # chat_id) — Telegram отказывает. Не фатально: обычный список
            # команд у него всё равно будет, персональный донастроится после
            # первого /start. Не роняем весь старт бота из-за этого.
            logger.warning(
                "Не удалось выставить админский список команд для %s (вероятно, ещё не писал боту)",
                admin_id,
            )

    await bot.set_my_short_description(short_description=SHORT_DESCRIPTION)
    await bot.set_my_description(description=DESCRIPTION)
