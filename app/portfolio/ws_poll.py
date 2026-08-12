"""Быстрый цикл обновления цен для WebSocket-подписчиков (Фаза 4) —
отдельный от 5-минутного app/portfolio/background.py, который обслуживает
чат-дашборд/сделки и трогать который незачем.

Опрашивает MOEX ISS только по тикерам, которые кто-то реально сейчас
смотрит (SubscriptionHub.subscribed_tickers()) — не по всем закэшированным,
чтобы не долбить бесплатный публичный API впустую. Интервал — компромисс
между "живо" и "не долбить"; это инженерное решение, не цифра от
пользователя, крутить можно."""

from __future__ import annotations

import asyncio
import logging

import aiosqlite

from app.portfolio import moex_client, repo
from app.portfolio.logic import rub_to_kopecks
from app.portfolio.ws_hub import SubscriptionHub

logger = logging.getLogger(__name__)

WS_POLL_INTERVAL_SECONDS = 10


async def ws_price_poll_loop(conn: aiosqlite.Connection, hub: SubscriptionHub) -> None:
    while True:
        try:
            tickers = hub.subscribed_tickers()
            if tickers:
                prices = await moex_client.fetch_last_prices(list(tickers))
                for ticker, price_rub in prices.items():
                    await repo.set_cached_price_kopecks(conn, ticker, rub_to_kopecks(price_rub))
                    await hub.broadcast(
                        ticker, {"type": "price", "ticker": ticker, "price_rub": str(price_rub)}
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Ошибка в цикле live-обновления цен MOEX (WebSocket)")

        await asyncio.sleep(WS_POLL_INTERVAL_SECONDS)
