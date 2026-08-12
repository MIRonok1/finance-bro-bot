from unittest.mock import AsyncMock, call

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SetMyCommands
from aiogram.types import BotCommandScopeChat, BotCommandScopeDefault

from app.bot_profile import (
    ADMIN_ONLY_COMMANDS,
    PUBLIC_COMMANDS,
    configure_bot_profile,
)


@pytest.mark.asyncio
async def test_configure_bot_profile_sets_default_and_admin_scopes() -> None:
    bot = AsyncMock()

    await configure_bot_profile(bot, admin_ids={111, 222})

    bot.set_my_commands.assert_any_call(commands=PUBLIC_COMMANDS, scope=BotCommandScopeDefault())
    admin_commands = PUBLIC_COMMANDS + ADMIN_ONLY_COMMANDS
    bot.set_my_commands.assert_has_calls(
        [
            call(commands=admin_commands, scope=BotCommandScopeChat(chat_id=111)),
            call(commands=admin_commands, scope=BotCommandScopeChat(chat_id=222)),
        ],
        any_order=True,
    )
    assert bot.set_my_commands.await_count == 3  # default + 2 админа
    bot.set_my_short_description.assert_awaited_once()
    bot.set_my_description.assert_awaited_once()


@pytest.mark.asyncio
async def test_configure_bot_profile_survives_admin_without_private_chat() -> None:
    """Админ ещё не писал боту -> Telegram отвечает 400 на его личный scope.

    Не должно ронять остальную настройку профиля.
    """
    bot = AsyncMock()

    def set_my_commands_side_effect(*, commands, scope):
        if isinstance(scope, BotCommandScopeChat) and scope.chat_id == 999:
            raise TelegramBadRequest(
                method=SetMyCommands(commands=commands, scope=scope), message="chat not found"
            )
        return True

    bot.set_my_commands.side_effect = set_my_commands_side_effect

    await configure_bot_profile(bot, admin_ids={999})

    bot.set_my_short_description.assert_awaited_once()
    bot.set_my_description.assert_awaited_once()


def test_admin_commands_do_not_duplicate_public_ones() -> None:
    public_names = {c.command for c in PUBLIC_COMMANDS}
    admin_names = {c.command for c in ADMIN_ONLY_COMMANDS}
    assert public_names.isdisjoint(admin_names)
