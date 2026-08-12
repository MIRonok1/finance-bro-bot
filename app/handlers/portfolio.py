"""FSM-флоу модуля «Портфель»: дашборд, покупка, продажа. Котировки — из
price_cache (TTL) с живым запросом к MOEX ISS при устаревании."""

from __future__ import annotations

import logging
from decimal import Decimal

import aiosqlite
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import texts
from app.config import Settings
from app.keyboards import CB_PORTFOLIO, main_menu
from app.mental_math.generators import fmt_decimal
from app.portfolio import repo
from app.portfolio.dashboard import build_snapshot
from app.portfolio.keyboards import (
    CB_BACK_TO_MENU,
    CB_BUY,
    CB_REFRESH,
    CB_SELL,
    CB_SELL_TICKER_PREFIX,
    dashboard_keyboard,
    sell_ticker_keyboard,
)
from app.portfolio.logic import (
    TradeError,
    compute_buy,
    compute_sell,
    kopecks_to_rub,
    rub_to_kopecks,
    total_equity_kopecks,
)
from app.portfolio.moex_client import MoexError
from app.portfolio.price_service import get_price_rub

logger = logging.getLogger(__name__)

router = Router(name="portfolio")


class PortfolioStates(StatesGroup):
    buying_ticker = State()
    buying_quantity = State()
    selling_quantity = State()


def _parse_positive_int(raw: str | None) -> int | None:
    if not raw:
        return None
    raw = raw.strip()
    if not raw.isdigit():
        return None
    value = int(raw)
    return value if value > 0 else None


async def _render_dashboard(db: aiosqlite.Connection, user_id: int) -> tuple[str, object]:
    snapshot = await build_snapshot(db, user_id)

    lines = [
        texts.PORTFOLIO_HEADER,
        texts.PORTFOLIO_CASH_LINE.format(cash=fmt_decimal(snapshot.cash_rub)),
        texts.PORTFOLIO_EQUITY_LINE.format(equity=fmt_decimal(snapshot.equity_rub)),
        texts.PORTFOLIO_DAILY_PNL_LINE.format(
            pnl=fmt_decimal(snapshot.daily_pnl_rub), pct=fmt_decimal(snapshot.daily_pnl_pct)
        ),
    ]
    if snapshot.imoex_daily_pct is not None:
        lines.append(
            texts.PORTFOLIO_VS_IMOEX_LINE.format(pct=fmt_decimal(snapshot.imoex_daily_pct))
        )

    lines.append("")
    if snapshot.holdings:
        for h in snapshot.holdings:
            lines.append(
                texts.PORTFOLIO_HOLDING_LINE.format(
                    ticker=h.ticker,
                    qty=h.quantity,
                    avg=fmt_decimal(h.avg_price_rub),
                    price=fmt_decimal(h.price_rub),
                    pnl=fmt_decimal(h.pnl_rub),
                )
            )
    else:
        lines.append(texts.PORTFOLIO_NO_HOLDINGS)

    return "\n".join(lines), dashboard_keyboard(has_holdings=bool(snapshot.holdings))


@router.callback_query(F.data == CB_PORTFOLIO)
async def show_portfolio(
    callback: CallbackQuery, db: aiosqlite.Connection, state: FSMContext
) -> None:
    await callback.answer()
    await state.clear()
    body, kb = await _render_dashboard(db, callback.from_user.id)
    await callback.message.answer(body, reply_markup=kb)


@router.callback_query(F.data == CB_REFRESH)
async def on_refresh(callback: CallbackQuery, db: aiosqlite.Connection) -> None:
    await callback.answer()
    body, kb = await _render_dashboard(db, callback.from_user.id)
    await callback.message.answer(body, reply_markup=kb)


@router.callback_query(F.data == CB_BUY)
async def on_buy_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await callback.message.answer(texts.PORTFOLIO_ASK_TICKER)
    await state.set_state(PortfolioStates.buying_ticker)


@router.message(PortfolioStates.buying_ticker)
async def on_buy_ticker(message: Message, db: aiosqlite.Connection, state: FSMContext) -> None:
    ticker = (message.text or "").strip().upper()
    if not ticker:
        await message.answer(texts.PORTFOLIO_ASK_TICKER)
        return
    try:
        price_rub = await get_price_rub(db, ticker)
    except MoexError:
        await message.answer(texts.PORTFOLIO_TICKER_NOT_FOUND.format(ticker=ticker))
        return

    await state.update_data(ticker=ticker, price_rub=str(price_rub))
    await message.answer(
        texts.PORTFOLIO_ASK_QUANTITY_BUY.format(ticker=ticker, price=fmt_decimal(price_rub))
    )
    await state.set_state(PortfolioStates.buying_quantity)


