"""Клавиатуры модуля «Портфель»."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app import texts
from app.portfolio.repo import Holding

CB_PREFIX = "pf"
CB_BUY = f"{CB_PREFIX}:buy"
CB_SELL = f"{CB_PREFIX}:sell"
CB_REFRESH = f"{CB_PREFIX}:refresh"
CB_BACK_TO_MENU = f"{CB_PREFIX}:back"
CB_SELL_TICKER_PREFIX = f"{CB_PREFIX}:sell_ticker"


def dashboard_keyboard(has_holdings: bool) -> InlineKeyboardMarkup:
    top_row = [InlineKeyboardButton(text=texts.PORTFOLIO_BUY_BUTTON, callback_data=CB_BUY)]
    if has_holdings:
        top_row.append(
            InlineKeyboardButton(text=texts.PORTFOLIO_SELL_BUTTON, callback_data=CB_SELL)
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            top_row,
            [InlineKeyboardButton(text=texts.PORTFOLIO_REFRESH_BUTTON, callback_data=CB_REFRESH)],
            [InlineKeyboardButton(text=texts.PORTFOLIO_BACK_BUTTON, callback_data=CB_BACK_TO_MENU)],
        ]
    )


def sell_ticker_keyboard(holdings: list[Holding]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{h.ticker} ({h.quantity} шт.)",
                callback_data=f"{CB_SELL_TICKER_PREFIX}:{h.ticker}",
            )
        ]
        for h in holdings
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
