"""Получение цены с TTL-кэшем: сначала БД (price_cache), при устаревании —
живой запрос к MOEX ISS."""

from __future__ import annotations

from decimal import Decimal

import aiosqlite

from app.portfolio import moex_client, repo
from app.portfolio.logic import kopecks_to_rub, rub_to_kopecks


async def get_price_rub(conn: aiosqlite.Connection, ticker: str) -> Decimal:
    cached = await repo.get_cached_price_kopecks(conn, ticker)
    if cached is not None:
        return kopecks_to_rub(cached)

    price_rub = await moex_client.fetch_last_price(ticker)
    await repo.set_cached_price_kopecks(conn, ticker, rub_to_kopecks(price_rub))
    return price_rub


async def refresh_price(conn: aiosqlite.Connection, ticker: str) -> Decimal:
    """Принудительно обновляет цену в кэше, минуя TTL — вызывается фоновой
    задачей и после сделок, где важна максимально свежая котировка."""
    price_rub = await moex_client.fetch_last_price(ticker)
    await repo.set_cached_price_kopecks(conn, ticker, rub_to_kopecks(price_rub))
    return price_rub
