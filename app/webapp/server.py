"""aiohttp-сервер Mini App: статика (собранный React) + /api/* + /healthz.

Работает в том же процессе и event loop, что и long polling бота — см.
main.py. Никакого отдельного деплоя/контейнера, только один дополнительный
TCP-порт рядом с обычным ботом (см. CLAUDE.md, Фаза 3)."""

from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite
from aiohttp import web
from aiohttp.web_log import AccessLogger

from app.config import Settings
from app.db import upsert_user
from app.portfolio.ws_hub import SubscriptionHub
from app.webapp.activity_api import routes as activity_routes
from app.webapp.api import routes
from app.webapp.auth import validate_init_data
from app.webapp.keys import DB_KEY, SETTINGS_KEY, WS_HUB_KEY
from app.webapp.mental_math_api import routes as mental_math_routes
from app.webapp.portfolio_ws import routes as portfolio_ws_routes
from app.webapp.quiz_api import routes as quiz_routes

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "webapp" / "dist"

# initData для WS-подключения едет query-параметром (браузерный WebSocket не
# умеет ставить кастомные заголовки на handshake) — обычный access-лог по
# умолчанию напечатал бы его в stdout (который собирает Netrun). Ни один
# другой путь initData через query не носит, поэтому один явный путь-
# исключение, а не общее правило редактирования логов.
_WS_PATH = "/api/portfolio/ws"


class _RedactingAccessLogger(AccessLogger):
    def log(self, request: web.BaseRequest, response: web.StreamResponse, time: float) -> None:
        if request.path == _WS_PATH:
            return
        super().log(request, response, time)


@web.middleware
async def auth_middleware(request: web.Request, handler):
    if not request.path.startswith("/api/"):
        return await handler(request)

    settings = request.app[SETTINGS_KEY]
    if request.path == _WS_PATH:
        # Браузерный WebSocket не может выставить заголовок Authorization на
        # handshake — initData едет query-параметром. Дальше — та же самая
        # проверка validate_init_data, не новый механизм авторизации.
        init_data = request.query.get("initData", "")
    else:
        auth_header = request.headers.get("Authorization", "")
        init_data = auth_header[len("tma ") :] if auth_header.startswith("tma ") else ""

    tg_user = validate_init_data(init_data, settings.bot_token)
    if tg_user is None:
        return web.json_response({"error": "unauthorized"}, status=401)

    # Регистрируем пользователя здесь, а не только в /api/me: остальные
    # ручки (portfolio, quiz/stats, ...) пишут в таблицы с FK на
    # users.telegram_id и упадут, если юзер впервые открыл Mini App не на
    # вкладке «Профиль». Тот же паттерн, что и /start в самом боте.
    db = request.app[DB_KEY]
    is_admin = tg_user.id in settings.admin_ids_set
    await upsert_user(db, tg_user.id, tg_user.username, is_admin)

    request["tg_user"] = tg_user
    return await handler(request)


def create_app(
    db: aiosqlite.Connection, settings: Settings, hub: SubscriptionHub
) -> web.Application:
    app = web.Application(middlewares=[auth_middleware])
    app[DB_KEY] = db
    app[SETTINGS_KEY] = settings
    app[WS_HUB_KEY] = hub
    app.add_routes(routes)
    app.add_routes(quiz_routes)
    app.add_routes(mental_math_routes)
    app.add_routes(activity_routes)
    app.add_routes(portfolio_ws_routes)

    # /api/* и /healthz регистрируются выше и матчатся первыми (точное
    # совпадение пути); статика на "/" — catch-all для всего остального,
    # поэтому порядок add_routes -> add_static важен.
    if STATIC_DIR.is_dir():
        index_path = STATIC_DIR / "index.html"

        # aiohttp.web.static НЕ отдаёт index.html на директорию-корень сам
        # (это не nginx) — без явного маршрута на "/" получим 403. Роут на
        # HashRouter других "хардовых" путей у SPA нет, так что этого
        # одного маршрута достаточно.
        async def index(_request: web.Request) -> web.FileResponse:
            return web.FileResponse(index_path)

        app.router.add_get("/", index)
        app.router.add_static("/", STATIC_DIR, show_index=False, name="static")
    else:
        logger.warning(
            "Собранный фронтенд не найден (%s) — Mini App отдаёт только "
            "/api/* и /healthz. Собери его: cd webapp && npm install && npm run build",
            STATIC_DIR,
        )

    return app


async def run_webapp_server(
    db: aiosqlite.Connection, settings: Settings, hub: SubscriptionHub
) -> web.AppRunner:
    """Поднимает сервер и возвращает AppRunner — вызывающий код (main.py)
    сам решает, когда его останавливать (runner.cleanup())."""
    app = create_app(db, settings, hub)
    runner = web.AppRunner(app, access_log_class=_RedactingAccessLogger)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.effective_webapp_port)
    await site.start()
    logger.info("Mini App сервер слушает порт %s", settings.effective_webapp_port)
    return runner
