"""Фоновая задача обновления кэша котировок MOEX для тикеров, реально
присутствующих в чьих-то портфелях.

Сетевые сбои не должны ронять бот — ловим и логируем, следующий цикл
попробует снова. Задача — часть asyncio-приложения, а не отдельный процесс:
теряется и создаётся заново при рестарте, что нормально (см. CLAUDE.md:
никакого состояния в памяти, которое нельзя потерять — здесь только кэш)."""

from __future__ import annotations

import asyncio
import logging

import aiosqlite

from app.portfolio import price_service, repo

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 300


async def refresh_price_cache_loop(conn: aiosqlite.Connection) -> None:
    while True:
        try:
            tickers = await repo.list_held_tickers(conn)
            for ticker in tickers:
                try:
                    await price_service.refresh_price(conn, ticker)
                except Exception:
                    logger.exception("Не удалось обновить цену %s", ticker)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Ошибка в цикле обновления цен MOEX")

        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
