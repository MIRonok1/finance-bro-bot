"""Реестр WebSocket-подписок на живые цены портфеля (Фаза 4).

Только в памяти процесса — и это осознанно нормально: если процесс
перезапустится (Netrun усыпляет при простое), клиент просто переподключится
и подпишется заново. Это не то состояние, которое CLAUDE.md запрещает
терять («Никакого состояния в памяти, которое нельзя потерять») — тут
нечего терять, кроме факта "кто сейчас смотрит", который тривиально
восстанавливается новым подключением."""

from __future__ import annotations

from aiohttp import web


class SubscriptionHub:
    def __init__(self) -> None:
        self._subscriptions: dict[web.WebSocketResponse, set[str]] = {}

    def subscribe(self, ws: web.WebSocketResponse, tickers: set[str]) -> None:
        self._subscriptions[ws] = tickers

    def unsubscribe_all(self, ws: web.WebSocketResponse) -> None:
        self._subscriptions.pop(ws, None)

    def subscribed_tickers(self) -> set[str]:
        """Union тикеров по всем живым подключениям — именно их и нужно
        поллить, не больше."""
        result: set[str] = set()
        for tickers in self._subscriptions.values():
            result |= tickers
        return result

    async def broadcast(self, ticker: str, payload: dict) -> None:
        # Список соединений снимаем заранее — subscribe/unsubscribe может
        # менять словарь конкурентно, пока мы ждём send_json на другом сокете.
        for ws in list(self._subscriptions):
            if ticker not in self._subscriptions.get(ws, set()):
                continue
            if ws.closed:
                continue
            try:
                await ws.send_json(payload)
            except ConnectionResetError:
                # Клиент уже отвалился, но close() из хендлера ещё не
                # добежал до finally — не роняем весь broadcast из-за этого.
                continue
