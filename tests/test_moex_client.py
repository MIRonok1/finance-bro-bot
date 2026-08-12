"""Тесты клиента MOEX ISS через httpx.MockTransport — без реального сетевого
доступа. Формат ответа основан на документации ISS (см. TODO: verify в
app/portfolio/moex_client.py) и должен быть сверен с реальным API отдельно."""

from decimal import Decimal

import httpx
import pytest

from app.portfolio.moex_client import MoexError, fetch_imoex_value, fetch_last_price


def _client_with_response(json_body: dict, status_code: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=json_body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_fetch_last_price_parses_valid_response():
    body = {"marketdata": {"columns": ["SECID", "LAST"], "data": [["SBER", 285.5]]}}
    client = _client_with_response(body)
    try:
        price = await fetch_last_price("SBER", client=client)
        assert price == Decimal("285.5")
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_fetch_last_price_raises_on_null_last():
    body = {"marketdata": {"columns": ["SECID", "LAST"], "data": [["SBER", None]]}}
    client = _client_with_response(body)
    try:
        with pytest.raises(MoexError, match="LAST=null"):
            await fetch_last_price("SBER", client=client)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_fetch_last_price_raises_on_empty_data():
    body = {"marketdata": {"columns": ["SECID", "LAST"], "data": []}}
    client = _client_with_response(body)
    try:
        with pytest.raises(MoexError, match="пуст"):
            await fetch_last_price("BADTICKER", client=client)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_fetch_last_price_raises_on_missing_block():
    client = _client_with_response({})
    try:
        with pytest.raises(MoexError, match="marketdata"):
            await fetch_last_price("SBER", client=client)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_fetch_last_price_raises_on_http_error():
    client = _client_with_response({}, status_code=500)
    try:
        with pytest.raises(MoexError):
            await fetch_last_price("SBER", client=client)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_fetch_imoex_value_parses_valid_response():
    body = {"marketdata": {"columns": ["SECID", "CURRENTVALUE"], "data": [["IMOEX", 3123.45]]}}
    client = _client_with_response(body)
    try:
        value = await fetch_imoex_value(client=client)
        assert value == Decimal("3123.45")
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_fetch_imoex_value_raises_on_null():
    body = {"marketdata": {"columns": ["SECID", "CURRENTVALUE"], "data": [["IMOEX", None]]}}
    client = _client_with_response(body)
    try:
        with pytest.raises(MoexError, match="CURRENTVALUE=null"):
            await fetch_imoex_value(client=client)
    finally:
        await client.aclose()
