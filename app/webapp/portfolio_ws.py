"""WebSocket с живыми ценами по холдингам пользователя (Фаза 4).

Авторизация — как и везде, initData Telegram, но браузерный WebSocket не
умеет ставить кастомные заголовки на handshake, поэтому initData передаётся
query-параметром (?initData=...), а не заголовком Authorization. Это не
новый механизм авторизации — та же validate_init_data, просто источник
данных другой (см. auth_middleware в server.py)."""

from __future__ import annotations

import logging

from aiohttp import web

from app.portfolio import repo
from app.portfolio.logic import kopecks_to_rub
from app.portfolio.ws_hub import SubscriptionHub
from app.webapp.keys import DB_KEY, WS_HUB_KEY

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()


@routes.get("/api/portfolio/ws")
async def portfolio_ws(request: web.Request) -> web.WebSocketResponse:
    tg_user = request["tg_user"]  # уже провалидирован auth_middleware (initData из query)
    db = request.app[DB_KEY]
    hub: SubscriptionHub = request.app[WS_HUB_KEY]

    ws = web.WebSocketResponse(heartbeat=25)
    await ws.prepare(request)

    held = set(await repo.list_held_tickers_for_user(db, tg_user.id))
    hub.subscribe(ws, held)

    # Сразу отдаём то, что уже есть в кэше — не заставляем клиента ждать
    # первого тика поллинга (до 10 секунд, см. ws_poll.WS_POLL_INTERVAL_SECONDS).
    for ticker in held:
        cached_kopecks = await repo.get_cached_price_kopecks(db, ticker)
        if cached_kopecks is not None:
            await ws.send_json(
                {
                    "type": "price",
                    "ticker": ticker,
                    "price_rub": str(kopecks_to_rub(cached_kopecks)),
                }
            )

    try:
        async for msg in ws:
            if msg.type in (web.WSMsgType.ERROR, web.WSMsgType.CLOSE):
                break
    finally:
        hub.unsubscribe_all(ws)

    return ws
