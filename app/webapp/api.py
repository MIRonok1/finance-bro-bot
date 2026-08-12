"""JSON API для Mini App. Все маршруты под /api/* защищены initData-
авторизацией (см. server.py -> auth_middleware); /healthz — публичный."""

from __future__ import annotations

import logging

from aiohttp import web

from app.db import get_daily_streak
from app.mental_math import repo as mm_repo
from app.payments import repo as payments_repo
from app.portfolio.dashboard import build_snapshot
from app.portfolio.logic import kopecks_to_rub
from app.portfolio.repo import get_equity_history, get_or_create_portfolio
from app.quiz import repo as quiz_repo
from app.webapp.keys import DB_KEY, SETTINGS_KEY

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()


@routes.get("/healthz")
async def healthz(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


@routes.get("/api/me")
async def get_me(request: web.Request) -> web.Response:
    tg_user = request["tg_user"]
    db = request.app[DB_KEY]
    settings = request.app[SETTINGS_KEY]

    # Регистрация пользователя уже произошла в auth_middleware — здесь
    # только читаем то, что нужно для профиля.
    is_admin = tg_user.id in settings.admin_ids_set

    cursor = await db.execute(
        "SELECT first_seen_at FROM users WHERE telegram_id = ?", (tg_user.id,)
    )
    row = await cursor.fetchone()
    member_since = row["first_seen_at"] if row else None

    daily_streak = await get_daily_streak(db, tg_user.id)
    active = await payments_repo.has_active_entitlement(db, tg_user.id)
    plan = await payments_repo.get_active_plan(db, tg_user.id) if active else None

    return web.json_response(
        {
            "telegram_id": tg_user.id,
            "first_name": tg_user.first_name,
            "last_name": tg_user.last_name,
            "username": tg_user.username,
            "photo_url": tg_user.photo_url,
            "member_since": member_since,
            "daily_streak": daily_streak,
            "is_admin": is_admin,
            "subscription": {"active": active, "plan": plan},
        }
    )


@routes.get("/api/quiz/stats")
async def get_quiz_stats(request: web.Request) -> web.Response:
    tg_user = request["tg_user"]
    db = request.app[DB_KEY]

    topic_rows = await quiz_repo.topic_stats(db, tg_user.id)
    due_count = await quiz_repo.count_due_questions(db, tg_user.id)

    topics = [
        {
            "title": title,
            "total": total,
            "correct": correct,
            "pct": round(correct / total * 100) if total else 0,
            "weak": quiz_repo.is_weak_topic(total, correct),
        }
        for title, total, correct in topic_rows
    ]
    return web.json_response({"topics": topics, "due_review": due_count})


@routes.get("/api/mental_math/stats")
async def get_mental_math_stats(request: web.Request) -> web.Response:
    tg_user = request["tg_user"]
    db = request.app[DB_KEY]

    best_streak, total, correct = await mm_repo.get_stats(db, tg_user.id)
    daily = await mm_repo.get_daily_accuracy(db, tg_user.id, days=14)

    series = [
        {"date": d, "total": t, "correct": c, "pct": round(c / t * 100) if t else 0}
        for d, t, c in daily
    ]
    return web.json_response(
        {
            "best_streak": best_streak,
            "total_attempts": total,
            "total_correct": correct,
            "daily": series,
        }
    )


@routes.get("/api/portfolio")
async def get_portfolio(request: web.Request) -> web.Response:
    tg_user = request["tg_user"]
    db = request.app[DB_KEY]

    snapshot = await build_snapshot(db, tg_user.id)

    return web.json_response(
        {
            "cash_rub": str(snapshot.cash_rub),
            "equity_rub": str(snapshot.equity_rub),
            "daily_pnl_rub": str(snapshot.daily_pnl_rub),
            "daily_pnl_pct": str(snapshot.daily_pnl_pct),
            "imoex_daily_pct": (
                str(snapshot.imoex_daily_pct) if snapshot.imoex_daily_pct is not None else None
            ),
            "holdings": [
                {
                    "ticker": h.ticker,
                    "quantity": h.quantity,
                    "avg_price_rub": str(h.avg_price_rub),
                    "price_rub": str(h.price_rub),
                    "pnl_rub": str(h.pnl_rub),
                }
                for h in snapshot.holdings
            ],
        }
    )


@routes.get("/api/portfolio/history")
async def get_portfolio_history(request: web.Request) -> web.Response:
    tg_user = request["tg_user"]
    db = request.app[DB_KEY]

    portfolio = await get_or_create_portfolio(db, tg_user.id)
    history = await get_equity_history(db, portfolio.id, days=30)

    series = [
        {"date": d, "equity_rub": float(kopecks_to_rub(equity_kopecks))}
        for d, equity_kopecks in history
    ]
    return web.json_response({"history": series})
