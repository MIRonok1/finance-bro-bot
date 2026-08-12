"""Расчёт снимка портфеля (holdings + equity + дневной P&L + IMOEX) — общий
для хендлера бота и для Mini App API, чтобы поход в MOEX и вычисление P&L
не дублировались в двух местах."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import aiosqlite

from app.portfolio import repo
from app.portfolio.logic import (
    kopecks_to_rub,
    pnl_pct,
    rub_to_kopecks,
    total_equity_kopecks,
    unrealized_pnl_kopecks,
)
from app.portfolio.moex_client import MoexError, fetch_imoex_value
from app.portfolio.price_service import get_price_rub


@dataclass
class HoldingSnapshot:
    ticker: str
    quantity: int
    avg_price_rub: Decimal
    price_rub: Decimal
    pnl_rub: Decimal


@dataclass
class PortfolioSnapshot:
    cash_rub: Decimal
    equity_rub: Decimal
    daily_pnl_rub: Decimal
    daily_pnl_pct: Decimal
    imoex_daily_pct: Decimal | None
    holdings: list[HoldingSnapshot]


async def build_snapshot(conn: aiosqlite.Connection, user_id: int) -> PortfolioSnapshot:
    portfolio = await repo.get_or_create_portfolio(conn, user_id)
    holdings = await repo.list_holdings(conn, portfolio.id)

    holdings_value_kopecks = 0
    snapshots: list[HoldingSnapshot] = []
    for h in holdings:
        try:
            price_rub = await get_price_rub(conn, h.ticker)
        except MoexError:
            continue
        price_kopecks = rub_to_kopecks(price_rub)
        holdings_value_kopecks += price_kopecks * h.quantity
        pnl_kopecks = unrealized_pnl_kopecks(h.quantity, h.avg_price_kopecks, price_kopecks)
        snapshots.append(
            HoldingSnapshot(
                ticker=h.ticker,
                quantity=h.quantity,
                avg_price_rub=kopecks_to_rub(h.avg_price_kopecks),
                price_rub=price_rub,
                pnl_rub=kopecks_to_rub(pnl_kopecks),
            )
        )

    equity_kopecks = total_equity_kopecks(portfolio.cash_kopecks, holdings_value_kopecks)

    try:
        imoex_now = await fetch_imoex_value()
    except MoexError:
        imoex_now = None

    if imoex_now is not None:
        portfolio = await repo.maybe_reset_daily_reference(
            conn, portfolio, equity_kopecks, imoex_now
        )

    daily_pnl_kopecks = equity_kopecks - portfolio.equity_open_kopecks
    daily_pnl_pct = pnl_pct(Decimal(portfolio.equity_open_kopecks), Decimal(equity_kopecks))

    imoex_daily_pct = None
    if imoex_now is not None and portfolio.imoex_open_value is not None:
        imoex_daily_pct = pnl_pct(portfolio.imoex_open_value, imoex_now)

    return PortfolioSnapshot(
        cash_rub=kopecks_to_rub(portfolio.cash_kopecks),
        equity_rub=kopecks_to_rub(equity_kopecks),
        daily_pnl_rub=kopecks_to_rub(daily_pnl_kopecks),
        daily_pnl_pct=daily_pnl_pct,
        imoex_daily_pct=imoex_daily_pct,
        holdings=snapshots,
    )
