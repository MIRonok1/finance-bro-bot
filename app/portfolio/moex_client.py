"""Клиент MOEX ISS API — публичный, без авторизации, котировки с задержкой.

TODO: verify — ISS отдаёт данные блоками вида {"<block>": {"columns": [...],
"data": [[...], ...]}}, это документированный и стабильный формат для всех
эндпоинтов ISS. Однако точные имена колонок ('LAST' для последней цены на
борде TQBR, 'CURRENTVALUE' для значения индекса) взяты из публичной
документации ISS, а не проверены вживую здесь — в этой среде разработки нет
сетевого доступа к iss.moex.com. Прогони scripts/doctor.py на Netrun и
сверь реальный ответ перед тем, как полагаться на модуль в проде.
"""

from __future__ import annotations

from decimal import Decimal

import httpx

ISS_BASE = "https://iss.moex.com/iss"
DEFAULT_TIMEOUT = 10.0
STOCK_BOARD = "TQBR"
IMOEX_TICKER = "IMOEX"


class MoexError(Exception):
    """Не удалось получить или разобрать данные MOEX ISS."""


def _extract_value(payload: dict, block: str, column: str) -> str | int | float | None:
    data_block = payload.get(block)
    if not data_block:
        raise MoexError(f"В ответе ISS нет блока '{block}'")
    columns = data_block.get("columns", [])
    rows = data_block.get("data", [])
    if not rows:
        raise MoexError(f"Блок '{block}' пуст — нет данных")
    if column not in columns:
        raise MoexError(f"В блоке '{block}' нет колонки '{column}'")
    return rows[0][columns.index(column)]


async def fetch_last_price(ticker: str, client: httpx.AsyncClient | None = None) -> Decimal:
    """Текущая цена акции (борд TQBR), в рублях."""
    url = f"{ISS_BASE}/engines/stock/markets/shares/boards/{STOCK_BOARD}/securities/{ticker}.json"
    params = {"iss.meta": "off", "iss.only": "marketdata", "marketdata.columns": "SECID,LAST"}

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        value = _extract_value(response.json(), "marketdata", "LAST")
        if value is None:
            raise MoexError(f"LAST=null для {ticker} — рынок закрыт или тикер неверен")
        return Decimal(str(value))
    except httpx.HTTPError as exc:
        raise MoexError(f"Сетевая ошибка при запросе цены {ticker}: {exc}") from exc
    finally:
        if owns_client:
            await client.aclose()


async def fetch_last_prices(
    tickers: list[str], client: httpx.AsyncClient | None = None
) -> dict[str, Decimal]:
    """Цены сразу нескольких тикеров одним HTTP-запросом (батч через
    securities=A,B,C на том же эндпоинте) — для быстрого поллинга живых цен
    по WebSocket (Фаза 4), где дёргать MOEX по тикеру за тикером на каждый
    цикл было бы слишком тяжело. Тикеры без данных (LAST=null, опечатка,
    делистинг) просто пропускаются, а не роняют весь батч — вызывающий код
    (ws_poll.py) должен быть готов получить не все запрошенные тикеры.

    TODO: verify — как и весь модуль, батч через securities= не проверен
    вживую (нет сети до iss.moex.com в среде разработки), только по
    документированному формату ISS.
    """
    if not tickers:
        return {}

    url = f"{ISS_BASE}/engines/stock/markets/shares/boards/{STOCK_BOARD}/securities.json"
    params = {
        "iss.meta": "off",
        "iss.only": "marketdata",
        "marketdata.columns": "SECID,LAST",
        "securities": ",".join(tickers),
    }

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data_block = response.json().get("marketdata")
        if not data_block:
            raise MoexError("В ответе ISS нет блока 'marketdata'")
        columns = data_block.get("columns", [])
        secid_idx = columns.index("SECID")
        last_idx = columns.index("LAST")

        prices: dict[str, Decimal] = {}
        for row in data_block.get("data", []):
            last = row[last_idx]
            if last is None:
                continue
            prices[row[secid_idx]] = Decimal(str(last))
        return prices
    except httpx.HTTPError as exc:
        raise MoexError(f"Сетевая ошибка при батч-запросе цен {tickers}: {exc}") from exc
    finally:
        if owns_client:
            await client.aclose()


async def fetch_imoex_value(client: httpx.AsyncClient | None = None) -> Decimal:
    """Текущее значение индекса IMOEX."""
    url = f"{ISS_BASE}/engines/stock/markets/index/securities/{IMOEX_TICKER}.json"
    params = {
        "iss.meta": "off",
        "iss.only": "marketdata",
        "marketdata.columns": "SECID,CURRENTVALUE",
    }

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        value = _extract_value(response.json(), "marketdata", "CURRENTVALUE")
        if value is None:
            raise MoexError("CURRENTVALUE=null для IMOEX")
        return Decimal(str(value))
    except httpx.HTTPError as exc:
        raise MoexError(f"Сетевая ошибка при запросе IMOEX: {exc}") from exc
    finally:
        if owns_client:
            await client.aclose()