@router.message(PortfolioStates.buying_quantity)
async def on_buy_quantity(message: Message, db: aiosqlite.Connection, state: FSMContext) -> None:
    quantity = _parse_positive_int(message.text)
    if quantity is None:
        await message.answer(texts.PORTFOLIO_INVALID_QUANTITY)
        return

    data = await state.get_data()
    ticker = data["ticker"]
    price_rub = Decimal(data["price_rub"])
    price_kopecks = rub_to_kopecks(price_rub)

    portfolio = await repo.get_or_create_portfolio(db, message.from_user.id)
    holding = await repo.get_holding(db, portfolio.id, ticker)
    holdings = await repo.list_holdings(db, portfolio.id)

    holdings_value_kopecks = 0
    for h in holdings:
        try:
            h_price_rub = await get_price_rub(db, h.ticker)
        except MoexError:
            h_price_rub = kopecks_to_rub(h.avg_price_kopecks)
        holdings_value_kopecks += rub_to_kopecks(h_price_rub) * h.quantity
    equity_kopecks = total_equity_kopecks(portfolio.cash_kopecks, holdings_value_kopecks)

    try:
        result = compute_buy(
            cash_kopecks=portfolio.cash_kopecks,
            holding_quantity=holding.quantity if holding else 0,
            holding_avg_price_kopecks=holding.avg_price_kopecks if holding else 0,
            price_kopecks=price_kopecks,
            quantity=quantity,
            total_equity_kopecks=equity_kopecks,
        )
    except TradeError as exc:
        await message.answer(str(exc))
        return

    await repo.apply_buy(
        db,
        portfolio.id,
        ticker,
        quantity,
        price_kopecks,
        result.new_cash_kopecks,
        result.new_quantity,
        result.new_avg_price_kopecks,
    )
    await message.answer(
        texts.PORTFOLIO_BUY_DONE.format(
            qty=quantity,
            ticker=ticker,
            price=fmt_decimal(price_rub),
            cash=fmt_decimal(kopecks_to_rub(result.new_cash_kopecks)),
        )
    )
    await state.clear()
    body, kb = await _render_dashboard(db, message.from_user.id)
    await message.answer(body, reply_markup=kb)


@router.callback_query(F.data == CB_SELL)
async def on_sell_start(callback: CallbackQuery, db: aiosqlite.Connection) -> None:
    await callback.answer()
    portfolio = await repo.get_or_create_portfolio(db, callback.from_user.id)
    holdings = await repo.list_holdings(db, portfolio.id)
    if not holdings:
        await callback.message.answer(texts.PORTFOLIO_NO_HOLDINGS_TO_SELL)
        return
    await callback.message.answer(
        texts.PORTFOLIO_CHOOSE_TICKER_TO_SELL, reply_markup=sell_ticker_keyboard(holdings)
    )


@router.callback_query(F.data.startswith(f"{CB_SELL_TICKER_PREFIX}:"))
async def on_sell_ticker_chosen(
    callback: CallbackQuery, db: aiosqlite.Connection, state: FSMContext
) -> None:
    ticker = callback.data.split(":")[-1]
    await callback.answer()

    portfolio = await repo.get_or_create_portfolio(db, callback.from_user.id)
    holding = await repo.get_holding(db, portfolio.id, ticker)
    if holding is None or holding.quantity <= 0:
        await callback.message.answer(texts.PORTFOLIO_NO_HOLDINGS_TO_SELL)
        return

    try:
        price_rub = await get_price_rub(db, ticker)
    except MoexError:
        await callback.message.answer(texts.PORTFOLIO_MOEX_UNAVAILABLE)
        return

    await state.update_data(ticker=ticker, price_rub=str(price_rub))
    await callback.message.answer(
        texts.PORTFOLIO_ASK_QUANTITY_SELL.format(
            ticker=ticker, qty=holding.quantity, price=fmt_decimal(price_rub)
        )
    )
    await state.set_state(PortfolioStates.selling_quantity)


@router.message(PortfolioStates.selling_quantity)
async def on_sell_quantity(message: Message, db: aiosqlite.Connection, state: FSMContext) -> None:
    quantity = _parse_positive_int(message.text)
    if quantity is None:
        await message.answer(texts.PORTFOLIO_INVALID_QUANTITY)
        return

    data = await state.get_data()
    ticker = data["ticker"]
    price_rub = Decimal(data["price_rub"])
    price_kopecks = rub_to_kopecks(price_rub)

    portfolio = await repo.get_or_create_portfolio(db, message.from_user.id)
    holding = await repo.get_holding(db, portfolio.id, ticker)

    try:
        result = compute_sell(
            cash_kopecks=portfolio.cash_kopecks,
            holding_quantity=holding.quantity if holding else 0,
            price_kopecks=price_kopecks,
            quantity=quantity,
        )
    except TradeError as exc:
        await message.answer(str(exc))
        return

    await repo.apply_sell(
        db,
        portfolio.id,
        ticker,
        quantity,
        price_kopecks,
        result.new_cash_kopecks,
        result.new_quantity,
    )
    await message.answer(
        texts.PORTFOLIO_SELL_DONE.format(
            qty=quantity,
            ticker=ticker,
            price=fmt_decimal(price_rub),
            cash=fmt_decimal(kopecks_to_rub(result.new_cash_kopecks)),
        )
    )
    await state.clear()
    body, kb = await _render_dashboard(db, message.from_user.id)
    await message.answer(body, reply_markup=kb)


@router.callback_query(F.data == CB_BACK_TO_MENU)
async def on_back_to_menu(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.answer(texts.START_GREETING, reply_markup=main_menu(settings.webapp_url))
