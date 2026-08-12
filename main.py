"""Точка входа: long polling. Никаких вебхуков, никакого HTTP-сервера.

Падаем с ненулевым кодом на фатальной ошибке — платформа (Netrun) сама
перезапустит процесс. Всё восстанавливаемое состояние живёт в БД, не в
памяти процесса.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import MenuButtonWebApp, WebAppInfo

from app.config import load_settings
from app.db import open_db
from app.fsm_storage import SQLiteStorage
from app.handlers import admin, common, mental_math, payments, portfolio, quiz, review, stats
from app.middlewares import ErrorHandlingMiddleware, ThrottlingMiddleware
from app.portfolio.background import refresh_price_cache_loop
from app.webapp.server import run_webapp_server


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )


async def main() -> None:
    settings = load_settings()
    setup_logging(settings.log_level)
    logger = logging.getLogger("main")
    logger.info(
        "Стартуем. db_path=%s paywall_enabled=%s", settings.db_path, settings.paywall_enabled
    )

    db = await open_db(settings.db_path)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=SQLiteStorage(db))

    # ErrorHandlingMiddleware — снаружи, чтобы ловить исключения из всех
    # остальных middleware и хендлеров.
    dp.update.outer_middleware(ErrorHandlingMiddleware())
    dp.update.outer_middleware(ThrottlingMiddleware())

    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(quiz.router)
    dp.include_router(mental_math.router)
    dp.include_router(stats.router)
    dp.include_router(review.router)
    dp.include_router(portfolio.router)
    dp.include_router(payments.router)

    # Прокидываем зависимости в хендлеры по имени параметра (db, settings).
    dp["db"] = db
    dp["settings"] = settings

    # Фоновая задача обновления кэша котировок MOEX. Живёт только в памяти
    # процесса — переживает рестарт как обычный кэш, ничего критичного не теряет.
    price_refresh_task = asyncio.create_task(refresh_price_cache_loop(db))

    # Mini App: aiohttp-сервер в том же процессе (Фаза 3, см. CLAUDE.md).
    webapp_runner = await run_webapp_server(db, settings)

    if settings.webapp_url:
        # Постоянная кнопка "☰ Приложение" рядом с полем ввода — стандартный
        # способ открыть Mini App, не команда. Без webapp_url не трогаем
        # меню, чтобы не сломать бота ссылкой в никуда.
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Приложение", web_app=WebAppInfo(url=settings.webapp_url)
            )
        )
    else:
        logger.warning("WEBAPP_URL не задан — кнопка Mini App в боте не включена.")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        price_refresh_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await price_refresh_task
        await webapp_runner.cleanup()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
